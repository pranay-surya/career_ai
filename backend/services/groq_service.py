"""
groq_service.py
Groq LLM integration for roadmap generation and career chatbot.
Uses free Groq API with llama-3.3-70b-versatile model.
"""
import os, json, re
from groq import Groq
from dotenv import load_dotenv
load_dotenv()

GROQ_API_KEY=os.getenv("GROQ_API_KEY")
MODEL        = "llama-3.3-70b-versatile"

def get_client() -> Groq:
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set. Please add it to your .env file.")
    return Groq(api_key=GROQ_API_KEY)


# ── Fallback static roadmaps (used when Groq is unavailable) ──
STATIC_ROADMAPS = {
    "Frontend Developer": {
        "phases": [
            {"name": "Web Fundamentals", "duration": "3 weeks", "topics": [
                {"name": "HTML5", "description": "Semantic HTML, forms, accessibility"},
                {"name": "CSS3", "description": "Flexbox, Grid, animations, responsive design"},
                {"name": "JavaScript Basics", "description": "Variables, functions, DOM manipulation"},
            ], "skills_gained": ["HTML", "CSS", "JavaScript"],
            "resources": [
                {"name": "FreeCodeCamp HTML/CSS", "type": "course", "url": "https://freecodecamp.org"},
                {"name": "The Odin Project", "type": "course", "url": "https://theodinproject.com"},
                {"name": "Traversy Media (YouTube)", "type": "youtube", "url": "https://youtube.com/@TraversyMedia"},
            ], "projects": ["Personal Portfolio", "Responsive Landing Page"]},
            {"name": "JavaScript Deep Dive", "duration": "3 weeks", "topics": [
                {"name": "ES6+ Features", "description": "Arrow functions, promises, async/await, modules"},
                {"name": "DOM & Events", "description": "Event listeners, fetch API, local storage"},
                {"name": "Git & GitHub", "description": "Version control, branches, pull requests"},
            ], "skills_gained": ["ES6", "Async JS", "Git"],
            "resources": [
                {"name": "JavaScript.info", "type": "docs", "url": "https://javascript.info"},
                {"name": "Akshay Saini JS (YouTube)", "type": "youtube", "url": "https://youtube.com/@akshaymarch7"},
            ], "projects": ["Todo App", "Weather App with API"]},
            {"name": "React Framework", "duration": "4 weeks", "topics": [
                {"name": "React Fundamentals", "description": "Components, props, state, hooks"},
                {"name": "React Router", "description": "SPA navigation and routing"},
                {"name": "State Management", "description": "Context API, Redux basics"},
            ], "skills_gained": ["React", "Hooks", "State Management"],
            "resources": [
                {"name": "React Official Docs", "type": "docs", "url": "https://react.dev"},
                {"name": "Scrimba React Course", "type": "course", "url": "https://scrimba.com"},
                {"name": "Codevolution React (YouTube)", "type": "youtube", "url": "https://youtube.com/@Codevolution"},
            ], "projects": ["E-commerce Product Page", "Blog App with React"]},
            {"name": "Job Ready Skills", "duration": "3 weeks", "topics": [
                {"name": "TypeScript", "description": "Type safety for JavaScript"},
                {"name": "Testing", "description": "Jest, React Testing Library"},
                {"name": "Performance", "description": "Lazy loading, code splitting, web vitals"},
            ], "skills_gained": ["TypeScript", "Testing", "Performance"],
            "resources": [
                {"name": "TypeScript Handbook", "type": "docs", "url": "https://typescriptlang.org/docs"},
                {"name": "LeetCode Frontend", "type": "practice", "url": "https://leetcode.com"},
            ], "projects": ["Full Portfolio Website", "Dashboard App"]},
        ]
    },
}


