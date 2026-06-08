# ATS Hiring Agent

AI-powered Applicant Tracking System that parses resume PDFs, scores candidates with explainable rubrics, and optionally matches resumes against job descriptions — all through a modern web UI and REST API.

Built with **FastAPI**, **PyMuPDF**, and **Nebius AI Studio** for LLM-backed extraction. Every prompt lives in version-controlled Jinja templates so scoring behavior is transparent and easy to tune.

---

## Table of contents

- [Features](#features)
- [How it works](#how-it-works)
- [Project structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the application](#running-the-application)
- [Using the web UI](#using-the-web-ui)
- [Scoring system](#scoring-system)
- [Job description matching](#job-description-matching)
- [API reference](#api-reference)
- [Customizing prompts](#customizing-prompts)
- [LLM providers](#llm-providers)
- [Troubleshooting](#troubleshooting)

---

## Features

### Web interface

- Drag-and-drop PDF upload (max 10 MB by default)
- Optional job description field for JD-aware matching
- Tabbed results: **Overview**, **JD Match**, **Resume Details**
- Responsive layout for desktop and mobile

### Resume evaluation

- PDF → Markdown extraction via `pymupdf_rag`
- Section-by-section JSON parsing (basics, work, education, skills, projects, awards)
- Four category scores with written evidence per category
- Bonus points and deductions with breakdowns
- Key strengths and areas for improvement
- Final score on a **1–100** ATS scale (normalized from the internal rubric)

### Job description matching

- Strict, evidence-based match scoring (0–100%)
- Skill match, experience match, and keyword match percentages
- Matched vs missing skills with confidence levels
- Strengths, gaps, and actionable recommendations
- Mandatory score caps when required skills or experience are absent

### Production-ready defaults

- Environment-based configuration (`.env`)
- Temporary file handling — uploads are not persisted on disk
- CORS, log level, and file size limits configurable
- Health check endpoint for monitoring

---

## How it works

```mermaid
flowchart TD
    A[Upload PDF] --> B[pymupdf_rag: PDF to Markdown]
    B --> C[pdf.py: LLM section extraction]
    C --> D[transform.py: normalize to JSON Resume]
    D --> E[evaluator.py: score resume]
    B --> E
    F[Optional JD text] --> G[jd_matcher.py: strict JD match]
    B --> G
    E --> H[JSON response]
    G --> H
    D --> H
    H --> I[Web UI / API client]
```

1. **Extract text** — The PDF is converted to structured Markdown text.
2. **Parse sections** — The LLM extracts each resume section using dedicated Jinja prompts.
3. **Normalize** — Raw LLM output is transformed into [JSON Resume](https://jsonresume.org/) format.
4. **Enrich with GitHub** *(if GitHub URL on resume)* — fetches repos, ranks top 7 via LLM.
5. **Evaluate** — scores open source, projects, production experience, and technical skills using resume + GitHub text.
6. **Match JD** *(optional)* — strict comparison against job description.
7. **Respond** — JSON returned to web UI or printed in CLI.

---

## Project structure

```
hiring-agent/
├── app.py                          # FastAPI web app
├── score.py                        # Thin CLI shim (delegates to services/score.py)
├── services/                       # Core business logic
│   ├── __init__.py
│   ├── config.py
│   ├── pdf.py
│   ├── evaluator.py
│   ├── jd_matcher.py
│   ├── github.py                   # GitHub API + repo ranking (4+ commits)
│   ├── pipeline.py                 # Shared web + CLI workflow
│   ├── score.py                    # CLI implementation
│   ├── resume_text.py              # Text builders for LLM input
│   ├── models.py
│   ├── llm_utils.py
│   ├── prompt.py
│   ├── transform.py
│   └── pymupdf_rag.py
├── prompts/
│   ├── template_manager.py
│   └── templates/
│       ├── basics.jinja … awards.jinja
│       ├── resume_evaluation_*.jinja
│       ├── jd_matching_*.jinja
│       └── github_project_selection.jinja
├── templates/
│   └── index.html
├── requirements.txt
├── .env.example
└── README.md
```

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| **Python 3.11+** | Tested with 3.11 and 3.12 |
| **Nebius AI Studio** | API key from [Nebius](https://nebius.com/) — required |

---

## Installation

### 1. Clone and enter the project

```bash
git clone <repository-url>
cd hiring-agent
```

### 2. Create a virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Edit `.env` with your Nebius API key and settings (see [Configuration](#configuration)).

---

## Configuration

All settings are loaded from `.env` via `python-dotenv`. See `.env.example` for the full template.

### Server settings

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `5000` | Server port |
| `DEBUG` | `false` | Enables debug log level when `true` |
| `LOG_LEVEL` | `INFO` | Python logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `OPEN_BROWSER` | `false` | Auto-open browser when running `python app.py` |
| `MAX_FILE_SIZE` | `10485760` | Max upload size in bytes (10 MB) |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins, or `*` for all |

### LLM settings

| Variable | Default | Description |
|----------|---------|-------------|
| `NEBIUS_API_KEY` | — | **Required.** Nebius AI Studio API key |
| `DEFAULT_MODEL` | `google/gemma-3-27b-it` | Nebius model identifier |
| `GITHUB_TOKEN` | — | Optional. Raises GitHub API limit to 5000 req/hour |
| `DEVELOPMENT_MODE` | `false` | Cache parsed resume + GitHub data in `cache/` |

### Supported models

Configured in `services/prompt.py`:

- `google/gemma-3-27b-it`
- `google/gemma-3-12b-it`
- `meta-llama/Meta-Llama-3.1-70B-Instruct`
- `meta-llama/Meta-Llama-3.1-8B-Instruct`
- `mistralai/Mistral-Nemo-Instruct-2407`

Model-specific temperature and `top_p` values are defined in `MODEL_PARAMETERS` inside `services/prompt.py`.

---

## Running the application

### Recommended (production)

```bash
python -m uvicorn app:app --host 0.0.0.0 --port 5000
```

### Development (with auto browser)

```bash
# Set in .env: DEBUG=true, OPEN_BROWSER=true
python app.py
```

### CLI (batch scoring)

```bash
python -m services.score path/to/resume.pdf
# or: python score.py path/to/resume.pdf
```

### Access points

| URL | Description |
|-----|-------------|
| http://localhost:5000 | Web UI |
| http://localhost:5000/docs | Swagger API documentation |
| http://localhost:5000/redoc | ReDoc API documentation |
| http://localhost:5000/api/health | Health check |

---

## Using the web UI

1. Open http://localhost:5000
2. **Upload** a resume PDF (drag-and-drop or click to browse)
3. *(Optional)* Paste a **job description** in the text area
4. Click **Upload & Evaluate**
5. Review results in the tabs:
   - **Overview** — Final score, category breakdown with evidence, strengths, improvements, bonuses, deductions
   - **JD Match** — Match percentages, skill analysis, gaps, recommendations *(only when JD is provided)*
   - **Resume Details** — Parsed personal info, work, education, skills, projects

Evaluation typically takes 30–90 seconds depending on model speed and resume length.

---

## Scoring system

The evaluator assigns scores across four categories. Scoring rules and fairness constraints are defined in `prompts/templates/resume_evaluation_*.jinja`.

| Category | Max points | What it measures |
|----------|------------|------------------|
| **Open Source** | 35 | Contributions to others' projects, GSoC, community involvement |
| **Self Projects** | 30 | Personal/hackathon project complexity and impact |
| **Production** | 25 | Work, internship, and real-world experience |
| **Technical Skills** | 10 | Breadth and depth of technical skills |

Additional adjustments:

- **Bonus points** — up to **+20** (e.g. prestigious programs, exceptional projects)
- **Deductions** — subtracted from total (e.g. missing links, tutorial-only projects)

**Final score (displayed)** = normalized to **1–100** from the internal rubric total (categories + bonus − deductions, max 120). Category breakdowns still show their original point values (e.g. open source /35).

### Fairness

Scores intentionally ignore name, gender, university, GPA, and location. Evaluation is based only on demonstrated technical skills, projects, and experience.

---

## Job description matching

When a job description is supplied, `JDMatcher` runs a **strict, evidence-based** comparison. Prompts live in:

- `prompts/templates/jd_matching_system_message.jinja` — scoring philosophy and caps
- `prompts/templates/jd_matching_criteria.jinja` — analysis instructions and JSON schema

### Match outputs

| Field | Description |
|-------|-------------|
| `match_score` | Overall fit (0–100), with mandatory caps for missing requirements |
| `skill_match_percentage` | % of required JD skills found in resume |
| `experience_match` | Alignment of years, seniority, and role type |
| `keyword_match_percentage` | % of important JD keywords present in resume |
| `matched_skills` / `missing_skills` | Per-skill analysis with importance and confidence |
| `matched_keywords` | Shared terms with frequency counts |
| `strengths` / `gaps` / `recommendations` | Actionable feedback |

### Strict scoring rules (summary)

- No credit for implied or assumed skills — only explicit resume evidence counts
- Missing any required skill caps overall match at **65**
- Missing more than half of required skills caps match at **45**
- Experience below JD minimum caps experience match at **40** and overall at **55**
- Scores above **70** require strong, documented proof

---

## API reference

### `GET /`

Serves the web UI (`templates/index.html`).

---

### `GET /api/health`

Health check for load balancers and monitoring.

**Response:**

```json
{
  "status": "healthy",
  "service": "ATS Hiring Agent API",
  "timestamp": "2026-06-05T12:00:00.000000"
}
```

---

### `POST /api/evaluate`

Evaluate a resume PDF. Optionally include a job description for JD matching.

**Content-Type:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | Yes | PDF resume (`.pdf` only) |
| `job_description` | string | No | Job description text for JD matching |

**Example (curl):**

```bash
curl -X POST http://localhost:5000/api/evaluate \
  -F "file=@resume.pdf" \
  -F "job_description=We are looking for a Python developer with FastAPI experience..."
```

**Success response (`200`):**

```json
{
  "success": true,
  "file_name": "resume.pdf",
  "evaluation": {
    "final_score": 53,
    "raw_score": 63,
    "category_scores": {
      "open_source": { "score": 8, "max": 35, "evidence": "..." },
      "self_projects": { "score": 22, "max": 30, "evidence": "..." },
      "production": { "score": 18, "max": 25, "evidence": "..." },
      "technical_skills": { "score": 8, "max": 10, "evidence": "..." }
    },
    "bonus_points": { "total": 5, "breakdown": "..." },
    "deductions": { "total": 0, "reasons": "..." },
    "key_strengths": ["...", "..."],
    "areas_for_improvement": ["...", "..."]
  },
  "resume_data": {
    "basics": { "name": "...", "email": "..." },
    "work": [],
    "education": [],
    "skills": [],
    "projects": []
  },
  "jd_match": null
}
```

When a job description is provided, `jd_match` contains the full match object (scores, skills, gaps, recommendations). When omitted, `jd_match` is `null`.

**Error responses:**

| Status | Cause |
|--------|-------|
| `400` | Invalid file type or unreadable PDF |
| `413` | File exceeds `MAX_FILE_SIZE` |
| `500` | Processing or LLM error |

---

## Customizing prompts

All LLM instructions are in Jinja templates under `prompts/templates/`. Edit these files to change scoring behavior — no Python changes required for most tuning.

| Template | Purpose |
|----------|---------|
| `basics.jinja` … `awards.jinja` | Resume section extraction |
| `system_message.jinja` | Extraction system message |
| `resume_evaluation_criteria.jinja` | Scoring rubric and JSON schema |
| `resume_evaluation_system_message.jinja` | Evaluation system message and fairness rules |
| `jd_matching_criteria.jinja` | JD match user prompt |
| `jd_matching_system_message.jinja` | JD match strict scoring rules |

Templates are loaded by `prompts/template_manager.py` using absolute paths, so they work regardless of the working directory.

After editing templates, restart the server to pick up changes.

---

## LLM provider

This project uses **Nebius AI Studio** exclusively via the OpenAI-compatible API.

Set in `.env`:

```env
NEBIUS_API_KEY=your_key_here
DEFAULT_MODEL=google/gemma-3-27b-it
```

The app will not start LLM calls without a valid `NEBIUS_API_KEY`.

---

## Troubleshooting

### `Failed to extract text from PDF`

The PDF may be scanned/image-only. Use a PDF with selectable text, or run OCR before upload.

### Slow evaluation

Section extraction calls the LLM six times (basics, work, education, skills, projects, awards), plus one evaluation call and optionally one JD match call. Use a faster Nebius model (e.g. `google/gemma-3-12b-it`) if latency is an issue.

### Nebius authentication errors

Verify `NEBIUS_API_KEY` in `.env` and that `DEFAULT_MODEL` matches a supported Nebius model name.

### JD Match tab shows placeholder

Paste a job description before clicking **Upload & Evaluate**. JD matching only runs when the `job_description` form field is non-empty.

### Template not found warnings

Ensure you run the server from the project root so `prompts/templates/` resolves correctly. The template manager uses absolute paths from the repo root.

---

## Tech stack

| Layer | Technology |
|-------|------------|
| API | FastAPI, Uvicorn |
| PDF | PyMuPDF, pymupdf4llm |
| LLM | Nebius AI Studio (OpenAI-compatible) |
| Schemas | Pydantic v2 |
| Prompts | Jinja2 |
| Frontend | Vanilla HTML/CSS/JS |
