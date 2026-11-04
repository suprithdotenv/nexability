import urllib.request, json

req = urllib.request.Request(
    'http://localhost:8001/api/v1/ml/matches?min_threshold=60.0&force_reprocess=true',
    headers={
        'X-Internal-Service-Key': 'ml-internal-secret-token',
        'X-Candidate-Id': 'b210a354-e127-4c99-953d-edc07c7081f1'
    }
)
try:
    res = urllib.request.urlopen(req)
    data = json.loads(res.read())
    print('=== ML MATCHES RESULT WITH 60% THRESHOLD ===')
    print(f'Status: {data.get("status")}')
    print(f'Candidate ID: {data.get("candidate_id")}')
    matches = data.get('top_matches', [])
    print(f'Match count: {len(matches)}')
    for m in matches:
        print(f"  Rank {m.get('rank')}: Score={m.get('professional_match_score')}% | Job={m.get('job_title')} | Company={m.get('company_info', {}).get('company_name')}")
        print("  Scores block:", m.get('scores'))
        reqs = m.get('accessibility_requirements', [])
        print(f"  Accessibility reqs ({len(reqs)}):")
        for r in reqs:
            print(f"    - [{r.get('status')}] {r.get('preference')} | Details: {r.get('details')}")
    print('\nFull response (keys):', list(data.keys()))
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
