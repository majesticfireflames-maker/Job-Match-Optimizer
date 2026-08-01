from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import tempfile
import re
from dotenv import load_dotenv
from groq import Groq
from pypdf import PdfReader

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    print("ERROR: GROQ_API_KEY not found. Create .env file")
    exit(1)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = Groq(api_key=GROQ_API_KEY)

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Job Match & Resume Optimizer</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
            color: #e0e0e0;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header {
            background: linear-gradient(135deg, #00b894 0%, #00cec9 100%);
            padding: 40px;
            border-radius: 20px;
            margin-bottom: 30px;
            text-align: center;
            box-shadow: 0 10px 40px rgba(0, 206, 201, 0.3);
        }
        .header h1 { font-size: 3rem; color: white; }
        .header p { color: rgba(255,255,255,0.9); font-size: 1.2rem; margin-top: 10px; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; }
        .card {
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 25px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .card h2 { color: #00b894; margin-bottom: 15px; font-size: 1.2rem; }
        textarea {
            width: 100%;
            height: 300px;
            background: rgba(0,0,0,0.3);
            color: #e0e0e0;
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 15px;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            resize: vertical;
        }
        textarea:focus { outline: none; border-color: #00b894; }
        .upload-area {
            border: 2px dashed rgba(0, 184, 148, 0.4);
            border-radius: 12px;
            padding: 30px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            margin-bottom: 15px;
        }
        .upload-area:hover { border-color: #00b894; background: rgba(0,184,148,0.05); }
        .upload-area input { display: none; }
        .upload-area .icon { font-size: 3rem; }
        .upload-area p { color: #aaa; }
        button {
            padding: 14px 40px;
            background: linear-gradient(135deg, #00b894, #00cec9);
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 1.1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            width: 100%;
            margin-top: 10px;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(0, 206, 201, 0.4);
        }
        button:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        .result-card {
            background: rgba(0,0,0,0.3);
            border-radius: 12px;
            padding: 20px;
            margin-top: 15px;
            border: 1px solid rgba(255,255,255,0.05);
            max-height: 600px;
            overflow-y: auto;
        }
        .result-card h3 {
            color: #00b894;
            margin-top: 15px;
            margin-bottom: 8px;
        }
        .result-card h3:first-child { margin-top: 0; }
        .result-card ul { padding-left: 20px; margin-bottom: 10px; }
        .result-card li { margin-bottom: 5px; color: #ccc; }
        .result-card pre {
            background: #0a0a0a;
            padding: 15px;
            border-radius: 8px;
            overflow-x: auto;
            font-size: 13px;
            color: #4CAF50;
            border: 1px solid rgba(255,255,255,0.05);
        }
        .score-big {
            font-size: 4rem;
            font-weight: 700;
            text-align: center;
            padding: 20px;
            background: rgba(0,184,148,0.1);
            border-radius: 12px;
            border: 3px solid #00b894;
            margin-bottom: 15px;
        }
        .score-label { font-size: 1rem; color: #888; margin-top: 5px; }
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255,255,255,0.1);
            border-top-color: #00b894;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        .loader-container {
            text-align: center;
            padding: 30px;
        }
        .loader-bar {
            width: 100%;
            height: 6px;
            background: rgba(255,255,255,0.1);
            border-radius: 3px;
            overflow: hidden;
            margin: 10px 0;
        }
        .loader-bar-fill {
            height: 100%;
            width: 0%;
            background: linear-gradient(90deg, #00b894, #00cec9);
            border-radius: 3px;
            animation: fillLoader 2s ease-in-out forwards;
        }
        @keyframes fillLoader {
            0% { width: 0%; }
            100% { width: 100%; }
        }
        .file-status {
            color: #00b894;
            font-size: 0.9rem;
            margin-top: 5px;
        }
        .file-status.error { color: #ff6b6b; }
        .stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin: 15px 0;
        }
        .stat-box {
            background: rgba(255,255,255,0.05);
            padding: 12px;
            border-radius: 8px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.05);
        }
        .stat-box .number { font-size: 1.5rem; font-weight: 700; color: #00b894; }
        .stat-box .label { font-size: 0.8rem; color: #888; }
        @media (max-width: 768px) {
            .grid { grid-template-columns: 1fr; }
            .header h1 { font-size: 2rem; }
        }
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: rgba(255,255,255,0.05); border-radius: 10px; }
        ::-webkit-scrollbar-thumb { background: #00b894; border-radius: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Job Match & Resume Optimizer</h1>
            <p>Upload your resume and paste a job description to get AI-powered optimization suggestions</p>
        </div>
        <div class="grid">
            <div class="card">
                <h2>Resume Upload</h2>
                <div class="upload-area" id="uploadArea">
                    <div class="icon">📄</div>
                    <p>Click to upload PDF resume</p>
                    <input type="file" id="resumeInput" accept=".pdf">
                </div>
                <div id="uploadStatus" class="file-status"></div>

                <h2 style="margin-top:20px;">Job Description</h2>
                <textarea id="jobDesc" placeholder="Paste the job description here..."></textarea>

                <button id="analyzeBtn">Analyze & Optimize</button>
            </div>
            <div class="card">
                <h2>Results</h2>
                <div id="result">
                    <div class="result-card" style="text-align:center;color:#888;padding:40px 20px;">
                        <div style="font-size:3rem;margin-bottom:10px;">📊</div>
                        <p>Upload your resume and paste a job description<br>to get AI-powered optimization suggestions</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script>
        const analyzeBtn = document.getElementById('analyzeBtn');
        const resumeInput = document.getElementById('resumeInput');
        const uploadArea = document.getElementById('uploadArea');
        const uploadStatus = document.getElementById('uploadStatus');
        const jobDesc = document.getElementById('jobDesc');
        const resultDiv = document.getElementById('result');

        let resumeFile = null;

        uploadArea.addEventListener('click', function() {
            resumeInput.click();
        });

        resumeInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                resumeFile = file;
                uploadStatus.textContent = 'Uploaded: ' + file.name;
                uploadStatus.className = 'file-status';
            }
        });

        analyzeBtn.addEventListener('click', async function() {
            const jobDescription = jobDesc.value.trim();

            if (!resumeFile) {
                alert('Please upload your resume first');
                return;
            }

            if (!jobDescription) {
                alert('Please paste a job description');
                return;
            }

            analyzeBtn.disabled = true;
            analyzeBtn.innerHTML = '<div class="loading"></div> Analyzing...';

            // Show loader with progress
            resultDiv.innerHTML = `
                <div class="result-card">
                    <div class="loader-container">
                        <div class="loading"></div>
                        <p style="margin-top:10px;color:#888;">AI is analyzing your resume...</p>
                        <div class="loader-bar"><div class="loader-bar-fill"></div></div>
                        <p style="font-size:0.8rem;color:#666;margin-top:5px;">Checking skills, experience, and keywords...</p>
                    </div>
                </div>
            `;

            try {
                const formData = new FormData();
                formData.append('resume', resumeFile);
                formData.append('job_description', jobDescription);

                const response = await fetch('/analyze', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (data.error) {
                    resultDiv.innerHTML = '<div class="result-card"><p style="color:#ff6b6b;">Error: ' + data.error + '</p></div>';
                } else {
                    resultDiv.innerHTML = formatResults(data);
                }

            } catch (error) {
                resultDiv.innerHTML = '<div class="result-card"><p style="color:#ff6b6b;">Error: ' + error.message + '</p></div>';
            }

            analyzeBtn.disabled = false;
            analyzeBtn.innerHTML = 'Analyze & Optimize';
        });

        function formatResults(data) {
            let html = '<div class="result-card">';

            // Score display
            const score = data.match_score || '70';
            html += `
                <div class="score-big">
                    ${score}%
                    <div class="score-label">Match Score</div>
                </div>
            `;

            // Extract stats
            let strengths = 0;
            let gaps = 0;
            let keywords = 0;

            const sections = data.analysis.split(/\\n(?=[A-Z])/);

            sections.forEach(function(section) {
                if (section.includes('Strengths')) {
                    strengths = countItems(section);
                    html += '<h3>Strengths</h3><ul>' + formatList(section) + '</ul>';
                } else if (section.includes('Gaps')) {
                    gaps = countItems(section);
                    html += '<h3>Gaps</h3><ul>' + formatList(section) + '</ul>';
                } else if (section.includes('Keyword')) {
                    keywords = countItems(section);
                    html += '<h3>Keyword Gap Analysis</h3><ul>' + formatList(section) + '</ul>';
                } else if (section.includes('Rewrite')) {
                    html += '<h3>Rewrite Suggestions</h3><ul>' + formatList(section) + '</ul>';
                } else if (section.includes('Optimized')) {
                    html += '<h3>Optimized Resume Summary</h3><p>' + formatExplanation(section) + '</p>';
                } else if (section.includes('Tips')) {
                    html += '<h3>ATS-Friendly Tips</h3><ul>' + formatList(section) + '</ul>';
                }
            });

            // Add stats at the top
            const statsHtml = `
                <div class="stats-grid">
                    <div class="stat-box">
                        <div class="number">${strengths || 0}</div>
                        <div class="label">Strengths Found</div>
                    </div>
                    <div class="stat-box">
                        <div class="number">${gaps || 0}</div>
                        <div class="label">Gaps Identified</div>
                    </div>
                    <div class="stat-box">
                        <div class="number">${keywords || 0}</div>
                        <div class="label">Missing Keywords</div>
                    </div>
                    <div class="stat-box">
                        <div class="number">${data.match_score || '70'}%</div>
                        <div class="label">Match Score</div>
                    </div>
                </div>
            `;

            html = statsHtml + html;
            html += '</div>';
            return html;
        }

        function countItems(section) {
            const lines = section.split('\\n').filter(function(line) {
                return line.match(/^[-*•]|\\d\\./);
            });
            return lines.length || 0;
        }

        function formatList(section) {
            const lines = section.split('\\n').filter(function(line) {
                return line.match(/^[-*•]|\\d\\./);
            });
            if (lines.length === 0) {
                const content = section.replace(/^[^:]*:/, '').trim();
                return '<li>' + content + '</li>';
            }
            return lines.map(function(line) {
                const clean = line.replace(/^[-*•]\\s*|^\\d\\.\\s*/, '').trim();
                return '<li>' + clean + '</li>';
            }).join('');
        }

        function formatExplanation(section) {
            return section.replace(/^[^:]*:/, '').trim();
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTML

@app.post("/analyze")
async def analyze(
    resume: UploadFile = File(...),
    job_description: str = Form(...)
):
    try:
        if not job_description:
            return JSONResponse({"error": "Job description is required"})

        content = await resume.read()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            with open(tmp_path, "rb") as f:
                reader = PdfReader(f)
                resume_text = ""
                for page in reader.pages:
                    resume_text += page.extract_text()
        finally:
            os.unlink(tmp_path)

        if not resume_text.strip():
            return JSONResponse({"error": "Could not extract text from resume"})

        prompt = f"""You are an expert resume reviewer and career coach. Analyze this resume against the job description and provide a detailed assessment.

Resume:
{resume_text[:4000]}

Job Description:
{job_description[:2000]}

Provide your analysis in this exact format:

Strengths:
- List what matches well

Gaps:
- List what's missing compared to the job description

Keyword Gap Analysis:
- List important keywords from the job description that are missing in the resume

Rewrite Suggestions:
- Provide specific rewrite suggestions for weak sections

Optimized Resume Summary:
- Write a 2-3 sentence optimized professional summary for this role

ATS-Friendly Tips:
- Provide formatting and content tips to pass ATS screening

Be specific, actionable, and helpful."""

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are an expert resume reviewer and career coach."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1024,
        )

        analysis = completion.choices[0].message.content

        import re
        match_score = "70"
        match_match = re.search(r'(\d+)%', analysis)
        if match_match:
            match_score = match_match.group(1)

        return JSONResponse({
            "analysis": analysis,
            "match_score": match_score
        })

    except Exception as e:
        return JSONResponse({"error": str(e)})

if __name__ == "__main__":
    print("=" * 60)
    print("JOB MATCH & RESUME OPTIMIZER")
    print("=" * 60)
    print("Open: http://localhost:8000")
    print("Upload resume and paste job description")
    print("Powered by Groq Llama 3.3 70B")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000)