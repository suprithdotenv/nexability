"""Patch matching_service.py line 263 to preserve full parsed text in source_text."""
filepath = r'D:\sap\nexability\ml\nexability_ml\matching_service.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_line = 'structured["source_text"] = result.get("safe_source_text") or ""'
new_line = 'structured["source_text"] = getattr(result.get("extraction"), "text", None) or result.get("safe_source_text") or ""'

if old_line in content:
    content = content.replace(old_line, new_line)
    print("Replaced source_text assignment in matching_service.py")
else:
    print("WARNING: Could not find target line")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated matching_service.py successfully")
