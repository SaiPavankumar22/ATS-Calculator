"""
Template Manager for Section Extraction

This module provides functionality to load and render Jinja templates for
section-specific resume extraction prompts.
"""

import logging
from pathlib import Path
from typing import Dict, Optional

from jinja2 import Environment, FileSystemLoader, Template

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATE_DIR = str(PROJECT_ROOT / "prompts" / "templates")


class TemplateManager:
    """Loads and renders Jinja templates for resume extraction and evaluation."""

    def __init__(self, template_dir: str = DEFAULT_TEMPLATE_DIR):
        self.template_dir = template_dir
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._templates: Dict[str, Template] = {}
        self._load_templates()

    def _load_templates(self):
        template_files = {
            "basics": "basics.jinja",
            "work": "work.jinja",
            "education": "education.jinja",
            "skills": "skills.jinja",
            "projects": "projects.jinja",
            "awards": "awards.jinja",
            "system_message": "system_message.jinja",
            "resume_evaluation_criteria": "resume_evaluation_criteria.jinja",
            "resume_evaluation_system_message": "resume_evaluation_system_message.jinja",
            "jd_matching_criteria": "jd_matching_criteria.jinja",
            "jd_matching_system_message": "jd_matching_system_message.jinja",
        }

        for section_name, filename in template_files.items():
            try:
                template_path = Path(self.template_dir) / filename
                if template_path.exists():
                    self._templates[section_name] = self.env.get_template(filename)
                else:
                    logger.warning("Template file not found: %s", template_path)
            except Exception as exc:
                logger.error("Error loading template %s: %s", filename, exc)

    def get_available_sections(self) -> list:
        return list(self._templates.keys())

    def render_template(self, section_name: str, **kwargs) -> Optional[str]:
        if section_name not in self._templates:
            logger.error(
                "Template not found for section: %s (available: %s)",
                section_name,
                self.get_available_sections(),
            )
            return None

        try:
            return self._templates[section_name].render(**kwargs)
        except Exception as exc:
            logger.error("Error rendering template for %s: %s", section_name, exc)
            return None
