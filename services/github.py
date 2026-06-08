"""GitHub profile and repository enrichment for resume evaluation."""

import json
import logging
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from prompts.template_manager import TemplateManager
from services.config import CACHE_DIR, DEVELOPMENT_MODE
from services.llm_utils import extract_json_from_response, initialize_llm_provider
from services.models import GitHubProfile
from services.prompt import DEFAULT_MODEL, MODEL_PARAMETERS

logger = logging.getLogger(__name__)

MIN_AUTHOR_COMMITS = 4
MAX_SELECTED_PROJECTS = 7


def _create_cache_filename(api_url: str, params: dict = None) -> str:
    url_parts = api_url.replace("https://api.github.com/", "").replace("/", "_")
    if params:
        param_str = "_".join([f"{k}_{v}" for k, v in sorted(params.items())])
        filename = f"gh_githubcache_{url_parts}_{param_str}.json"
    else:
        filename = f"gh_githubcache_{url_parts}.json"
    return str(CACHE_DIR / filename)


def _fetch_github_api(api_url, params=None):
    headers = {}
    github_token = os.environ.get("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    cache_filename = _create_cache_filename(api_url, params)
    if DEVELOPMENT_MODE and os.path.exists(cache_filename):
        logger.info("Loading cached GitHub data from %s", cache_filename)
        try:
            cached_data = json.loads(Path(cache_filename).read_text(encoding="utf-8"))
            return 200, cached_data
        except OSError as exc:
            logger.warning("Error reading cache file %s: %s", cache_filename, exc)

    response = requests.get(api_url, params, timeout=10, headers=headers)
    status_code = response.status_code

    rate_limit_remaining = response.headers.get("X-RateLimit-Remaining")
    rate_limit_limit = response.headers.get("X-RateLimit-Limit")
    rate_limit_reset = response.headers.get("X-RateLimit-Reset")

    if rate_limit_remaining is not None and rate_limit_limit is not None:
        remaining = int(rate_limit_remaining)
        limit = int(rate_limit_limit)

        if remaining < 10 and rate_limit_reset:
            reset_timestamp = int(rate_limit_reset)
            wait_seconds = max(0, reset_timestamp - int(time.time())) + 5
            reset_time = datetime.fromtimestamp(reset_timestamp)
            logger.warning(
                "GitHub API rate limit low: %s/%s. Resets at %s",
                remaining,
                limit,
                reset_time,
            )
            if not github_token:
                logger.info(
                    "Set GITHUB_TOKEN in .env to increase rate limits (60/hour to 5000/hour)"
                )
            if 0 < wait_seconds <= 3600:
                logger.info("Sleeping %s seconds until rate limit resets", wait_seconds)
                time.sleep(wait_seconds)

    data = response.json() if response.status_code == 200 else {}

    if DEVELOPMENT_MODE and status_code == 200:
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            Path(cache_filename).write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("Error caching GitHub data to %s: %s", cache_filename, exc)

    return status_code, data


def extract_github_username(github_url: str) -> Optional[str]:
    if not github_url:
        return None

    github_url = github_url.replace(" ", "").strip()
    patterns = [
        r"https?://github\.com/([^/]+)",
        r"github\.com/([^/]+)",
        r"@([^/]+)",
        r"^([a-zA-Z0-9-]+)$",
    ]

    for pattern in patterns:
        match = re.search(pattern, github_url)
        if match:
            username = match.group(1)
            if "?" in username:
                username = username.split("?", 1)[0]
            return username
    return None


def find_github_profile_url(parsed_resume) -> Optional[str]:
    """Extract GitHub profile URL from parsed resume basics."""
    if not parsed_resume or not getattr(parsed_resume, "basics", None):
        return None

    profiles = parsed_resume.basics.profiles or []
    for profile in profiles:
        network = (profile.network or "").lower()
        url = profile.url or ""
        if "github" in network or "github.com" in url.lower():
            return url
    return None


def fetch_github_profile(github_url: str) -> Optional[GitHubProfile]:
    try:
        username = extract_github_username(github_url)
        if not username:
            logger.warning("Could not extract username from: %s", github_url)
            return None

        status_code, data = _fetch_github_api(f"https://api.github.com/users/{username}")

        if status_code == 200:
            return GitHubProfile(
                username=username,
                name=data.get("name"),
                bio=data.get("bio"),
                location=data.get("location"),
                company=data.get("company"),
                public_repos=data.get("public_repos"),
                followers=data.get("followers"),
                following=data.get("following"),
                created_at=data.get("created_at"),
                updated_at=data.get("updated_at"),
                avatar_url=data.get("avatar_url"),
                blog=data.get("blog"),
                twitter_username=data.get("twitter_username"),
                hireable=data.get("hireable"),
            )
        if status_code == 404:
            logger.warning("GitHub user not found: %s", username)
        else:
            logger.warning("GitHub API error: %s - %s", status_code, data)
        return None
    except requests.exceptions.RequestException as exc:
        logger.error("Error fetching GitHub profile: %s", exc)
        return None


def fetch_contributions_count(owner: str, contributors_data):
    user_contributions = 0
    total_contributions = 0
    for contributor in contributors_data:
        if isinstance(contributor, dict):
            contributions = contributor.get("contributions", 0)
            total_contributions += contributions
            if contributor.get("login", "").lower() == owner.lower():
                user_contributions = contributions
    return user_contributions, total_contributions


def fetch_repo_contributors(owner: str, repo_name: str) -> list:
    try:
        status_code, contributors_data = _fetch_github_api(
            f"https://api.github.com/repos/{owner}/{repo_name}/contributors"
        )
        return contributors_data if status_code == 200 else []
    except Exception as exc:
        logger.error("Error fetching contributors for %s/%s: %s", owner, repo_name, exc)
        return []


def fetch_all_github_repos(github_url: str, max_repos: int = 100) -> List[Dict]:
    try:
        username = extract_github_username(github_url)
        if not username:
            return []

        params = {"sort": "updated", "per_page": min(max_repos, 100), "type": "all"}
        status_code, repos_data = _fetch_github_api(
            f"https://api.github.com/users/{username}/repos", params=params
        )

        if status_code != 200:
            logger.warning("GitHub repos API error: %s", status_code)
            return []

        projects = []
        for repo in repos_data:
            if repo.get("fork") and repo.get("forks_count", 0) < 5:
                continue

            repo_name = repo.get("name")
            contributors_data = fetch_repo_contributors(username, repo_name)
            contributor_count = len(contributors_data)
            user_contributions, total_contributions = fetch_contributions_count(
                username, contributors_data
            )
            project_type = "open_source" if contributor_count > 1 else "self_project"

            projects.append(
                {
                    "name": repo.get("name"),
                    "description": repo.get("description"),
                    "github_url": repo.get("html_url"),
                    "live_url": repo.get("homepage") or None,
                    "technologies": [repo.get("language")] if repo.get("language") else [],
                    "project_type": project_type,
                    "contributor_count": contributor_count,
                    "author_commit_count": user_contributions,
                    "total_commit_count": total_contributions,
                    "github_details": {
                        "stars": repo.get("stargazers_count", 0),
                        "forks": repo.get("forks_count", 0),
                        "language": repo.get("language"),
                        "description": repo.get("description"),
                        "created_at": repo.get("created_at"),
                        "updated_at": repo.get("updated_at"),
                        "topics": repo.get("topics", []),
                        "open_issues": repo.get("open_issues_count", 0),
                        "size": repo.get("size", 0),
                        "fork": repo.get("fork", False),
                        "archived": repo.get("archived", False),
                        "default_branch": repo.get("default_branch"),
                        "contributors": contributor_count,
                    },
                }
            )

        projects.sort(
            key=lambda x: x.get("author_commit_count", 0), reverse=True
        )
        logger.info(
            "Found %s repositories (%s open source, %s self projects)",
            len(projects),
            sum(1 for p in projects if p["project_type"] == "open_source"),
            sum(1 for p in projects if p["project_type"] == "self_project"),
        )
        return projects
    except Exception as exc:
        logger.error("Error fetching GitHub repositories: %s", exc)
        return []


def generate_profile_json(profile: GitHubProfile) -> Dict:
    if not profile:
        return {}
    return profile.model_dump()


def _prepare_projects_for_selection(projects: List[Dict]) -> List[Dict]:
    """Filter and sort projects per github_project_selection.jinja rules."""
    prepared = []
    for project in projects:
        commit_count = project.get("author_commit_count", 0) or 0
        if commit_count < MIN_AUTHOR_COMMITS:
            continue
        prepared.append(
            {
                "name": project.get("name"),
                "description": project.get("description"),
                "github_url": project.get("github_url"),
                "live_url": project.get("live_url"),
                "technologies": project.get("technologies", []),
                "project_type": project.get("project_type", "self_project"),
                "contributor_count": project.get("contributor_count", 1),
                "author_commit_count": commit_count,
                "total_commit_count": project.get("total_commit_count", 0),
                "github_details": project.get("github_details", {}),
            }
        )

    prepared.sort(key=lambda x: x["author_commit_count"], reverse=True)
    return prepared


def _merge_project_fields(selected: Dict, source: Dict) -> Dict:
    """Fill missing fields on LLM output from the source project record."""
    merged = {**source, **{k: v for k, v in selected.items() if v is not None}}
    if not merged.get("project_type"):
        merged["project_type"] = source.get("project_type", "self_project")
    if not merged.get("contributor_count"):
        merged["contributor_count"] = source.get("contributor_count", 1)
    return merged


def _validate_selected_projects(
    selected: List[Dict], source_by_name: Dict[str, Dict]
) -> List[Dict]:
    """Enforce template hard requirements: unique names, min commits, max 7."""
    validated = []
    seen_names = set()

    for project in selected:
        name = project.get("name", "")
        if not name or name in seen_names:
            continue

        source = source_by_name.get(name, {})
        commit_count = project.get("author_commit_count") or source.get(
            "author_commit_count", 0
        )
        if commit_count < MIN_AUTHOR_COMMITS:
            logger.debug("Skipping %s: only %s commits", name, commit_count)
            continue

        seen_names.add(name)
        validated.append(_merge_project_fields(project, source))

        if len(validated) >= MAX_SELECTED_PROJECTS:
            break

    return validated


def _fallback_project_selection(qualified: List[Dict]) -> List[Dict]:
    """Select top projects by commit count when LLM selection fails."""
    return qualified[:MAX_SELECTED_PROJECTS]


def generate_projects_json(projects: List[Dict]) -> List[Dict]:
    if not projects:
        return []

    qualified = _prepare_projects_for_selection(projects)
    if not qualified:
        logger.info(
            "No repositories with %s+ author commits found", MIN_AUTHOR_COMMITS
        )
        return []

    source_by_name = {p["name"]: p for p in qualified if p.get("name")}

    try:
        template_manager = TemplateManager()
        projects_json = json.dumps(qualified, indent=2)
        prompt = template_manager.render_template(
            "github_project_selection", projects_data=projects_json
        )
        if not prompt:
            return _fallback_project_selection(qualified)

        provider = initialize_llm_provider(DEFAULT_MODEL)
        model_params = MODEL_PARAMETERS.get(
            DEFAULT_MODEL, {"temperature": 0.1, "top_p": 0.9}
        )
        response = provider.chat(
            model=DEFAULT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Respond only with valid JSON. No markdown or explanation.",
                },
                {"role": "user", "content": prompt},
            ],
            options=model_params,
        )

        response_text = extract_json_from_response(response["message"]["content"])
        selected_projects = json.loads(response_text)
        if not isinstance(selected_projects, list):
            raise ValueError("LLM response is not a JSON array")

        validated = _validate_selected_projects(selected_projects, source_by_name)
        if validated:
            logger.info(
                "LLM selected %s qualifying GitHub projects (4+ commits each)",
                len(validated),
            )
            return validated

        logger.warning("LLM returned no qualifying projects, using commit-based fallback")
        return _fallback_project_selection(qualified)

    except Exception as exc:
        logger.warning("LLM project selection failed, using commit-based fallback: %s", exc)
        return _fallback_project_selection(qualified)


def fetch_and_display_github_info(github_url: str) -> Dict[str, Any]:
    """Fetch profile, repos, rank top projects, and return structured data."""
    logger.info("Fetching GitHub data for %s", github_url)
    github_profile = fetch_github_profile(github_url)
    if not github_profile:
        return {}

    projects = fetch_all_github_repos(github_url)
    return {
        "profile": generate_profile_json(github_profile),
        "projects": generate_projects_json(projects),
        "total_projects": len(projects),
    }
