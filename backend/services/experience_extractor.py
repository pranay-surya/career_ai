"""
experience_extractor.py
Extracts work experience entries from resume text using regex patterns.
No external API required.
"""
import re


# Common job title keywords
JOB_TITLE_PATTERNS = [
    r"(software engineer|developer|intern|data scientist|data analyst|"
    r"machine learning engineer|devops engineer|cloud engineer|"
    r"full stack developer|frontend developer|backend developer|"
    r"product manager|project manager|ui/ux designer|"
    r"research intern|technical intern|summer intern|"
    r"junior developer|senior developer|lead engineer)",
]

# Duration patterns
DURATION_PATTERN = re.compile(
    r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|january|february|march|"
    r"april|june|july|august|september|october|november|december)"
    r"[\s,]*\d{4}\s*[-–—to]+\s*"
    r"(present|current|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|"
    r"january|february|march|april|june|july|august|september|october|november|december|\d{4})",
    re.IGNORECASE,
)


def extract_experience(text: str) -> list[dict]:
    """
    Returns a list of dicts: [{"title": ..., "company": ..., "duration": ...}]
    Best-effort extraction from plain text.
    """
    entries = []

    # Split text into lines
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    for i, line in enumerate(lines):
        line_lower = line.lower()

        # Check if this line looks like a job title
        for pattern in JOB_TITLE_PATTERNS:
            match = re.search(pattern, line_lower)
            if match:
                title = match.group(0).title()

                # Try to find company name (usually next non-empty line or same line after '|', '@', 'at')
                company = ""
                company_match = re.search(r'(?:at|@|\|)\s*([A-Z][a-zA-Z\s&.,]+)', line)
                if company_match:
                    company = company_match.group(1).strip()
                elif i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if len(next_line) < 60 and not any(
                        kw in next_line.lower() for kw in ["developed", "built", "led", "managed"]
                    ):
                        company = next_line

                # Try to find duration in nearby lines
                duration = ""
                search_range = lines[max(0, i-1):min(len(lines), i+3)]
                for nearby in search_range:
                    dur_match = DURATION_PATTERN.search(nearby)
                    if dur_match:
                        duration = dur_match.group(0).strip()
                        break

                entries.append({
                    "title": title,
                    "company": company[:60] if company else "",
                    "duration": duration,
                })
                break  # Don't double-match same line

    # Deduplicate by title
    seen = set()
    unique = []
    for e in entries:
        key = e["title"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(e)

    return unique[:6]  # Return max 6 experience entries
