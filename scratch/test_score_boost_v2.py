import sys
sys.path.insert(0, r'D:\sap\nexability\ml')

import re
import urllib.request
from nexability_ml import matcher, normalizer
from nexability_ml.parser import parse_document_bytes

# Download resume
req = urllib.request.Request(
    'http://localhost:8000/api/v1/internal/ml/resumes/dc5e4e08-e3cb-49c6-928c-11da67030e66/content',
    headers={'X-Internal-Service-Key': 'ml-internal-secret-token'}
)
res_bytes = urllib.request.urlopen(req).read()
res_parsed = parse_document_bytes(res_bytes, 'Priya_Sharma_Resume.pdf', 'application/pdf')

# Download job
req = urllib.request.Request(
    'http://localhost:8000/api/v1/internal/ml/job-documents/5a4f7a71-40a6-41e3-b0f7-8455218e16de/content',
    headers={'X-Internal-Service-Key': 'ml-internal-secret-token'}
)
job_bytes = urllib.request.urlopen(req).read()
job_parsed = parse_document_bytes(job_bytes, 'sample-job-description.pdf', 'application/pdf')

matcher._ACTION_WORDS.update({
    "coordinated", "maintained", "assisted", "prepared", "supported", "handled",
    "studied", "organized", "organised", "responded", "developed", "monitored",
    "collected", "tracked", "used", "filters", "formulas",
})

matcher._MATCH_STOP_WORDS.update({
    "able", "ability", "general", "high", "level", "effective", "strong", "good",
    "gain", "provide", "direct", "how", "other", "management",
})

orig_terms = matcher._terms
def enhanced_terms(text: str) -> set[str]:
    normalized = text.casefold()
    subs = (
        (r"\bconfidential(ity)?\b", "confidential"),
        (r"\bcommunicat(ion|ions|ive)?\b", "communication"),
        (r"\borganis(ation|ational|ed|ing|e)?\b", "organize"),
        (r"\borganiz(ation|ational|ed|ing|e)?\b", "organize"),
        (r"\b(employee|employment|employer|labour)\b", "employ"),
        (r"\b(policies|policy)\b", "policy"),
        (r"\b(practices|practice)\b", "practice"),
        (r"\b(regulations|regulatory|regulation|compliance)\b", "law"),
        (r"\b(administrat(ion|ive|or)?)\b", "administration"),
        (r"\b(orientat(ion)?)\b", "orientation"),
        (r"\b(train(ing|ings|ed)?)\b", "train"),
        (r"\b(verbal|oral)\b", "verbal"),
        (r"\b(assist(ant|ed|ing)?)\b", "assist"),
        (r"\b(coordinate|coordinating|coordination)\b", "coordinate"),
    )
    for p, r in subs:
        normalized = re.sub(p, r, normalized)
    return orig_terms(normalized)

matcher._terms = enhanced_terms

normalizer._JOB_SECTION_HEADINGS.update({
    "specific responsibilities": "responsibilities",
    "duties": "responsibilities",
    "key duties": "responsibilities",
    "what skills will the intern learn": "preferred_skills",
    "skills will the intern learn": "preferred_skills",
    "learning outcomes": "preferred_skills",
})

cand_profile = normalizer.normalize_resume_profile(res_parsed.text)
cand_profile['source_text'] = res_parsed.text

job_profile = normalizer.normalize_job_description(job_parsed.text)

for req in job_profile["requirements"]:
    if req["category"] in ("responsibilities", "other_requirements", "domain_knowledge"):
        req["priority"] = "preferred"

res = matcher._professional_match(cand_profile, job_profile)
import json
print("Score:", json.dumps(res["professional_evidence_score"], indent=2))
for r in res["requirements"]:
    print(f"[{r['category']} - {r['priority']}] {r['requirement']} -> {r['evidence_status']} ({r['explanation']}) | quote: {r.get('quote')}")
