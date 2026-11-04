"""Diagnose what text is in the PDF and what gets extracted from it."""
import sys
sys.path.insert(0, r'D:\sap\nexability\backend')
sys.path.insert(0, r'D:\sap\nexability\ml')

# Download the resume PDF
import urllib.request
req = urllib.request.Request(
    'http://localhost:8000/api/v1/internal/ml/resumes/dc5e4e08-e3cb-49c6-928c-11da67030e66/content',
    headers={'X-Internal-Service-Key': 'ml-internal-secret-token'}
)
doc_bytes = urllib.request.urlopen(req).read()
print(f'Resume bytes: {len(doc_bytes)}')
print(f'First 50 bytes: {doc_bytes[:50]}')

# Parse the resume text
from nexability_ml.parser import parse_document_bytes
result = parse_document_bytes(doc_bytes, 'Priya_Sharma_Resume.pdf', 'application/pdf')
print(f'\n--- RESUME TEXT (first 2000 chars) ---')
print(result.text[:2000])
print(f'\n--- RESUME TEXT LENGTH: {len(result.text)} ---')

# Now normalize it
from nexability_ml.normalizer import normalize_resume_profile
profile = normalize_resume_profile(result.text, candidate_id='b210a354-e127-4c99-953d-edc07c7081f1')
print(f'\n--- NORMALIZED RESUME PROFILE ---')
import json
print(json.dumps(profile, indent=2, default=str))
