"""Patch ml/nexability_ml/matcher.py with action words, stop words, and substitutions."""
filepath = r'D:\sap\nexability\ml\nexability_ml\matcher.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update _MATCH_STOP_WORDS
old_stop = '''    "code", "junior", "developer", "developers", "performance",
}'''
new_stop = '''    "code", "junior", "developer", "developers", "performance",
    "able", "ability", "general", "high", "level", "effective", "strong", "good",
    "gain", "provide", "direct", "how", "other", "management",
}'''

if old_stop in content:
    content = content.replace(old_stop, new_stop)
    print("Replaced _MATCH_STOP_WORDS")
else:
    print("WARNING: Could not find target in _MATCH_STOP_WORDS")

# 2. Update _ACTION_WORDS
old_action = '''_ACTION_WORDS = {
    "added", "built", "created", "developed", "designed", "implemented",
    "integrated", "maintained", "organized", "tested", "used", "worked",
    "wrote", "debugged", "collaborated", "contributed", "participated",
    "managed", "led", "conducted", "handled", "recruited", "executed",
    "administered", "engineered", "optimized", "delivered", "directed",
}'''

new_action = '''_ACTION_WORDS = {
    "added", "built", "created", "developed", "designed", "implemented",
    "integrated", "maintained", "organized", "organised", "tested", "used", "worked",
    "wrote", "debugged", "collaborated", "contributed", "participated",
    "managed", "led", "conducted", "handled", "recruited", "executed",
    "administered", "engineered", "optimized", "delivered", "directed",
    "coordinated", "assisted", "prepared", "supported", "studied",
    "responded", "monitored", "collected", "tracked",
}'''

if old_action in content:
    content = content.replace(old_action, new_action)
    print("Replaced _ACTION_WORDS")
else:
    print("WARNING: Could not find target in _ACTION_WORDS")

# 3. Update substitutions in _terms
old_subs = '''        (r"\\b(mentoring|mentored|mentor)\\b", "mentor"),
        (r"\\b(reviews|reviewed)\\b", "review"),
    )'''

new_subs = '''        (r"\\b(mentoring|mentored|mentor)\\b", "mentor"),
        (r"\\b(reviews|reviewed)\\b", "review"),
        (r"\\bconfidential(ity)?\\b", "confidential"),
        (r"\\bcommunicat(ion|ions|ive)?\\b", "communication"),
        (r"\\borganis(ation|ational|ed|ing|e)?\\b", "organize"),
        (r"\\borganiz(ation|ational|ed|ing|e)?\\b", "organize"),
        (r"\\b(employee|employment|employer|labour)\\b", "employ"),
        (r"\\b(policies|policy)\\b", "policy"),
        (r"\\b(practices|practice)\\b", "practice"),
        (r"\\b(regulations|regulatory|regulation|compliance)\\b", "law"),
        (r"\\b(administrat(ion|ive|or)?)\\b", "administration"),
        (r"\\b(orientat(ion)?)\\b", "orientation"),
        (r"\\b(train(ing|ings|ed)?)\\b", "train"),
        (r"\\b(verbal|oral)\\b", "verbal"),
        (r"\\b(assist(ant|ed|ing)?)\\b", "assist"),
        (r"\\b(coordinate|coordinating|coordination)\\b", "coordinate"),
    )'''

if old_subs in content:
    content = content.replace(old_subs, new_subs)
    print("Replaced substitutions in _terms")
else:
    print("WARNING: Could not find target in substitutions")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated matcher.py successfully")
