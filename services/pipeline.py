"""Shared resume evaluation pipeline used by the web app and CLI."""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from services.config import CACHE_DIR, DEVELOPMENT_MODE
from services.evaluator import ResumeEvaluator
from services.github import fetch_and_display_github_info, find_github_profile_url
from services.jd_matcher import JDMatcher
from services.models import EvaluationData, JSONResume
from services.pdf import PDFHandler
from services.prompt import DEFAULT_MODEL, MODEL_PARAMETERS
from services.resume_text import build_evaluation_text

logger = logging.getLogger(__name__)

RAW_MAX_SCORE = 120


def normalize_final_score(raw_score: float) -> int:
    """Convert internal rubric score (0-120) to ATS display score (1-100)."""
    clamped = max(0, min(RAW_MAX_SCORE, raw_score))
    normalized = round((clamped / RAW_MAX_SCORE) * 99) + 1
    return max(1, min(100, normalized))


def calculate_raw_score(evaluation: EvaluationData) -> float:
    scores = evaluation.scores
    return (
        scores.open_source.score
        + scores.self_projects.score
        + scores.production.score
        + scores.technical_skills.score
        + evaluation.bonus_points.total
        - evaluation.deductions.total
    )


def fetch_github_data(parsed_resume: Optional[JSONResume]) -> Dict[str, Any]:
    """Fetch and optionally cache GitHub enrichment data."""
    github_url = find_github_profile_url(parsed_resume)
    if not github_url:
        return {}

    cache_key = github_url.replace("https://", "").replace("/", "_")
    cache_file = CACHE_DIR / f"githubcache_{cache_key}.json"

    if DEVELOPMENT_MODE and cache_file.exists():
        logger.info("Loading cached GitHub data from %s", cache_file)
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not read GitHub cache: %s", exc)

    try:
        github_data = fetch_and_display_github_info(github_url)
    except Exception as exc:
        logger.warning("GitHub enrichment failed: %s", exc)
        return {}

    if DEVELOPMENT_MODE and github_data:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(
            json.dumps(github_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    return github_data or {}


def evaluate_resume_pipeline(
    resume_text: str,
    parsed_resume: Optional[JSONResume],
    job_description: Optional[str] = None,
    include_github: bool = True,
) -> Tuple[EvaluationData, Optional[Any], Dict[str, Any]]:
    """
    Run the full evaluation pipeline:
    1. Optional GitHub enrichment
    2. Resume scoring with enriched text
    3. Optional JD matching
    """
    github_data: Dict[str, Any] = {}
    if include_github and parsed_resume:
        github_data = fetch_github_data(parsed_resume)

    evaluation_text = build_evaluation_text(resume_text, parsed_resume, github_data)
    evaluator = ResumeEvaluator(
        model_name=DEFAULT_MODEL,
        model_params=MODEL_PARAMETERS.get(DEFAULT_MODEL),
    )
    evaluation = evaluator.evaluate_resume(evaluation_text)

    jd_score = None
    if job_description and job_description.strip():
        try:
            jd_matcher = JDMatcher()
            parsed_resume_dict = (
                parsed_resume.model_dump() if parsed_resume else None
            )
            jd_score = jd_matcher.match_resume_to_jd(
                evaluation_text, job_description, parsed_resume_dict
            )
        except Exception as exc:
            logger.warning("JD matching failed (continuing anyway): %s", exc)

    return evaluation, jd_score, github_data


def parse_pdf(pdf_path: str) -> Tuple[Optional[str], Optional[JSONResume]]:
    """Extract text and structured resume from a PDF, with optional caching."""
    cache_file = CACHE_DIR / f"resumecache_{Path(pdf_path).stem}.json"

    if DEVELOPMENT_MODE and cache_file.exists():
        logger.info("Loading cached resume data from %s", cache_file)
        try:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            return None, JSONResume(**cached)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not read resume cache: %s", exc)

    pdf_handler = PDFHandler()
    resume_text = pdf_handler.extract_text_from_pdf(pdf_path)
    if not resume_text:
        return None, None

    parsed_resume = pdf_handler.extract_json_from_text(resume_text)

    if DEVELOPMENT_MODE and parsed_resume:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(
            json.dumps(parsed_resume.model_dump(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    return resume_text, parsed_resume
