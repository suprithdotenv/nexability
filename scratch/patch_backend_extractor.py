"""Patch backend/app/automated_pipeline/extractor.py with HR/office skills and headers."""
import re

filepath = r'D:\sap\nexability\backend\app\automated_pipeline\extractor.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add skills to CANONICAL_SKILL_PATTERNS
extra_skills = '''    (r"\\bsupervised\\s*learning\\b", "Supervised Learning"),
    (r"\\b(microsoft\\s*excel|ms\\s*excel|excel)\\b", "Microsoft Excel"),
    (r"\\b(microsoft\\s*word|ms\\s*word)\\b", "Microsoft Word"),
    (r"\\b(microsoft\\s*office|ms\\s*office|powerpoint)\\b", "Microsoft Office"),
    (r"\\b(human\\s*resources|hr\\s*administration|hr\\s*operations)\\b", "Human Resources"),
    (r"\\b(employee\\s*relations|employee\\s*onboarding|onboarding)\\b", "Employee Relations"),
    (r"\\b(recruitment|talent\\s*acquisition)\\b", "Recruitment"),
    (r"\\b(employment\\s*law|labor\\s*law|compliance)\\b", "Employment Law"),
    (r"\\b(communication\\s*skills|written\\s*communication|verbal\\s*communication)\\b", "Communication"),
    (r"\\b(confidentiality|confidential\\s*information)\\b", "Confidentiality"),
    (r"\\b(teamwork|collaboration)\\b", "Teamwork"),'''

if '(r"\\bsupervised\\s*learning\\b", "Supervised Learning"),' in content:
    content = content.replace(
        '(r"\\bsupervised\\s*learning\\b", "Supervised Learning"),',
        extra_skills
    )
    print("Replaced CANONICAL_SKILL_PATTERNS")
else:
    print("WARNING: Could not find target in CANONICAL_SKILL_PATTERNS")

# 2. Add action verbs
extra_verbs = '''    "handled", "processed", "executed", "visualized", "modelled", "modeled",
    "coordinated", "maintained", "assisted", "prepared", "supported", "studied",
    "organized", "organised", "responded", "monitored", "collected", "tracked",'''

if '"handled", "processed", "executed", "visualized", "modelled", "modeled",' in content:
    content = content.replace(
        '"handled", "processed", "executed", "visualized", "modelled", "modeled",',
        extra_verbs
    )
    print("Replaced ACTION_VERBS")
else:
    print("WARNING: Could not find target in ACTION_VERBS")

# 3. Add to SECTION_HEADER_MAP
old_sec = '''SECTION_HEADER_MAP = {
    "skills": ["skills", "technical skills", "core competencies", "technologies", "tech stack", "tools and technologies"],'''
new_sec = '''SECTION_HEADER_MAP = {
    "skills": ["skills", "technical skills", "core skills", "core competencies", "key skills", "technologies", "tech stack", "tools and technologies"],'''

if old_sec in content:
    content = content.replace(old_sec, new_sec)
    print("Replaced SECTION_HEADER_MAP")
else:
    print("WARNING: Could not find target in SECTION_HEADER_MAP")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated backend extractor.py successfully")
