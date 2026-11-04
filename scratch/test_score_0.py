import urllib.request, json

req = urllib.request.Request(
    'http://localhost:8001/api/v1/ml/matches?min_threshold=0.0&force_reprocess=true',
    headers={
        'X-Internal-Service-Key': 'ml-internal-secret-token',
        'X-Candidate-Id': 'b210a354-e127-4c99-953d-edc07c7081f1'
    }
)
res = urllib.request.urlopen(req)
data = json.loads(res.read())
print(f'Match count: {data.get("match_count")}')
for m in data.get('top_matches', []):
    print(f"Rank {m.get('rank')}: Score={m.get('professional_match_score')}% | Job={m.get('job_title')}")
    print("Scores:", m.get('scores'))
    reqs = m.get('professional_match', {}).get('requirements', [])
    print(f"Requirements ({len(reqs)}):")
    for r in reqs:
        print(f"  [{r.get('priority')} - {r.get('category')}] {r.get('requirement')} -> {r.get('evidence_status')} ({r.get('explanation')}) | quote: {r.get('quote')}")
