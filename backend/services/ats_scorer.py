"""
ats_scorer.py
Calculates an ATS (Applicant Tracking System) compatibility score
and generates improvement suggestions — no external API needed.
"""
import re

# Scoring weights (must sum to 100)
WEIGHTS = {
    "skills_count":       25,   # how many skills found
    "keywords":           20,   # ATS keywords present
    "contact_info":       10,   # email/phone/linkedin present
    "sections":           15,   # resume has standard sections
    "length":             10,   # appropriate word count
    "action_verbs":       10,   # starts bullet points with action verbs
    "quantification":     10,   # numbers/metrics present
}

# Standard resume sections
SECTION_KEYWORDS = [
    "education", "experience", "skills", "projects",
    "summary", "objective", "certifications", "achievements",
    "internship", "work experience", "technical skills",
]

# Strong ATS keywords by domain
ATS_KEYWORDS = [
    "developed", "implemented", "designed", "built", "led", "managed",
    "optimized", "deployed", "integrated", "collaborated", "architected",
    "automated", "reduced", "improved", "delivered", "created",
    "python", "javascript", "react", "sql", "machine learning",
    "rest api", "microservices", "agile", "scrum", "ci/cd",
    "cloud", "docker", "git", "data analysis",
]

ACTION_VERBS = [
    "developed", "designed", "built", "created", "implemented",
    "optimized", "led", "managed", "delivered", "automated",
    "improved", "deployed", "integrated", "architected", "reduced",
    "increased", "collaborated", "analyzed", "maintained", "launched",
]


def calculate_ats_score(resume_text: str, skills_found: list[str]) -> dict:
    """
    Returns a dict with:
      - total_score (0-100)
      - breakdown: dict of individual scores
      - suggestions: list of improvement tips
      - ats_keywords: keywords to add
    """
    text_lower = resume_text.lower()
    breakdown  = {}
    suggestions= []

    # 1. Skills count (0-25)
    skill_score = min(len(skills_found) / 15 * WEIGHTS["skills_count"], WEIGHTS["skills_count"])
    breakdown["skills_count"] = round(skill_score)
    if len(skills_found) < 8:
        suggestions.append("Add more technical skills — aim for at least 10-15 relevant skills.")
    elif len(skills_found) < 5:
        suggestions.append("Your skills section is very thin. List all technologies you know.")

    # 2. ATS Keywords (0-20)
    kw_found = [kw for kw in ATS_KEYWORDS if kw in text_lower]
    kw_score = min(len(kw_found) / 10 * WEIGHTS["keywords"], WEIGHTS["keywords"])
    breakdown["keywords"] = round(kw_score)
    missing_kw = [kw for kw in ATS_KEYWORDS[:12] if kw not in text_lower]
    if len(missing_kw) > 5:
        suggestions.append("Include more industry-standard keywords like: " + ", ".join(missing_kw[:5]) + ".")

    # 3. Contact info (0-10)
    has_email   = bool(re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', resume_text))
    has_phone   = bool(re.search(r'(\+?\d[\d\s\-()]{7,})', resume_text))
    has_linkedin= "linkedin" in text_lower
    contact_score = (has_email * 4) + (has_phone * 3) + (has_linkedin * 3)
    breakdown["contact_info"] = contact_score
    if not has_email:
        suggestions.append("Add your email address — it's essential for ATS parsing.")
    if not has_phone:
        suggestions.append("Include your phone number in the contact section.")
    if not has_linkedin:
        suggestions.append("Add your LinkedIn profile URL to boost credibility.")

    # 4. Sections (0-15)
    sections_found = [s for s in SECTION_KEYWORDS if s in text_lower]
    section_score  = min(len(sections_found) / 5 * WEIGHTS["sections"], WEIGHTS["sections"])
    breakdown["sections"] = round(section_score)
    if len(sections_found) < 4:
        suggestions.append("Ensure your resume has clear sections: Summary, Skills, Experience, Education, Projects.")

    # 5. Length (0-10)
    word_count = len(resume_text.split())
    if 300 <= word_count <= 800:
        length_score = WEIGHTS["length"]
    elif word_count < 300:
        length_score = 4
        suggestions.append(f"Your resume is too short ({word_count} words). Aim for 400-600 words.")
    else:
        length_score = 7
        suggestions.append(f"Resume is quite long ({word_count} words). Consider trimming to 1-2 pages.")
    breakdown["length"] = length_score

    # 6. Action verbs (0-10)
    verbs_found = [v for v in ACTION_VERBS if v in text_lower]
    verb_score  = min(len(verbs_found) / 6 * WEIGHTS["action_verbs"], WEIGHTS["action_verbs"])
    breakdown["action_verbs"] = round(verb_score)
    if len(verbs_found) < 4:
        suggestions.append("Start bullet points with action verbs: 'Developed', 'Implemented', 'Optimized', etc.")

    # 7. Quantification (0-10)
    has_numbers = bool(re.search(r'\d+[%+x]|\d+ (users|clients|projects|teams|hours|days|months)', text_lower))
    quant_score = WEIGHTS["quantification"] if has_numbers else 2
    breakdown["quantification"] = quant_score
    if not has_numbers:
        suggestions.append("Quantify your achievements with numbers: '40% faster', '10K+ users', '3 projects'.")

    total_score = sum(breakdown.values())

    # ATS keywords to add
    ats_keywords_to_add = [kw.title() for kw in ATS_KEYWORDS if kw not in text_lower][:12]

    return {
        "total_score":       min(total_score, 100),
        "breakdown":         breakdown,
        "suggestions":       suggestions,
        "ats_keywords":      ats_keywords_to_add,
    }