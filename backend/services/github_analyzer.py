"""
github_analyzer.py
Fetches and analyzes a GitHub profile using the free GitHub REST API.
No token required for public profiles (60 requests/hour unauthenticated).
With a token: 5000 requests/hour.
"""
import httpx
from datetime import datetime, timezone

GITHUB_API = "https://api.github.com"

# Tech stack detection from repo topics/languages/names
TECH_INDICATORS = {
    "React": ["react", "reactjs", "react-app"],
    "Vue":   ["vue", "vuejs", "nuxt"],
    "Angular": ["angular", "angularjs"],
    "Node.js": ["nodejs", "node", "express"],
    "Django": ["django"],
    "FastAPI": ["fastapi"],
    "Flask":  ["flask"],
    "Docker": ["docker", "dockerfile", "containerization"],
    "Kubernetes": ["kubernetes", "k8s", "helm"],
    "AWS":    ["aws", "lambda", "s3", "ec2"],
    "Machine Learning": ["ml", "machine-learning", "sklearn", "pytorch", "tensorflow"],
    "Data Science": ["data-science", "pandas", "numpy", "jupyter"],
    "CI/CD": ["github-actions", "jenkins", "ci-cd", "devops"],
    "GraphQL": ["graphql", "apollo"],
    "MongoDB": ["mongodb", "mongoose"],
    "PostgreSQL": ["postgresql", "postgres"],
    "Redis": ["redis"],
    "Blockchain": ["blockchain", "web3", "solidity"],
    "Android": ["android", "kotlin"],
    "iOS": ["ios", "swift"],
}


async def fetch_github_profile(username: str, token: str | None = None) -> dict:
    """
    Fetches full GitHub profile analysis.
    Returns structured data for the frontend.
    """
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(timeout=15.0) as client:

        # 1. User profile
        user_res = await client.get(f"{GITHUB_API}/users/{username}", headers=headers)
        if user_res.status_code == 404:
            raise ValueError(f"GitHub user '{username}' not found.")
        if user_res.status_code == 403:
            raise ValueError("GitHub API rate limit exceeded. Please try again later.")
        user_res.raise_for_status()
        user = user_res.json()

        # 2. Repos (up to 100)
        repos_res = await client.get(
            f"{GITHUB_API}/users/{username}/repos",
            headers=headers,
            params={"sort": "updated", "per_page": 100, "type": "owner"}
        )
        repos_res.raise_for_status()
        repos = repos_res.json()

    # ── Analyze ──
    return _analyze(user, repos)


def _analyze(user: dict, repos: list) -> dict:
    username     = user.get("login", "")
    public_repos = user.get("public_repos", 0)
    followers    = user.get("followers", 0)
    following    = user.get("following", 0)
    created_at   = user.get("created_at", "")

    # Account age in years
    if created_at:
        try:
            created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            account_age_years = (datetime.now(timezone.utc) - created).days / 365
        except Exception:
            account_age_years = 0
    else:
        account_age_years = 0

    # ── Language aggregation ──
    lang_counts: dict[str, int] = {}
    for repo in repos:
        if repo.get("language"):
            lang = repo["language"]
            lang_counts[lang] = lang_counts.get(lang, 0) + 1

    # ── Total stars & forks ──
    total_stars = sum(r.get("stargazers_count", 0) for r in repos)
    total_forks = sum(r.get("forks_count", 0) for r in repos)

    # ── Tech stack from repo names, descriptions, topics ──
    combined_text = " ".join([
        (r.get("name") or "").lower() + " " +
        (r.get("description") or "").lower()
        for r in repos
    ])
    tech_stack = []
    for tech, keywords in TECH_INDICATORS.items():
        if any(kw in combined_text for kw in keywords):
            tech_stack.append(tech)
    # Also add top languages
    for lang in list(lang_counts.keys())[:5]:
        if lang not in tech_stack:
            tech_stack.append(lang)

    # ── Top repos with scoring ──
    top_repos = []
    for repo in sorted(repos, key=lambda r: r.get("stargazers_count", 0), reverse=True)[:8]:
        score = _score_repo(repo)
        updated = repo.get("pushed_at", "")
        if updated:
            try:
                dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                updated = dt.strftime("%b %Y")
            except Exception:
                updated = ""
        top_repos.append({
            "name":        repo.get("name", ""),
            "description": (repo.get("description") or "")[:100],
            "language":    repo.get("language", ""),
            "stars":       repo.get("stargazers_count", 0),
            "forks":       repo.get("forks_count", 0),
            "score":       score,
            "updated":     updated,
        })

    # ── Overall score ──
    overall_score = _calculate_overall_score(
        public_repos, followers, total_stars, lang_counts, account_age_years, user
    )

    # ── Recruiter attractiveness score ──
    recruiter_score = _calculate_recruiter_score(
        public_repos, followers, total_stars, user, len(tech_stack)
    )

    # ── Suggestions ──
    suggestions = _generate_suggestions(user, public_repos, followers, total_stars, lang_counts)

    # ── Missing skills ──
    missing_skills = _detect_missing_skills(lang_counts, tech_stack)

    return {
        "username":       username,
        "name":           user.get("name") or username,
        "bio":            user.get("bio") or "",
        "avatar_url":     user.get("avatar_url") or "",
        "location":       user.get("location") or "",
        "blog":           user.get("blog") or "",
        "public_repos":   public_repos,
        "followers":      followers,
        "following":      following,
        "total_stars":    total_stars,
        "total_forks":    total_forks,
        "languages":      lang_counts,
        "tech_stack":     tech_stack[:12],
        "top_repos":      top_repos,
        "overall_score":  overall_score,
        "recruiter_score":recruiter_score,
        "suggestions":    suggestions,
        "missing_skills": missing_skills,
        "account_age_years": round(account_age_years, 1),
    }


