"""Update matcher.py with proficient in stop words and confidentially regex."""
filepath = r'D:\sap\nexability\ml\nexability_ml\matcher.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add proficient to _MATCH_STOP_WORDS
old_stop = '"gain", "provide", "direct", "how", "other", "management",'
new_stop = '"gain", "provide", "direct", "how", "other", "management", "proficient",'

if old_stop in content:
    content = content.replace(old_stop, new_stop)
    print("Added proficient to _MATCH_STOP_WORDS")
else:
    print("WARNING: Could not find old_stop")

# 2. Update confidential regex in _terms
old_conf = '(r"\\bconfidential(ity)?\\b", "confidential")'
new_conf = '(r"\\bconfidential(ity|ly)?\\b", "confidential")'

if old_conf in content:
    content = content.replace(old_conf, new_conf)
    print("Updated confidential regex")
else:
    print("WARNING: Could not find old_conf")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated matcher.py successfully")
