"""Patch extract_job_profile_json in backend/app/automated_pipeline/extractor.py for clean job title."""
filepath = r'D:\sap\nexability\backend\app\automated_pipeline\extractor.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_code = '''    lines = [l.strip() for l in text.splitlines() if l.strip()]
    title = ""
    for line in lines[:5]:
        if any(role_term in line.lower() for role_term in [
            "developer", "engineer", "analyst", "intern", "internship",
            "architect", "consultant", "scientist", "manager",
        ]):
            title = line[:80]
            break'''

new_code = '''    lines = [l.strip() for l in text.splitlines() if l.strip()]
    title = ""
    for line in lines[:10]:
        m = re.search(r"(?i)^\s*(?:Job\s+Title|Title|Role)\s*[:\-]?\s*(.+)$", line)
        if m:
            title = m.group(1).strip()
            break
    if not title:
        for line in lines[:5]:
            if any(role_term in line.lower() for role_term in [
                "developer", "engineer", "analyst", "intern", "internship",
                "architect", "consultant", "scientist", "manager", "assistant",
            ]):
                title = line[:80]
                break'''

if old_code in content:
    content = content.replace(old_code, new_code)
    print("Replaced title extraction logic in extractor.py")
else:
    print("WARNING: Could not find target in extractor.py")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated extractor.py successfully")
