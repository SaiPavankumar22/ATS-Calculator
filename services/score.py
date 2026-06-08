"""
CLI entry point for resume scoring.

Usage:
    python -m services.score path/to/resume.pdf
"""

import logging
import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from services.pipeline import (
    calculate_raw_score,
    evaluate_resume_pipeline,
    normalize_final_score,
    parse_pdf,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def print_evaluation_results(evaluation, candidate_name: str = "Candidate") -> None:
    raw_score = calculate_raw_score(evaluation)
    display_score = normalize_final_score(raw_score)

    print("\n" + "=" * 80)
    print(f"RESUME EVALUATION RESULTS FOR: {candidate_name}")
    print("=" * 80)
    print(f"\nOVERALL SCORE: {display_score}/100 (raw: {raw_score:.1f}/120)")

    scores = evaluation.scores
    categories = [
        ("Open Source", scores.open_source),
        ("Self Projects", scores.self_projects),
        ("Production", scores.production),
        ("Technical Skills", scores.technical_skills),
    ]

    print("\nDETAILED SCORES:")
    print("-" * 60)
    for label, cat in categories:
        print(f"{label}: {cat.score}/{cat.max}")
        print(f"   Evidence: {cat.evidence}\n")

    if evaluation.bonus_points.total:
        print(f"BONUS POINTS: +{evaluation.bonus_points.total}")
        print(f"   {evaluation.bonus_points.breakdown}")

    if evaluation.deductions.total:
        print(f"DEDUCTIONS: -{evaluation.deductions.total}")
        print(f"   {evaluation.deductions.reasons}")

    if evaluation.key_strengths:
        print("\nKEY STRENGTHS:")
        for i, strength in enumerate(evaluation.key_strengths, 1):
            print(f"  {i}. {strength}")

    if evaluation.areas_for_improvement:
        print("\nAREAS FOR IMPROVEMENT:")
        for i, area in enumerate(evaluation.areas_for_improvement, 1):
            print(f"  {i}. {area}")

    print("\n" + "=" * 80)


def main(pdf_path: str):
    resume_text, parsed_resume = parse_pdf(pdf_path)
    if not parsed_resume:
        logger.error("Failed to parse resume from %s", pdf_path)
        return None

    if not resume_text:
        from services.pdf import PDFHandler

        resume_text = PDFHandler().extract_text_from_pdf(pdf_path) or ""

    evaluation, _, github_data = evaluate_resume_pipeline(
        resume_text=resume_text,
        parsed_resume=parsed_resume,
        include_github=True,
    )

    candidate_name = os.path.basename(pdf_path).replace(".pdf", "")
    if parsed_resume.basics and parsed_resume.basics.name:
        candidate_name = parsed_resume.basics.name

    if github_data:
        project_count = len(github_data.get("projects") or [])
        print(
            f"GitHub enrichment: {project_count} ranked projects "
            f"(4+ commits each) included in evaluation"
        )

    print_evaluation_results(evaluation, candidate_name)
    return evaluation


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m services.score <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not os.path.exists(pdf_path):
        print(f"Error: File '{pdf_path}' does not exist.")
        sys.exit(1)

    main(pdf_path)
