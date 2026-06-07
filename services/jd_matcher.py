"""
Job Description Matcher - Scores resume against job description.
Analyzes skill match, keyword presence, experience level, and overall relevance.
"""

import json
import logging
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from prompts.template_manager import TemplateManager
from services.llm_utils import extract_json_from_response, initialize_llm_provider
from services.prompt import DEFAULT_MODEL, MODEL_PARAMETERS

logger = logging.getLogger(__name__)


class SkillMatch(BaseModel):
    """Represents a skill match between resume and JD."""

    skill: str
    found_in_resume: bool
    importance: str = Field(description="required, nice_to_have, or bonus")
    confidence: int = Field(description="0-100 confidence score", ge=0, le=100)


class KeywordMatch(BaseModel):
    """Represents a keyword match."""

    keyword: str
    found_in_resume: bool
    frequency_in_jd: int = Field(ge=0)
    frequency_in_resume: int = Field(ge=0)


class JDMatchScore(BaseModel):
    """Overall JD match score result."""

    match_score: int = Field(description="Overall match score 0-100", ge=0, le=100)
    skill_match_percentage: int = Field(
        description="Percentage of required skills matched", ge=0, le=100
    )
    experience_match: int = Field(
        description="Experience level match 0-100", ge=0, le=100
    )
    keyword_match_percentage: int = Field(
        description="Percentage of key keywords found", ge=0, le=100
    )
    matched_skills: List[SkillMatch] = Field(description="Skills that matched")
    missing_skills: List[SkillMatch] = Field(description="Important missing skills")
    matched_keywords: List[KeywordMatch] = Field(description="Matched keywords")
    experience_summary: str = Field(description="Summary of experience match")
    strengths: List[str] = Field(description="Resume strengths for this JD")
    gaps: List[str] = Field(description="Resume gaps for this JD")
    recommendations: List[str] = Field(
        description="Recommendations to improve match"
    )


class JDMatcher:
    """Matches resume content against job description."""

    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.model_name = model_name
        self.model_params = MODEL_PARAMETERS.get(
            model_name, {"temperature": 0.1, "top_p": 0.9}
        )
        self.template_manager = TemplateManager()
        self.provider = initialize_llm_provider(model_name)

    def match_resume_to_jd(
        self,
        resume_text: str,
        job_description: str,
        parsed_resume: Optional[Dict] = None,
    ) -> JDMatchScore:
        """
        Match resume against job description and return detailed score.

        Args:
            resume_text: Full resume text content
            job_description: Job description text
            parsed_resume: Optional parsed resume data (unused, kept for API compat)

        Returns:
            JDMatchScore with detailed matching analysis
        """
        del parsed_resume  # reserved for future structured matching

        try:
            logger.info("Starting JD matching analysis...")

            system_message = self.template_manager.render_template(
                "jd_matching_system_message"
            )
            if not system_message:
                raise ValueError("Failed to load JD matching system message template")

            prompt = self.template_manager.render_template(
                "jd_matching_criteria",
                resume_text=resume_text,
                job_description=job_description,
            )
            if not prompt:
                raise ValueError("Failed to load JD matching criteria template")

            logger.debug("Calling %s for JD matching...", self.model_name)

            chat_params = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt},
                ],
                "options": {
                    "stream": False,
                    "temperature": self.model_params.get("temperature", 0.1),
                    "top_p": self.model_params.get("top_p", 0.9),
                },
            }

            kwargs = {"format": JDMatchScore.model_json_schema()}
            response = self.provider.chat(**chat_params, **kwargs)

            response_text = extract_json_from_response(response["message"]["content"])
            match_data = json.loads(response_text)
            jd_score = JDMatchScore(**match_data)

            logger.info("JD matching complete. Match score: %s", jd_score.match_score)
            return jd_score

        except json.JSONDecodeError as exc:
            logger.error("Error parsing JD matching response: %s", exc)
            raise
        except Exception as exc:
            logger.error("Error in JD matching: %s", exc)
            raise

    def get_match_percentage_color(self, score: int) -> str:
        """Get a color class for the match score."""
        if score >= 85:
            return "excellent"
        if score >= 70:
            return "good"
        if score >= 50:
            return "fair"
        return "poor"
