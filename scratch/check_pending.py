import urllib.request, json

req = urllib.request.Request(
    'http://localhost:8000/api/v1/internal/ml/pending-documents',
    headers={'X-Internal-Service-Key': 'ml-internal-secret-token'}
)
res = urllib.request.urlopen(req)
data = json.loads(res.read())
print('=== PENDING JOB DOCUMENTS ===')
jobs = data.get('pending_job_documents', [])
print(f'Count: {len(jobs)}')
for d in jobs:
    print(f'  ID: {d["document_id"]} | path: {d["storage_path"]}')

print('\n=== ACTIVE RESUMES ===')
resumes = data.get('active_resumes', [])
print(f'Count: {len(resumes)}')
for r in resumes:
    print(f'  ID: {r["document_id"]} | owner: {r["owner_id"]} | path: {r["storage_path"]}')
