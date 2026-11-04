import sys
sys.path.insert(0, r'D:\sap\nexability\ml')

from nexability_ml.matcher import _resume_lines, _match_requirement, _job_requirements, _professional_match
from nexability_ml.normalizer import normalize_job_description, normalize_resume_profile
from nexability_ml.parser import parse_document_bytes
import urllib.request
import re

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

cand_profile = normalize_resume_profile(res_parsed.text)
cand_profile['source_text'] = res_parsed.text

job_profile = normalize_job_description(job_parsed.text)

# Let's inspect the requirements in job_profile
print("Job requirements before tweak:")
for r in job_profile["requirements"]:
    print(f"  [{r['category']} - {r['priority']}] {r['requirement']}")
