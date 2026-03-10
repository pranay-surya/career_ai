"""
linkedin_analyzer.py
Analyzes LinkedIn profile data (from manual input, PDF export, or pasted text).
Uses local scoring + Groq AI for headline suggestions and tips.
No LinkedIn API required.
"""
import re
import os
from services.skill_extractor import extract_skills, detect_missing_skills

# ── Section weights for overall score ──
WEIGHTS = {
    "headline":        15,
    "about":           15,
    "experience":      20,
    "education":       10,
    "skills":          15,
    "recommendations": 10,
    "connections":     10,
    "certifications":   5,
}

# Keywords that make a headline strong
POWER_HEADLINE_WORDS = [
    "engineer", "developer", "scientist", "analyst", "architect",
    "specialist", "expert", "lead", "senior", "intern", "fresher",
    "open to work", "seeking", "passionate", "building", "helping",
]

# About section quality indicators
ABOUT_QUALITY_WORDS = [
    "experience", "passionate", "specialize", "built", "developed",
    "worked", "skills", "project", "team", "impact", "result",
    "graduated", "currently", "looking", "open", "love", "focus",
]


def score_headline(headline: str) -> int:
    if not headline or len(headline.strip()) < 5:
        return 0
    score = 30  # base
    hl = headline.lower()
    # Length check (sweet spot: 60-120 chars)
    if 60 <= len(headline) <= 120:
        score += 25
    elif 30 <= len(headline) < 60:
        score += 15
    # Power words
    power_matches = sum(1 for w in POWER_HEADLINE_WORDS if w in hl)
    score += min(power_matches * 10, 30)
    # Has separator (|, ·, -)
    if any(sep in headline for sep in ["|", "·", "-", "/"]):
        score += 15
    return min(score, 100)


def score_about(about: str) -> int:
    if not about or len(about.strip()) < 20:
        return 0
    score = 20  # base
    words = about.split()
    # Length
    if len(words) >= 150:    score += 30
    elif len(words) >= 80:   score += 20
    elif len(words) >= 40:   score += 10
    # Quality words
    quality_matches = sum(1 for w in ABOUT_QUALITY_WORDS if w in about.lower())
    score += min(quality_matches * 5, 30)
    # Has numbers/metrics
    if re.search(r'\d+', about):
        score += 20
    return min(score, 100)


def score_experience(experience: str) -> int:
    if not experience or len(experience.strip()) < 10:
        return 0
    score = 20
    exp_lower = experience.lower()
    # Count job entries (look for common patterns)
    entries = len(re.findall(r'(at |@|\|)\s*[A-Z]|\b(20\d\d|19\d\d)\b', experience))
    score += min(entries * 15, 40)
    # Has bullet points or action verbs
    action_verbs = ["developed", "built", "led", "managed", "created", "designed",
                    "improved", "increased", "reduced", "delivered", "collaborated"]
    matches = sum(1 for v in action_verbs if v in exp_lower)
    score += min(matches * 5, 25)
    # Has metrics
    if re.search(r'\d+[%+]|\d+ (users|clients|projects|team)', exp_lower):
        score += 15
    return min(score, 100)


def score_skills(skills_str: str) -> int:
    if not skills_str:
        return 0
    skills = [s.strip() for s in re.split(r'[,\n]', skills_str) if s.strip()]
    count = len(skills)
    if count >= 15:  return 100
    if count >= 10:  return 80
    if count >= 5:   return 60
    if count >= 3:   return 40
    return 20


def score_education(education: str) -> int:
    if not education or len(education.strip()) < 5:
        return 30  # base — most people have education
    edu_lower = education.lower()
    score = 50
    if any(w in edu_lower for w in ["b.tech", "btech", "b.e", "bachelor", "b.sc", "bsc"]):
        score += 25
    if any(w in edu_lower for w in ["m.tech", "mtech", "master", "m.sc", "msc", "mba", "phd"]):
        score += 35
    if re.search(r'20\d\d', education):
        score += 10
    return min(score, 100)


