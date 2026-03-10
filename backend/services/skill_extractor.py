"""
skill_extractor.py
Extracts skills from resume text using keyword matching.
No paid API required — uses a comprehensive local skills dictionary.
"""
import re

# ── Master Skills Database ──
SKILLS_DB = {
    # Programming Languages
    "python", "java", "javascript", "typescript", "c", "c++", "c#", "go", "rust",
    "kotlin", "swift", "ruby", "php", "scala", "r", "matlab", "perl", "dart",
    # Web Frontend
    "html", "css", "react", "vue", "angular", "nextjs", "nuxt", "svelte",
    "tailwind", "bootstrap", "sass", "less", "jquery", "webpack", "vite",
    # Web Backend
    "nodejs", "express", "fastapi", "django", "flask", "spring", "laravel",
    "rails", "nestjs", "graphql", "rest", "restful", "api",
    # Databases
    "sql", "mysql", "postgresql", "sqlite", "mongodb", "redis", "cassandra",
    "elasticsearch", "dynamodb", "firebase", "supabase", "oracle",
    # Cloud & DevOps
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ansible",
    "jenkins", "github actions", "ci/cd", "linux", "bash", "shell scripting",
    "nginx", "apache",
    # AI / ML / Data
    "machine learning", "deep learning", "nlp", "computer vision",
    "tensorflow", "pytorch", "scikit-learn", "keras", "pandas", "numpy",
    "matplotlib", "seaborn", "huggingface", "langchain", "openai",
    "data analysis", "data visualization", "power bi", "tableau",
    "excel", "statistics", "hadoop", "spark", "airflow",
    # Mobile
    "android", "ios", "flutter", "react native", "xamarin",
    # Tools & Practices
    "git", "github", "gitlab", "bitbucket", "jira", "agile", "scrum",
    "figma", "postman", "linux", "vs code", "jupyter",
    # Soft Skills (bonus detection)
    "communication", "leadership", "teamwork", "problem solving",
    "critical thinking", "project management",
}

# Skills that suggest a specific career role
ROLE_SKILL_MAP = {
    "Frontend Developer":   {"react","vue","angular","html","css","javascript","typescript","nextjs"},
    "Backend Developer":    {"python","nodejs","fastapi","django","flask","java","spring","sql","postgresql"},
    "Full Stack Developer": {"react","nodejs","mongodb","python","javascript","html","css"},
    "AI/ML Engineer":       {"python","machine learning","deep learning","tensorflow","pytorch","scikit-learn","nlp"},
    "Data Scientist":       {"python","pandas","numpy","statistics","machine learning","data analysis","sql","jupyter"},
    "Data Analyst":         {"sql","excel","power bi","tableau","python","data analysis","statistics"},
    "Cloud Engineer":       {"aws","azure","gcp","docker","kubernetes","terraform","linux"},
    "DevOps Engineer":      {"docker","kubernetes","jenkins","ci/cd","linux","bash","aws","terraform"},
    "Cybersecurity":        {"linux","networking","python","bash","security","penetration testing"},
}

# Skills that indicate experience level
BEGINNER_MARKERS    = {"html","css","python","java","javascript","git","sql"}
INTERMEDIATE_MARKERS= {"react","nodejs","django","fastapi","docker","aws","postgresql"}
ADVANCED_MARKERS    = {"kubernetes","terraform","machine learning","deep learning","system design","microservices"}


def extract_skills(text: str) -> list[str]:
    """Return list of skills found in resume text."""
    text_lower = text.lower()
    found = []
    for skill in SKILLS_DB:
        # Use word boundary matching for short skills to avoid false positives
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            found.append(skill.title())
    return sorted(set(found))


def detect_missing_skills(found_skills: list[str], career_goal: str | None = None) -> list[str]:
    """
    Given found skills, suggest missing important skills.
    If a career_goal is given, focus on that domain.
    """
    found_lower = {s.lower() for s in found_skills}
    missing = []

    # Core skills every developer should have
    core_skills = {"git", "python", "sql", "linux", "docker"}
    for s in core_skills:
        if s not in found_lower:
            missing.append(s.title())

    # Role-specific missing skills
    if career_goal:
        for role, skills in ROLE_SKILL_MAP.items():
            if career_goal.lower() in role.lower():
                for s in skills:
                    if s not in found_lower:
                        missing.append(s.title())
                break

    # Deduplicate & limit
    return list(dict.fromkeys(missing))[:10]


def recommend_roles(found_skills: list[str]) -> list[str]:
    """Recommend job roles based on detected skills."""
    found_lower = {s.lower() for s in found_skills}
    scores = {}
    for role, skills in ROLE_SKILL_MAP.items():
        match_count = len(found_lower & skills)
        if match_count > 0:
            scores[role] = match_count / len(skills)

    # Sort by match score, return top 4
    sorted_roles = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [role for role, _ in sorted_roles[:4]]


def detect_experience_level(found_skills: list[str]) -> tuple[int, str]:
    """Return estimated years of experience and label."""
    found_lower = {s.lower() for s in found_skills}
    adv = len(found_lower & ADVANCED_MARKERS)
    mid = len(found_lower & INTERMEDIATE_MARKERS)

    if adv >= 2:
        return 2, "Mid-Senior"
    elif mid >= 3:
        return 1, "Intermediate"
    else:
        return 0, "Fresher/Junior"