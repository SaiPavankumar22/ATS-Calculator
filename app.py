"""FastAPI application entry point for the ATS Hiring Agent."""

import logging
import re
import tempfile
import traceback
import webbrowser
from datetime import datetime
from pathlib import Path
from threading import Thread

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from services.config import (
    CORS_ORIGINS,
    HOST,
    LOG_LEVEL,
    MAX_FILE_SIZE,
    OPEN_BROWSER,
    PORT,
    TEMPLATES_DIR,
)
from services.pdf import PDFHandler
from services.pipeline import (
    calculate_raw_score,
    evaluate_resume_pipeline,
    normalize_final_score,
)

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {"pdf"}

app = FastAPI(
    title="ATS Hiring Agent",
    description="Resume Evaluation System Powered by AI",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if CORS_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pdf_handler = PDFHandler()


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def secure_filename(filename: str) -> str:
    name = Path(filename).name
    cleaned = re.sub(r"[^\w\s.-]", "", name).strip()
    return cleaned or "resume.pdf"


def build_evaluation_response(evaluation, parsed_resume, jd_score, github_data, filename: str) -> dict:
    scores_data = evaluation.scores
    raw_score = calculate_raw_score(evaluation)

    return {
        "success": True,
        "file_name": filename,
        "evaluation": {
            "final_score": normalize_final_score(raw_score),
            "raw_score": round(raw_score, 1),
            "category_scores": {
                "open_source": {
                    "score": scores_data.open_source.score,
                    "max": scores_data.open_source.max,
                    "evidence": scores_data.open_source.evidence,
                },
                "self_projects": {
                    "score": scores_data.self_projects.score,
                    "max": scores_data.self_projects.max,
                    "evidence": scores_data.self_projects.evidence,
                },
                "production": {
                    "score": scores_data.production.score,
                    "max": scores_data.production.max,
                    "evidence": scores_data.production.evidence,
                },
                "technical_skills": {
                    "score": scores_data.technical_skills.score,
                    "max": scores_data.technical_skills.max,
                    "evidence": scores_data.technical_skills.evidence,
                },
            },
            "bonus_points": {
                "total": evaluation.bonus_points.total,
                "breakdown": evaluation.bonus_points.breakdown,
            },
            "deductions": {
                "total": evaluation.deductions.total,
                "reasons": evaluation.deductions.reasons,
            },
            "key_strengths": evaluation.key_strengths,
            "areas_for_improvement": evaluation.areas_for_improvement,
        },
        "resume_data": {
            "basics": (
                parsed_resume.basics.model_dump()
                if parsed_resume and parsed_resume.basics
                else None
            ),
            "work": [w.model_dump() for w in (parsed_resume.work or [])]
            if parsed_resume
            else [],
            "education": [e.model_dump() for e in (parsed_resume.education or [])]
            if parsed_resume
            else [],
            "skills": [s.model_dump() for s in (parsed_resume.skills or [])]
            if parsed_resume
            else [],
            "projects": [p.model_dump() for p in (parsed_resume.projects or [])]
            if parsed_resume
            else [],
        },
        "jd_match": jd_score.model_dump() if jd_score else None,
        "github_data": github_data or None,
    }


@app.get("/")
async def index():
    return FileResponse(TEMPLATES_DIR / "index.html")


@app.post("/api/evaluate")
async def evaluate_resume(
    file: UploadFile = File(...),
    job_description: str = Form(None),
):
    filepath = None
    try:
        if not file.filename or not allowed_file(file.filename):
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Please upload a PDF file.",
            )

        file_content = await file.read()
        if len(file_content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE // 1024 // 1024}MB.",
            )

        filename = secure_filename(file.filename)
        suffix = Path(filename).suffix or ".pdf"

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file_content)
            filepath = tmp.name

        logger.info("Processing uploaded resume: %s", filename)

        resume_text = pdf_handler.extract_text_from_pdf(filepath)
        if not resume_text:
            raise HTTPException(
                status_code=400,
                detail="Failed to extract text from PDF. Please ensure the PDF contains readable text.",
            )

        parsed_resume = pdf_handler.extract_json_from_text(resume_text)

        evaluation, jd_score, github_data = evaluate_resume_pipeline(
            resume_text=resume_text,
            parsed_resume=parsed_resume,
            job_description=job_description,
            include_github=True,
        )

        return JSONResponse(
            content=build_evaluation_response(
                evaluation, parsed_resume, jd_score, github_data, filename
            ),
            status_code=200,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error processing resume: %s", exc)
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error processing resume: {exc}",
        ) from exc
    finally:
        if filepath:
            try:
                Path(filepath).unlink(missing_ok=True)
            except OSError as exc:
                logger.warning("Could not delete temporary file: %s", exc)


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "ATS Hiring Agent API",
        "timestamp": datetime.now().isoformat(),
    }


def open_browser(url: str, delay: float = 1.5) -> None:
    import time

    time.sleep(delay)
    try:
        webbrowser.open(url)
        logger.info("Browser opened at %s", url)
    except OSError as exc:
        logger.warning("Could not open browser automatically: %s", exc)


if __name__ == "__main__":
    url = f"http://localhost:{PORT}"

    if OPEN_BROWSER:
        Thread(target=open_browser, args=(url,), daemon=True).start()

    logger.info("Starting ATS Hiring Agent on %s", url)
    uvicorn.run(app, host=HOST, port=PORT, log_level=LOG_LEVEL.lower())