def _score_repo(repo: dict) -> int:
    """Score a single repo 0-100."""
    score = 0
    score += min(repo.get("stargazers_count", 0) * 5, 30)   # Stars (max 30)
    score += min(repo.get("forks_count", 0) * 3, 15)         # Forks (max 15)
    if repo.get("description"):     score += 15              # Has description
    if repo.get("language"):        score += 10              # Has language
    if not repo.get("fork"):        score += 10              # Original (not a fork)
    if repo.get("topics"):          score += 10              # Has topics/tags
    if repo.get("license"):         score += 10              # Has license
    return min(score, 100)


def _calculate_overall_score(repos, followers, stars, langs, age, user) -> int:
    score = 0
    score += min(repos / 20 * 25, 25)        # repos (max 25)
    score += min(followers / 100 * 20, 20)   # followers (max 20)
    score += min(stars / 50 * 20, 20)        # stars (max 20)
    score += min(len(langs) / 4 * 15, 15)    # language diversity (max 15)
    if user.get("bio"):        score += 5
    if user.get("blog"):       score += 5
    if user.get("location"):   score += 5
    score += min(age / 3 * 5, 5)             # account age (max 5)
    return min(round(score), 100)


def _calculate_recruiter_score(repos, followers, stars, user, tech_count) -> int:
    score = 0
    score += min(repos / 15 * 25, 25)
    score += min(followers / 50 * 20, 20)
    score += min(stars / 30 * 20, 20)
    score += min(tech_count / 5 * 15, 15)
    if user.get("bio"):      score += 5
    if user.get("blog"):     score += 5
    if user.get("email"):    score += 5
    if user.get("location"): score += 5
    if user.get("company"):  score += 5
    return min(round(score), 100)


def _generate_suggestions(user, repos, followers, stars, langs) -> list[str]:
    tips = []
    if not user.get("bio"):
        tips.append("Add a bio to your profile — it's the first thing recruiters read.")
    if not user.get("blog"):
        tips.append("Add your portfolio/LinkedIn URL to the website field.")
    if not user.get("location"):
        tips.append("Add your location to appear in location-based recruiter searches.")
    if repos < 6:
        tips.append(f"You have only {repos} repos. Aim for 10+ to show consistent activity.")
    if repos > 0 and stars == 0:
        tips.append("Pin your best projects and add README files to attract stars.")
    if len(langs) < 2:
        tips.append("Explore multiple programming languages to broaden your skill profile.")
    if followers < 10:
        tips.append("Engage with the community — follow developers, star useful repos, contribute to open source.")
    if repos > 5:
        tips.append("Add descriptive READMEs with screenshots to your top projects.")
        tips.append("Include topics/tags on your repositories to improve discoverability.")
    if not tips:
        tips.append("Great profile! Keep contributing regularly to maintain momentum.")
    return tips[:6]


def _detect_missing_skills(langs: dict, tech_stack: list) -> list[str]:
    """Suggest skills missing from their stack."""
    missing = []
    tech_lower = [t.lower() for t in tech_stack]
    lang_lower = [l.lower() for l in langs.keys()]
    all_lower  = tech_lower + lang_lower

    core_missing = {
        "Docker":     "docker" not in all_lower,
        "CI/CD":      "ci/cd" not in all_lower and "github actions" not in all_lower,
        "SQL/Database": not any(db in all_lower for db in ["sql","postgresql","mongodb","mysql"]),
        "Testing":    not any(t in all_lower for t in ["test","pytest","jest","unittest"]),
        "Cloud (AWS/GCP/Azure)": not any(c in all_lower for c in ["aws","gcp","azure","cloud"]),
    }
    for skill, is_missing in core_missing.items():
        if is_missing:
            missing.append(skill)
    return missing[:6]