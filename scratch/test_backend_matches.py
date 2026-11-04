"""Test candidate matches endpoint through backend API with JWT."""
import sys
sys.path.insert(0, r'D:\sap\nexability\backend')

import urllib.request, json
from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.models.user import User
from app.models.candidate_profile import CandidateProfile

db = SessionLocal()
cp = db.query(CandidateProfile).filter(CandidateProfile.id == 'b210a354-e127-4c99-953d-edc07c7081f1').first()
user = db.query(User).filter(User.id == cp.user_id).first() if cp else None
db.close()

if not user:
    print("Could not find candidate user")
    exit(1)

print(f"Candidate User: {user.email} (ID: {user.id})")
token = create_access_token(user_id=str(user.id), role="CANDIDATE")

req = urllib.request.Request(
    'http://localhost:8000/api/v1/candidates/me/matches?min_threshold=60.0',
    headers={'Authorization': f'Bearer {token}'}
)
try:
    res = urllib.request.urlopen(req)
    data = json.loads(res.read())
    print("\n=== BACKEND /api/v1/candidates/me/matches SUCCESS ===")
    print("Status:", data.get("status"))
    print("Match count:", data.get("match_count"))
    for m in data.get("top_matches", []):
        print(f"Rank {m.get('rank')}: {m.get('job_title')} at {m.get('company_info', {}).get('company_name')} | Score: {m.get('professional_match_score')}%")
        print("Scores:", m.get("scores"))
        print("Accessibility match:", m.get("accessibility_match"))
except Exception as e:
    print("Backend call error:", e)
    import traceback
    traceback.print_exc()