def score_recommendations(count: int) -> int:
    if count >= 5:   return 100
    if count >= 3:   return 75
    if count >= 1:   return 50
    return 0


def extract_experience_entries(experience_text: str) -> list[dict]:
    """Parse experience text into structured entries."""
    entries = []
    if not experience_text:
        return entries

    lines = [l.strip() for l in experience_text.split('\n') if l.strip()]
    current = {}

    for line in lines:
        # Detect role line (short line with job title keywords)
        is_title = any(kw in line.lower() for kw in [
            "engineer", "developer", "intern", "analyst", "manager",
            "designer", "scientist", "consultant", "lead", "architect"
        ])
        # Detect duration
        has_date = bool(re.search(r'(20\d\d|19\d\d|present|current|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)', line, re.I))

        if is_title and len(line) < 80:
            if current:
                entries.append(current)
            current = {"title": line, "company": "", "duration": ""}
        elif has_date and current and not current.get("duration"):
            current["duration"] = line
        elif current and not current.get("company") and len(line) < 60:
            current["company"] = line

    if current:
        entries.append(current)

    return entries[:6]


def generate_headline_suggestions(name: str, headline: str, skills_str: str, experience: str, career_goal: str = "") -> list[str]:
    """Generate 3 improved headline options locally."""
    skills_list = [s.strip() for s in re.split(r'[,\n]', skills_str) if s.strip()][:3]
    skills_part = " | ".join(skills_list) if skills_list else ""

    # Detect seniority
    is_fresher = any(w in (experience or "").lower() for w in ["intern", "fresher", "student", "graduate"])
    level = "Fresher" if is_fresher else "Developer"

    goal = career_goal or (skills_list[0] + " Developer" if skills_list else "Software Developer")

    suggestions = []

    # Formula 1: Role | Skills | Status
    if skills_part:
        suggestions.append(f"Aspiring {goal} | {skills_part} | Open to Opportunities")
    # Formula 2: Passion-driven
    suggestions.append(f"Passionate {goal} | Building Scalable Solutions | Open to Work")
    # Formula 3: Value-focused
    if skills_list:
        suggestions.append(f"{goal} | {skills_list[0]} Enthusiast | Seeking Internship / Full-time Roles")
    # Formula 4: Achievement style
    suggestions.append(f"{goal} | Turning Ideas into Products | {skills_list[0] if skills_list else 'Tech'} & Beyond")

    return suggestions[:4]


def generate_action_tips(data: dict) -> list[str]:
    tips = []
    if not data.get("headline") or len(data.get("headline","")) < 30:
        tips.append("Add a keyword-rich headline (60–120 chars) — it's the most visible part of your profile.")
    if not data.get("about") or len(data.get("about","")) < 100:
        tips.append("Write a 150–200 word 'About' section with your story, skills, and what you're seeking.")
    if data.get("connections", 0) < 100:
        tips.append("Connect with at least 100+ people — classmates, professors, colleagues, and industry professionals.")
    if data.get("connections", 0) < 500:
        tips.append("Reach 500+ connections to get the '500+' badge which boosts profile visibility significantly.")
    if data.get("recommendations", 0) < 2:
        tips.append("Request 2–3 recommendations from professors, managers or teammates — they add strong credibility.")
    if not data.get("certifications"):
        tips.append("Add certifications (AWS, Google, Meta, etc.) — many are free and boost your profile score.")
    tips.append("Post or share content 2–3 times a week to increase profile views and network engagement.")
    tips.append("Turn on 'Open to Work' with specific roles to get matched with recruiters automatically.")
    tips.append("Add a professional headshot — profiles with photos get 21x more views.")
    tips.append("Use the Featured section to showcase your best projects, GitHub repos, or articles.")
    return tips[:7]


