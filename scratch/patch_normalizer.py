"""Patch ml/nexability_ml/normalizer.py with headings, priority logic, and skills."""
filepath = r'D:\sap\nexability\ml\nexability_ml\normalizer.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update _JOB_SECTION_HEADINGS
old_headings = '''_JOB_SECTION_HEADINGS = {
    "required": "required_skills",
    "required skill": "required_skills",
    "required skills": "required_skills",
    "requirements": "required_skills",
    "qualifications": "required_skills",
    "preferred": "preferred_skills",
    "preferred skill": "preferred_skills",
    "preferred skills": "preferred_skills",
    "responsibilities": "responsibilities",
    "key responsibilities": "responsibilities",
    "what you will do": "responsibilities",
    "what you ll do": "responsibilities",
    "domain knowledge": "domain_knowledge",
    "education": "education",
    "education requirements": "education",
    "experience": "experience",
    "work experience": "experience",
    "experience requirements": "experience",
}'''

new_headings = '''_JOB_SECTION_HEADINGS = {
    "required": "required_skills",
    "required skill": "required_skills",
    "required skills": "required_skills",
    "requirements": "required_skills",
    "qualifications": "required_skills",
    "basic qualifications": "required_skills",
    "minimum qualifications": "required_skills",
    "preferred": "preferred_skills",
    "preferred skill": "preferred_skills",
    "preferred skills": "preferred_skills",
    "desired qualifications": "preferred_skills",
    "preferred qualifications": "preferred_skills",
    "responsibilities": "responsibilities",
    "specific responsibilities": "responsibilities",
    "key responsibilities": "responsibilities",
    "duties": "responsibilities",
    "key duties": "responsibilities",
    "what you will do": "responsibilities",
    "what you ll do": "responsibilities",
    "what skills will the intern learn": "preferred_skills",
    "skills will the intern learn": "preferred_skills",
    "learning outcomes": "preferred_skills",
    "internship exposure": "domain_knowledge",
    "functional areas": "domain_knowledge",
    "domain knowledge": "domain_knowledge",
    "education": "education",
    "education requirements": "education",
    "experience": "experience",
    "work experience": "experience",
    "experience requirements": "experience",
}'''

if old_headings in content:
    content = content.replace(old_headings, new_headings)
    print("Replaced _JOB_SECTION_HEADINGS")
else:
    print("WARNING: Could not find target in _JOB_SECTION_HEADINGS")

# 2. Update _KNOWN_SKILLS
old_known = '''    "data structures and algorithms": ("data structures and algorithms",),
}'''

new_known = '''    "data structures and algorithms": ("data structures and algorithms",),
    "microsoft excel": ("microsoft excel", "excel", "ms excel"),
    "microsoft word": ("microsoft word", "word", "ms word"),
    "microsoft office": ("microsoft office", "ms office", "powerpoint"),
    "communication": ("communication skills", "written communication", "verbal communication", "oral communication", "interpersonal communication"),
    "confidentiality": ("confidentiality", "confidential information", "confidential"),
    "human resources": ("human resources", "hr administration", "hr operations", "employee relations", "hris"),
    "employment law": ("employment law", "labor law", "employment compliance"),
}'''

if old_known in content:
    content = content.replace(old_known, new_known)
    print("Replaced _KNOWN_SKILLS")
else:
    print("WARNING: Could not find target in _KNOWN_SKILLS")

# 3. Update candidate skills in _extract_skills
old_cand_skills = '''            "spark", "pandas", "numpy", "communication", "leadership",
            "teamwork",
        )'''

new_cand_skills = '''            "spark", "pandas", "numpy", "communication", "leadership",
            "teamwork", "microsoft excel", "microsoft word", "excel", "word",
            "powerpoint", "confidentiality", "human resources", "hr administration",
            "onboarding", "recruitment", "employee relations",
        )'''

if old_cand_skills in content:
    content = content.replace(old_cand_skills, new_cand_skills)
    print("Replaced candidate skills in _extract_skills")
else:
    print("WARNING: Could not find target in _extract_skills")

# 4. Update priority logic in _parse_job_requirements
old_prio = '''preferred = current_category == "preferred_skills"
                requirements.append(
                    {
                        "requirement": original,
                        "category": current_category,
                        "priority": "preferred" if preferred else "required",'''

new_prio = '''preferred = current_category in {"preferred_skills", "responsibilities", "domain_knowledge"}
                requirements.append(
                    {
                        "requirement": original,
                        "category": current_category,
                        "priority": "preferred" if preferred else "required",'''

if old_prio in content:
    content = content.replace(old_prio, new_prio)
    print("Replaced priority logic in _parse_job_requirements")
else:
    print("WARNING: Could not find target in _parse_job_requirements")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated normalizer.py successfully")
