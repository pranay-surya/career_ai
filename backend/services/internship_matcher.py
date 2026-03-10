"""
internship_matcher.py
Curated internship database + AI-powered skill matching engine.
No external API required — uses local dataset + scoring algorithm.
"""
from datetime import datetime, timedelta
import random

# ── Curated Internship Database ──
# In production this would come from real job board APIs
INTERNSHIP_DB = [
    # ─── BEGINNER ───
    {
        "id": "001", "title": "Python Developer Intern", "company": "TechStart India",
        "location": "Remote", "mode": "remote", "duration": "2 Months", "duration_months": 2,
        "stipend": "₹5,000/month", "stipend_value": 5000,
        "skills": ["Python", "Git", "Basic SQL"],
        "level": "beginner", "domain": "backend",
        "source": "Internshala", "apply_url": "https://internshala.com",
        "description": "Work on Python scripts and automation tasks for a growing startup.",
        "posted_days_ago": 2,
    },
    {
        "id": "002", "title": "Frontend Web Developer Intern", "company": "PixelCraft Studios",
        "location": "Remote", "mode": "remote", "duration": "3 Months", "duration_months": 3,
        "stipend": "₹8,000/month", "stipend_value": 8000,
        "skills": ["HTML", "CSS", "JavaScript"],
        "level": "beginner", "domain": "frontend",
        "source": "LinkedIn", "apply_url": "https://linkedin.com/jobs",
        "description": "Build responsive web pages and UI components for client projects.",
        "posted_days_ago": 1,
    },
    {
        "id": "003", "title": "Data Entry & Analysis Intern", "company": "DataFlow Analytics",
        "location": "Remote", "mode": "remote", "duration": "2 Months", "duration_months": 2,
        "stipend": "₹4,000/month", "stipend_value": 4000,
        "skills": ["Excel", "Python", "Data Analysis"],
        "level": "beginner", "domain": "data",
        "source": "Internshala", "apply_url": "https://internshala.com",
        "description": "Analyze datasets and prepare reports using Python and Excel.",
        "posted_days_ago": 3,
    },
    {
        "id": "004", "title": "Android App Developer Intern", "company": "AppVenture Labs",
        "location": "Bangalore", "mode": "onsite", "duration": "3 Months", "duration_months": 3,
        "stipend": "₹10,000/month", "stipend_value": 10000,
        "skills": ["Java", "Android", "Git"],
        "level": "beginner", "domain": "mobile",
        "source": "Indeed", "apply_url": "https://indeed.com",
        "description": "Develop features for Android apps under senior developer guidance.",
        "posted_days_ago": 5,
    },
    {
        "id": "005", "title": "UI/UX Design Intern", "company": "DesignHub",
        "location": "Remote", "mode": "remote", "duration": "2 Months", "duration_months": 2,
        "stipend": "₹6,000/month", "stipend_value": 6000,
        "skills": ["Figma", "CSS", "HTML"],
        "level": "beginner", "domain": "design",
        "source": "Internshala", "apply_url": "https://internshala.com",
        "description": "Create wireframes and UI designs for web and mobile applications.",
        "posted_days_ago": 4,
    },
    {
        "id": "006", "title": "Machine Learning Intern (Fresher)", "company": "AI Foundry",
        "location": "Remote", "mode": "remote", "duration": "3 Months", "duration_months": 3,
        "stipend": "₹8,000/month", "stipend_value": 8000,
        "skills": ["Python", "NumPy", "Pandas"],
        "level": "beginner", "domain": "ai",
        "source": "Wellfound", "apply_url": "https://wellfound.com",
        "description": "Assist with data preprocessing and model training tasks.",
        "posted_days_ago": 2,
    },

    # ─── INTERMEDIATE ───
    {
        "id": "007", "title": "Full Stack Developer Intern", "company": "BuildSpace Tech",
        "location": "Remote", "mode": "remote", "duration": "6 Months", "duration_months": 6,
        "stipend": "₹20,000/month", "stipend_value": 20000,
        "skills": ["React", "Node.js", "MongoDB", "REST API"],
        "level": "intermediate", "domain": "fullstack",
        "source": "LinkedIn", "apply_url": "https://linkedin.com/jobs",
        "description": "Build and maintain full stack features for our SaaS product.",
        "posted_days_ago": 1,
    },
    {
        "id": "008", "title": "Backend Engineer Intern", "company": "CloudNest Systems",
        "location": "Hyderabad", "mode": "hybrid", "duration": "6 Months", "duration_months": 6,
        "stipend": "₹25,000/month", "stipend_value": 25000,
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
        "level": "intermediate", "domain": "backend",
        "source": "LinkedIn", "apply_url": "https://linkedin.com/jobs",
        "description": "Develop REST APIs and microservices for our cloud platform.",
        "posted_days_ago": 3,
    },
    {
        "id": "009", "title": "Data Science Intern", "company": "Insightful Analytics",
        "location": "Remote", "mode": "remote", "duration": "4 Months", "duration_months": 4,
        "stipend": "₹18,000/month", "stipend_value": 18000,
        "skills": ["Python", "Pandas", "Scikit-learn", "SQL", "Tableau"],
        "level": "intermediate", "domain": "data",
        "source": "Wellfound", "apply_url": "https://wellfound.com",
        "description": "Build predictive models and create dashboards for business insights.",
        "posted_days_ago": 2,
    },
    {
        "id": "010", "title": "React Frontend Intern", "company": "ProductLab",
        "location": "Pune", "mode": "hybrid", "duration": "3 Months", "duration_months": 3,
        "stipend": "₹15,000/month", "stipend_value": 15000,
        "skills": ["React", "JavaScript", "TypeScript", "CSS"],
        "level": "intermediate", "domain": "frontend",
        "source": "Indeed", "apply_url": "https://indeed.com",
        "description": "Build interactive dashboards and components using React.",
        "posted_days_ago": 6,
    },
    {
        "id": "011", "title": "DevOps Intern", "company": "InfraStack",
        "location": "Remote", "mode": "remote", "duration": "6 Months", "duration_months": 6,
        "stipend": "₹22,000/month", "stipend_value": 22000,
        "skills": ["Docker", "Linux", "CI/CD", "AWS", "Bash"],
        "level": "intermediate", "domain": "devops",
        "source": "LinkedIn", "apply_url": "https://linkedin.com/jobs",
        "description": "Manage CI/CD pipelines and containerized deployments.",
        "posted_days_ago": 4,
    },
    {
        "id": "012", "title": "ML Engineer Intern", "company": "NeuralWave AI",
        "location": "Bangalore", "mode": "onsite", "duration": "6 Months", "duration_months": 6,
        "stipend": "₹30,000/month", "stipend_value": 30000,
        "skills": ["Python", "TensorFlow", "PyTorch", "Scikit-learn", "NLP"],
        "level": "intermediate", "domain": "ai",
        "source": "Wellfound", "apply_url": "https://wellfound.com",
        "description": "Train and deploy machine learning models for NLP applications.",
        "posted_days_ago": 1,
    },
    {
        "id": "013", "title": "Cloud Engineer Intern", "company": "SkyOps Technologies",
        "location": "Remote", "mode": "remote", "duration": "6 Months", "duration_months": 6,
        "stipend": "₹20,000/month", "stipend_value": 20000,
        "skills": ["AWS", "Terraform", "Docker", "Linux"],
        "level": "intermediate", "domain": "cloud",
        "source": "Indeed", "apply_url": "https://indeed.com",
        "description": "Provision cloud infrastructure and automate deployments on AWS.",
        "posted_days_ago": 7,
    },

    # ─── ADVANCED ───
    {
        "id": "014", "title": "Software Engineering Intern", "company": "Google India",
        "location": "Hyderabad", "mode": "onsite", "duration": "3 Months", "duration_months": 3,
        "stipend": "₹1,50,000/month", "stipend_value": 150000,
        "skills": ["Python", "C++", "System Design", "Data Structures", "Algorithms"],
        "level": "advanced", "domain": "backend",
        "source": "Company Portal", "apply_url": "https://careers.google.com",
        "description": "Work on large-scale distributed systems with Google's engineering team.",
        "posted_days_ago": 10,
    },
    {
        "id": "015", "title": "AI Research Intern", "company": "Microsoft Research India",
        "location": "Bangalore", "mode": "onsite", "duration": "6 Months", "duration_months": 6,
        "stipend": "₹1,20,000/month", "stipend_value": 120000,
        "skills": ["Python", "PyTorch", "Deep Learning", "Research", "NLP"],
        "level": "advanced", "domain": "ai",
        "source": "Company Portal", "apply_url": "https://careers.microsoft.com",
        "description": "Contribute to cutting-edge AI research projects at Microsoft Research.",
        "posted_days_ago": 15,
    },
    {
        "id": "016", "title": "Senior Frontend Intern", "company": "Razorpay",
        "location": "Bangalore", "mode": "hybrid", "duration": "6 Months", "duration_months": 6,
        "stipend": "₹80,000/month", "stipend_value": 80000,
        "skills": ["React", "TypeScript", "GraphQL", "System Design", "Performance"],
        "level": "advanced", "domain": "frontend",
        "source": "LinkedIn", "apply_url": "https://linkedin.com/jobs",
        "description": "Build high-performance payment UI for millions of Razorpay users.",
        "posted_days_ago": 8,
    },
    {
        "id": "017", "title": "Backend Platform Intern", "company": "Zepto",
        "location": "Mumbai", "mode": "onsite", "duration": "6 Months", "duration_months": 6,
        "stipend": "₹90,000/month", "stipend_value": 90000,
        "skills": ["Go", "Microservices", "Kafka", "PostgreSQL", "Docker", "Kubernetes"],
        "level": "advanced", "domain": "backend",
        "source": "Wellfound", "apply_url": "https://wellfound.com",
        "description": "Build and scale backend microservices powering Zepto's delivery platform.",
        "posted_days_ago": 5,
    },
    {
        "id": "018", "title": "Data Engineer Intern", "company": "Swiggy",
        "location": "Bangalore", "mode": "hybrid", "duration": "6 Months", "duration_months": 6,
        "stipend": "₹70,000/month", "stipend_value": 70000,
        "skills": ["Python", "Spark", "Airflow", "SQL", "AWS", "Data Pipelines"],
        "level": "advanced", "domain": "data",
        "source": "LinkedIn", "apply_url": "https://linkedin.com/jobs",
        "description": "Design data pipelines and ETL workflows for Swiggy's data platform.",
        "posted_days_ago": 3,
    },
    {
        "id": "019", "title": "Security Engineer Intern", "company": "HackerOne India",
        "location": "Remote", "mode": "remote", "duration": "6 Months", "duration_months": 6,
        "stipend": "₹60,000/month", "stipend_value": 60000,
        "skills": ["Python", "Linux", "Networking", "Security", "Penetration Testing"],
        "level": "advanced", "domain": "security",
        "source": "Company Portal", "apply_url": "https://hackerone.com/careers",
        "description": "Perform security assessments and build security tooling.",
        "posted_days_ago": 12,
    },
    {
        "id": "020", "title": "iOS Developer Intern", "company": "CRED",
        "location": "Bangalore", "mode": "onsite", "duration": "6 Months", "duration_months": 6,
        "stipend": "₹75,000/month", "stipend_value": 75000,
        "skills": ["Swift", "iOS", "Xcode", "REST API", "Git"],
        "level": "advanced", "domain": "mobile",
        "source": "LinkedIn", "apply_url": "https://linkedin.com/jobs",
        "description": "Build iOS features for CRED's award-winning mobile application.",
        "posted_days_ago": 6,
    },
]