def analyze_linkedin_profile(
    name: str = "",
    headline: str = "",
    location: str = "",
    connections: int = 0,
    about: str = "",
    skills: str = "",
    recommendations: int = 0,
    experience: str = "",
    education: str = "",
    certifications: str = "",
    career_goal: str = "",
) -> dict:
    """
    Full LinkedIn profile analysis.
    Returns scores, suggestions, skill gaps, headline ideas.
    """
    # ── Individual scores ──
    headline_score     = score_headline(headline)
    about_score        = score_about(about)
    experience_score   = score_experience(experience)
    skills_score       = score_skills(skills)
    education_score    = score_education(education)
    recommendations_sc = score_recommendations(recommendations)
    connections_score  = min(round((connections / 500) * 100), 100)
    cert_score         = 80 if certifications else 0
    photo_score        = 70  # assumed since we can't verify

    # ── Overall weighted score ──
    overall = round(
        headline_score     * (WEIGHTS["headline"]        / 100) +
        about_score        * (WEIGHTS["about"]           / 100) +
        experience_score   * (WEIGHTS["experience"]      / 100) +
        education_score    * (WEIGHTS["education"]       / 100) +
        skills_score       * (WEIGHTS["skills"]          / 100) +
        recommendations_sc * (WEIGHTS["recommendations"] / 100) +
        connections_score  * (WEIGHTS["connections"]     / 100) +
        cert_score         * (WEIGHTS["certifications"]  / 100)
    )

    # ── Skill detection ──
    combined_text  = f"{about} {experience} {skills} {certifications}"
    skills_detected = extract_skills(combined_text) if combined_text.strip() else []
    if skills:
        manual_skills = [s.strip().title() for s in re.split(r'[,\n]', skills) if s.strip()]
        skills_detected = list(dict.fromkeys(manual_skills + skills_detected))[:20]

    missing_skills = detect_missing_skills(skills_detected, career_goal)

    # ── Experience entries ──
    experience_entries = extract_experience_entries(experience)

    # ── Headline suggestions ──
    headline_suggestions = generate_headline_suggestions(
        name, headline, skills, experience, career_goal
    )

    # ── Strong / weak points ──
    strong_points = []
    weak_points   = []

    if headline_score >= 60:  strong_points.append("Your headline is descriptive and keyword-rich.")
    else:                      weak_points.append("Headline is too short or missing keywords — recruiters read it first.")
    if about_score >= 60:     strong_points.append("Your About section clearly communicates your value.")
    else:                      weak_points.append("About section is missing or too brief — add your story and goals.")
    if experience_score >= 60:strong_points.append("Experience section shows solid work history.")
    else:                      weak_points.append("Experience section lacks details — add metrics and action verbs.")
    if skills_score >= 60:    strong_points.append(f"Good skills section with {len(skills_detected)} skills listed.")
    else:                      weak_points.append("Add more skills — aim for 15+ relevant skills.")
    if connections >= 500:    strong_points.append("500+ connections — excellent network reach.")
    elif connections >= 100:  strong_points.append("Growing network — keep connecting with professionals.")
    else:                      weak_points.append("Network is small (<100) — start connecting with classmates and peers.")
    if recommendations >= 2:  strong_points.append(f"{recommendations} recommendations add strong social proof.")
    else:                      weak_points.append("No recommendations — request them from professors or colleagues.")
    if education:             strong_points.append("Education section is complete.")
    if certifications:        strong_points.append("Certifications boost your profile credibility significantly.")
    else:                      weak_points.append("Add certifications to stand out — many are free (Google, Meta, AWS).")

    # ── Action tips ──
    action_tips = generate_action_tips({
        "headline": headline, "about": about, "connections": connections,
        "recommendations": recommendations, "certifications": certifications,
    })

    return {
        "name":                 name or "LinkedIn User",
        "headline":             headline,
        "location":             location,
        "connections":          connections,
        "overall_score":        overall,
        "headline_score":       headline_score,
        "about_score":          about_score,
        "experience_score":     experience_score,
        "skills_score":         skills_score,
        "education_score":      education_score,
        "recommendations_score":recommendations_sc,
        "photo_score":          photo_score,
        "skills_detected":      skills_detected,
        "missing_skills":       missing_skills,
        "experience":           experience_entries,
        "headline_suggestions": headline_suggestions,
        "strong_points":        strong_points,
        "weak_points":          weak_points,
        "action_tips":          action_tips,
    }
