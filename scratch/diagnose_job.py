"""Diagnose what text is in the job PDF and what gets extracted."""
import sys
sys.path.insert(0, r'D:\sap\nexability\backend')
sys.path.insert(0, r'D:\sap\nexability\ml')

# Download the job doc
import urllib.request
req = urllib.request.Request(
    'http://localhost:8000/api/v1/internal/ml/job-documents/5a4f7a71-40a6-41e3-b0f7-8455218e16de/content',
    headers={'X-Internal-Service-Key': 'ml-internal-secret-token'}
)
doc_bytes = urllib.request.urlopen(req).read()
print(f'Job doc bytes: {len(doc_bytes)}')

# Parse the job doc text
from nexability_ml.parser import parse_document_bytes
result = parse_document_bytes(doc_bytes, 'sample-job-description.pdf', 'application/pdf')
print(f'\n--- JOB DOC TEXT (first 3000 chars) ---')
print(result.text[:3000])
print(f'\n--- JOB DOC TEXT LENGTH: {len(result.text)} ---')

# Now normalize it
from nexability_ml.normalizer import normalize_job_description, _parse_job_requirements
reqs = _parse_job_requirements(result.text)
print(f'\n--- JOB REQUIREMENTS (raw): {len(reqs)} found ---')
for r in reqs[:20]:
    print(f'  [{r["category"]}] {r["requirement"][:80]}')

profile = normalize_job_description(result.text, employer_id='85b60b37-9333-475c-a90a-7ffea2265562')
import json
print(f'\n--- NORMALIZED JOB PROFILE ---')
print(json.dumps(profile, indent=2, default=str)[:3000])
