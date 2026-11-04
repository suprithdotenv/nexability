"""Patch matcher.py to add more resume heading variants."""
import re

filepath = r'D:\sap\nexability\ml\nexability_ml\matcher.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace _RESUME_HEADINGS dict
old_headings = '''_RESUME_HEADINGS = {
    "skills": "skills",
    "technical skills": "skills",
    "core concepts": "skills",
    "projects": "projects",
    "academic projects": "projects",
    "personal projects": "projects",
    "experience": "experience",
    "work experience": "experience",
    "professional experience": "experience",
    "experience activities": "experience",
    "education": "education",
    "academic background": "education",
    "certifications additional": "certifications",
    "certifications": "certifications",
    "professional summary": "summary",
    "summary": "summary",
}'''

new_headings = '''_RESUME_HEADINGS = {
    "skills": "skills",
    "technical skills": "skills",
    "core concepts": "skills",
    "core skills": "skills",
    "key skills": "skills",
    "competencies": "skills",
    "areas of expertise": "skills",
    "skill set": "skills",
    "projects": "projects",
    "academic projects": "projects",
    "personal projects": "projects",
    "experience": "experience",
    "work experience": "experience",
    "professional experience": "experience",
    "experience activities": "experience",
    "internship": "experience",
    "internships": "experience",
    "work history": "experience",
    "employment history": "experience",
    "education": "education",
    "academic background": "education",
    "academic qualification": "education",
    "academic qualifications": "education",
    "qualifications": "education",
    "certifications additional": "certifications",
    "certifications": "certifications",
    "certificates": "certifications",
    "professional summary": "summary",
    "summary": "summary",
    "career objective": "summary",
    "objective": "summary",
    "profile": "summary",
}'''

if old_headings in content:
    content = content.replace(old_headings, new_headings)
    print("SUCCESS: Replaced _RESUME_HEADINGS")
else:
    # Try normalizing line endings
    content_normalized = content.replace('\r\n', '\n')
    old_normalized = old_headings.replace('\r\n', '\n')
    if old_normalized in content_normalized:
        content = content_normalized.replace(old_normalized, new_headings)
        print("SUCCESS: Replaced _RESUME_HEADINGS (after normalizing line endings)")
    else:
        print("FAILED: Could not find _RESUME_HEADINGS to replace")
        # Print what we found
        idx = content.find('_RESUME_HEADINGS')
        print(f"Found at index {idx}")
        print(repr(content[idx:idx+500]))
        exit(1)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("File written successfully")
