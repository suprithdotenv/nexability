import urllib.request, json

# Test the ML matching service directly
req = urllib.request.Request(
    'http://localhost:8001/api/v1/ml/matches?min_threshold=0.0',
    headers={
        'X-Internal-Service-Key': 'ml-internal-secret-token',
        'X-Candidate-Id': 'b210a354-e127-4c99-953d-edc07c7081f1'
    }
)
try:
    res = urllib.request.urlopen(req)
    data = json.loads(res.read())
    print('=== ML MATCHES RESULT ===')
    print(f'Status: {data.get("status")}')
    print(f'Candidate ID: {data.get("candidate_id")}')
    matches = data.get('matches', [])
    print(f'Match count: {len(matches)}')
    for m in matches:
        print(f'  Score: {m.get("professional_compatibility_score")} | Job: {m.get("job_document_id")} | Employer: {m.get("employer_name")}')
    print('\nFull response:')
    print(json.dumps(data, indent=2))
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
