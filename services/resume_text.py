"""Convert structured resume and enrichment data to text for LLM evaluation."""

from typing import Dict, Optional

from services.models import JSONResume


def convert_json_resume_to_text(resume_data: JSONResume) -> str:
    """Convert parsed JSON resume to plain text for evaluation."""
    if not resume_data:
        return ""

    lines = ["=== RESUME DATA ==="]

    if resume_data.basics:
        basics = resume_data.basics
        lines.append(f"Name: {basics.name or 'N/A'}")
        if basics.email:
            lines.append(f"Email: {basics.email}")
        if basics.phone:
            lines.append(f"Phone: {basics.phone}")
        if basics.summary:
            lines.append(f"Summary: {basics.summary}")
        if basics.profiles:
            lines.append("Profiles:")
            for profile in basics.profiles:
                lines.append(f"  - {profile.network or 'Profile'}: {profile.url}")

    if resume_data.work:
        lines.append("\nWork Experience:")
        for job in resume_data.work:
            lines.append(
                f"- {job.position or 'Role'} at {job.name or 'Company'} "
                f"({job.startDate or '?'} - {job.endDate or 'Present'})"
            )
            if job.summary:
                lines.append(f"  {job.summary}")
            for highlight in job.highlights or []:
                lines.append(f"  • {highlight}")

    if resume_data.education:
        lines.append("\nEducation:")
        for edu in resume_data.education:
            lines.append(
                f"- {edu.studyType or ''} in {edu.area or ''} at "
                f"{edu.institution or 'Institution'} "
                f"({edu.startDate or '?'} - {edu.endDate or 'Present'})"
            )

    if resume_data.skills:
        lines.append("\nSkills:")
        for skill in resume_data.skills:
            keywords = ", ".join(skill.keywords or [])
            lines.append(f"- {skill.name or 'Skills'}: {keywords}")

    if resume_data.projects:
        lines.append("\nProjects:")
        for project in resume_data.projects:
            lines.append(f"- {project.name or 'Project'}")
            if project.description:
                lines.append(f"  {project.description}")
            if project.url:
                lines.append(f"  URL: {project.url}")
            if project.technologies:
                lines.append(f"  Tech: {', '.join(project.technologies)}")

    if resume_data.awards:
        lines.append("\nAwards:")
        for award in resume_data.awards:
            lines.append(f"- {award.title or 'Award'} ({award.date or 'N/A'})")

    return "\n".join(lines) + "\n"


def convert_github_data_to_text(github_data: dict) -> str:
    """Convert GitHub enrichment data to text block for evaluation."""
    if not github_data:
        return ""

    lines = ["\n=== GITHUB DATA ==="]

    profile = github_data.get("profile")
    if profile:
        lines.append("GitHub Profile:")
        lines.append(f"- Username: {profile.get('username', 'N/A')}")
        lines.append(f"- Name: {profile.get('name', 'N/A')}")
        lines.append(f"- Bio: {profile.get('bio', 'N/A')}")
        lines.append(f"- Public Repositories: {profile.get('public_repos', 'N/A')}")
        lines.append(f"- Followers: {profile.get('followers', 'N/A')}")
        lines.append(f"- Following: {profile.get('following', 'N/A')}")

    projects = github_data.get("projects") or []
    if projects:
        lines.append(f"\nGitHub Projects ({len(projects)} selected):")
        for index, project in enumerate(projects, 1):
            lines.append(f"{index}. {project.get('name', 'N/A')}")
            lines.append(f"   Type: {project.get('project_type', 'N/A')}")
            lines.append(f"   Description: {project.get('description', 'N/A')}")
            lines.append(f"   URL: {project.get('github_url', 'N/A')}")
            details = project.get("github_details") or {}
            lines.append(f"   Stars: {details.get('stars', 'N/A')}")
            lines.append(f"   Forks: {details.get('forks', 'N/A')}")
            lines.append(f"   Language: {details.get('language', 'N/A')}")
            lines.append(
                f"   Author commits: {project.get('author_commit_count', 'N/A')} / "
                f"{project.get('total_commit_count', 'N/A')}"
            )
            reason = project.get("reason_for_project_selection")
            if reason:
                lines.append(f"   Selection reason: {reason}")

    return "\n".join(lines) + "\n"


def build_evaluation_text(
    resume_text: str,
    parsed_resume: Optional[JSONResume] = None,
    github_data: Optional[dict] = None,
) -> str:
    """Build the full text payload sent to the resume evaluator."""
    if parsed_resume:
        text = convert_json_resume_to_text(parsed_resume)
    else:
        text = resume_text

    if github_data:
        text += convert_github_data_to_text(github_data)

    return text