def calculate_match_score(job: dict, user_skills: list[str], role: str, level: str, mode: str, duration: str) -> int:
    """Calculate a 0-100 match score for a job based on user's profile."""
    score = 0
    user_skills_lower = [s.lower() for s in user_skills]
    job_skills_lower  = [s.lower() for s in job["skills"]]

    # Skill match (up to 50 points)
    if user_skills_lower and job_skills_lower:
        matched = sum(1 for s in job_skills_lower if s in user_skills_lower)
        skill_score = (matched / len(job_skills_lower)) * 50
        score += round(skill_score)
    else:
        score += 25  # neutral if no skills provided

    # Role / domain match (up to 30 points)
    if role:
        role_lower = role.lower()
        if role_lower in job["title"].lower():            score += 30
        elif role_lower in job["domain"].lower():         score += 20
        elif any(word in job["title"].lower() for word in role_lower.split()): score += 15

    # Level match (up to 15 points)
    if level == "all" or level == job["level"]:           score += 15

    # Mode match (up to 5 points)
    if mode == "all" or mode == job["mode"]:              score += 5

    return min(score, 100)


def search_internships(
    role: str = "",
    level: str = "all",
    mode: str = "all",
    duration: str = "all",
    skills: list[str] = [],
) -> list[dict]:
    """
    Search and rank internships based on filters and skill matching.
    Returns sorted list of internships with match scores.
    """
    results = []

    for job in INTERNSHIP_DB:
        # ── Hard filters ──
        if level != "all" and job["level"] != level:
            continue
        if mode != "all" and job["mode"] != mode:
            continue
        if duration != "all":
            if duration == "1-2" and job["duration_months"] > 2:    continue
            if duration == "3-6" and not (3 <= job["duration_months"] <= 6): continue
            if duration == "6+"  and job["duration_months"] < 6:    continue

        # Role keyword filter (broad match)
        if role:
            role_lower = role.lower()
            title_match   = role_lower in job["title"].lower()
            domain_match  = role_lower in job["domain"]
            any_word      = any(w in job["title"].lower() or w in job["domain"]
                               for w in role_lower.split() if len(w) > 2)
            if not (title_match or domain_match or any_word):
                continue

        # ── Calculate match score ──
        match_score = calculate_match_score(job, skills, role, level, mode, duration)

        # Compute posted date
        posted_date = (datetime.now() - timedelta(days=job["posted_days_ago"])).isoformat()

        results.append({
            **job,
            "match_score":  match_score,
            "posted_date":  posted_date,
            "posted_label": f"{job['posted_days_ago']}d ago" if job["posted_days_ago"] > 0 else "Today",
        })

    # Sort by match score descending
    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results
