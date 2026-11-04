from nexability_ml import matcher, normalizer
from nexability_ml.parser import parse_document_bytes
import urllib.request, json

req = urllib.request.Request(
    'http://localhost:8000/api/v1/internal/ml/resumes/dc5e4e08-e3cb-49c6-928c-11da67030e66/content',
    headers={'X-Internal-Service-Key': 'ml-internal-secret-token'}
)
res_bytes = urllib.request.urlopen(req).read()
res_parsed = parse_document_bytes(res_bytes, 'Priya_Sharma_Resume.pdf', 'application/pdf')

req = urllib.request.Request(
    'http://localhost:8000/api/v1/internal/ml/job-documents/5a4f7a71-40a6-41e3-b0f7-8455218e16de/content',
    headers={'X-Internal-Service-Key': 'ml-internal-secret-token'}
)
job_bytes = urllib.request.urlopen(req).read()
job_parsed = parse_document_bytes(job_bytes, 'sample-job-description.pdf', 'application/pdf')

cand = normalizer.normalize_resume_profile(res_parsed.text)
cand['source_text'] = res_parsed.text
job = normalizer.normalize_job_description(job_parsed.text)

res = matcher._professional_match(cand, job)
print('Score:', json.dumps(res['professional_evidence_score'], indent=2))
for r in res['requirements']:
    if r['priority'] == 'required':
        print(f"  [REQUIRED] {r['requirement']} -> {r['evidence_status']} | quote: {r.get('quote')}")
