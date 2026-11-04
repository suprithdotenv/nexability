import sys
sys.path.insert(0, r'D:\sap\nexability\backend')

from app.db.session import SessionLocal
from app.models.job_document import JobDocument
from app.models.job_document_profile import JobDocumentProfile
from app.automated_pipeline.models import JobDocumentChunk, CandidateResumeChunk
from app.models.resume import Resume
from app.models.candidate_resume_profile import CandidateResumeProfile

db = SessionLocal()
print('=== FINAL DATABASE VERIFICATION ===')
print('Job Documents:', db.query(JobDocument).count())
for j in db.query(JobDocument).all():
    print(f'  - Job Doc ID: {j.id} | Status: {j.status} | File: {j.original_filename}')

print('Job Document Chunks (Neon pgvector):', db.query(JobDocumentChunk).count())
print('Job Document Profiles:', db.query(JobDocumentProfile).count())
for jp in db.query(JobDocumentProfile).all():
    title = jp.profile_json.get('job_title') if jp.profile_json else None
    print(f'  - Profile ID: {jp.id} | Status: {jp.status} | Title: {title}')

print('Candidate Resumes:', db.query(Resume).count())
for r in db.query(Resume).all():
    print(f'  - Resume ID: {r.id} | File: {r.original_filename} | Active: {r.is_active}')

print('Candidate Resume Chunks (Neon pgvector):', db.query(CandidateResumeChunk).count())
print('Candidate Resume Profiles:', db.query(CandidateResumeProfile).count())
for cp in db.query(CandidateResumeProfile).all():
    skills_cnt = cp.profile_json.get('skills_count') if cp.profile_json else None
    print(f'  - Profile ID: {cp.id} | Status: {cp.status} | Skills count: {skills_cnt}')

db.close()