async def generate_roadmap(
    career_goal:   str,
    level:         str = "beginner",
    time_available:str = "2-3 hours/day",
    focus_area:    str = "job-ready",
    roadmap_type:  str = "simple",
) -> dict:
    """
    Generate a structured career roadmap using Groq LLM.
    Falls back to static data if API is unavailable.
    """
    try:
        client = get_client()
    except ValueError:
        return _build_static_roadmap(career_goal, level, roadmap_type)

    phases_count = 3 if roadmap_type == "simple" else 5
    prompt = f"""You are an expert career coach. Generate a detailed learning roadmap for:

Career Goal: {career_goal}
Current Level: {level}
Time Available: {time_available}
Focus Area: {focus_area}
Roadmap Type: {roadmap_type} ({'beginner-friendly basics' if roadmap_type == 'simple' else 'comprehensive job-ready path'})

Return ONLY valid JSON (no markdown, no explanation) in this exact structure:
{{
  "career_goal": "{career_goal}",
  "level": "{level}",
  "roadmap_type": "{roadmap_type}",
  "time_available": "{time_available}",
  "total_weeks": <number>,
  "total_topics": <number>,
  "phases": [
    {{
      "name": "Phase name",
      "duration": "X weeks",
      "topics": [
        {{"name": "Topic name", "description": "1 sentence description"}}
      ],
      "skills_gained": ["skill1", "skill2"],
      "resources": [
        {{"name": "Resource name", "type": "youtube|course|docs|github|practice", "url": "https://..."}}
      ],
      "projects": ["Project idea 1", "Project idea 2"]
    }}
  ]
}}

Rules:
- {phases_count} phases total
- 3-5 topics per phase
- 3-4 resources per phase (ONLY free resources: YouTube, freeCodeCamp, official docs, GitHub repos, LeetCode)
- 2-3 project ideas per phase that build a portfolio
- Resources must have real, working URLs
- Be specific and practical"""

    completion = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=4000,
    )

    raw = completion.choices[0].message.content.strip()

    # Strip markdown code fences if present
    raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'\s*```$', '', raw, flags=re.MULTILINE)
    raw = raw.strip()

    roadmap = json.loads(raw)

    # Ensure required fields
    roadmap.setdefault("career_goal",    career_goal)
    roadmap.setdefault("level",          level)
    roadmap.setdefault("roadmap_type",   roadmap_type)
    roadmap.setdefault("time_available", time_available)
    roadmap.setdefault("total_weeks",    sum_weeks(roadmap.get("phases", [])))
    roadmap.setdefault("total_topics",   sum_topics(roadmap.get("phases", [])))

    return roadmap


async def chat_with_groq(message: str, history: list[dict], context: str = "") -> str:
    """
    Career advice chatbot powered by Groq.
    """
    try:
        client = get_client()
    except ValueError:
        return "Groq API key is not configured. Please add GROQ_API_KEY to your .env file and restart the server."

    system_prompt = f"""You are CareerAI, an expert career coach and technical mentor for students and fresh graduates.
{context}
You help with: career roadmaps, skill guidance, interview prep, resume tips, portfolio advice, and job search strategies.
Be concise, practical, and encouraging. Use bullet points for lists. Keep responses under 200 words unless detailed explanation is needed."""

    messages = [{"role": "system", "content": system_prompt}]
    for h in history[-6:]:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})

    completion = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.6,
        max_tokens=600,
    )
    return completion.choices[0].message.content.strip()


# ── Helpers ──
def sum_weeks(phases: list) -> int:
    total = 0
    for p in phases:
        dur = p.get("duration", "")
        nums = re.findall(r'\d+', dur)
        if nums: total += int(nums[0])
    return total or len(phases) * 3


def sum_topics(phases: list) -> int:
    return sum(len(p.get("topics", [])) for p in phases)


def _build_static_roadmap(career_goal: str, level: str, roadmap_type: str) -> dict:
    """Return a static roadmap when Groq is unavailable."""
    base_key = None
    goal_lower = career_goal.lower()
    for key in STATIC_ROADMAPS:
        if key.lower() in goal_lower or goal_lower in key.lower():
            base_key = key
            break

    if not base_key:
        base_key = list(STATIC_ROADMAPS.keys())[0]

    phases = STATIC_ROADMAPS[base_key]["phases"]
    if roadmap_type == "simple":
        phases = phases[:3]

    return {
        "career_goal":    career_goal,
        "level":          level,
        "roadmap_type":   roadmap_type,
        "time_available": "2-3 hours/day",
        "total_weeks":    sum_weeks(phases),
        "total_topics":   sum_topics(phases),
        "phases":         phases,
        "_note":          "Static roadmap (Groq API not configured). Add GROQ_API_KEY for AI-powered roadmaps.",
    }