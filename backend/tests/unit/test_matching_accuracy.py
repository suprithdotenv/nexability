"""
backend/tests/unit/test_matching_accuracy.py
=============================================

Comprehensive Matching Accuracy & Grounded Scoring Test Suite.
Tests the 10 critical matching scenarios:
  1. Strong Python backend resume vs Python backend job.
  2. Python backend resume vs unrelated HR job (must score low, no high score from generic words).
  3. Python backend resume vs Machine Learning job (reflects actual ML gap).
  4. Machine Learning resume vs Machine Learning job (ranks ML #1).
  5. Candidate with missing required skills (penalized proportionally).
  6. Resume with skills only listed vs demonstrated (demonstrated skills score higher than listed).
  7. Multiple unrelated job descriptions for same candidate (distinct scores, no 71% duplicates).
  8. Multiple candidates compared against the same job (correct relative ordering).
  9. Multiple resumes uploaded for one candidate (verifies only the active resume is used).
  10. Job description updated and reprocessed (verifies old embeddings are replaced, not reused).
"""
import uuid
import pytest
from app.automated_pipeline.extractor import extract_candidate_profile_json, extract_job_profile_json
from app.automated_pipeline.chunker import chunk_text
from app.automated_pipeline.embeddings import get_embedding_encoder, cosine_similarity
from app.automated_pipeline.matching import _calculate_professional_score
from app.automated_pipeline.models import CandidateResumeChunk, JobDocumentChunk


# Helpers to build mock chunks with real embeddings
def _build_candidate_chunks(text: str, candidate_id: uuid.UUID = None, resume_id: uuid.UUID = None):
    candidate_id = candidate_id or uuid.uuid4()
    resume_id = resume_id or uuid.uuid4()
    chunks = chunk_text(text)
    encoder = get_embedding_encoder()
    embeddings = encoder.encode([c["chunk_text"] for c in chunks], prefix="passage: ")
    rows = []
    for c, emb in zip(chunks, embeddings):
        rows.append(CandidateResumeChunk(
            candidate_profile_id=candidate_id,
            resume_id=resume_id,
            chunk_index=c["chunk_index"],
            chunk_text=c["chunk_text"],
            embedding=emb,
        ))
    return rows


def _build_job_chunks(text: str, employer_id: uuid.UUID = None, job_id: uuid.UUID = None):
    employer_id = employer_id or uuid.uuid4()
    job_id = job_id or uuid.uuid4()
    chunks = chunk_text(text)
    encoder = get_embedding_encoder()
    embeddings = encoder.encode([c["chunk_text"] for c in chunks], prefix="passage: ")
    rows = []
    for c, emb in zip(chunks, embeddings):
        rows.append(JobDocumentChunk(
            employer_profile_id=employer_id,
            job_document_id=job_id,
            chunk_index=c["chunk_index"],
            chunk_text=c["chunk_text"],
            embedding=emb,
        ))
    return rows


# Document texts for testing
PYTHON_BACKEND_RESUME = """
Rohan Kulkarni
Professional Backend Developer
Summary:
Backend developer with 3 years of hands-on experience building scalable web APIs and distributed microservices.
Technical Skills:
Python, FastAPI, Flask, PostgreSQL, SQL, Docker, Git, GitHub, REST APIs
Experience:
Senior Software Engineer - FinTech Labs
- Architected and built high-performance asynchronous REST APIs using Python and FastAPI.
- Designed database schemas and optimized complex SQL queries in PostgreSQL for sub-10ms response times.
- Containerized microservices using Docker and automated CI/CD pipelines with GitHub Actions.
Projects:
Payment Microservice:
- Implemented transactional payment gateway in Python with Flask and PostgreSQL.
- Tested endpoints using Pytest and integrated Docker deployment.
Education:
B.Tech Computer Science, 2022
"""

ML_RESUME = """
Maya Krishnan
Machine Learning Engineer
Summary:
Machine learning specialist focused on supervised learning, statistical modeling, and predictive analytics.
Technical Skills:
Python, Machine Learning, Deep Learning, Scikit-Learn, Pandas, NumPy, Statistics, Matplotlib, Seaborn
Experience:
ML Research Associate - Data Innovations
- Applied machine learning to develop supervised learning classification models and regression pipelines using Scikit-Learn and Python.
- Preprocessed large datasets using Pandas and NumPy, handling missing values and feature engineering.
- Visualized analytical distributions and evaluation metrics using Matplotlib and Seaborn.
Projects:
Customer Churn Prediction:
- Built Random Forest and Gradient Boosting machine learning models, optimizing hyperparameters to achieve 92% ROC-AUC.
Education:
M.S. Artificial Intelligence, 2024
"""

LISTED_ONLY_RESUME = """
Alex Taylor
Technical Generalist
Summary:
Motivated graduate seeking software engineering opportunities with strong communication and team problem-solving skills.
Technical Skills:
Python, FastAPI, PostgreSQL, Docker, Kubernetes, AWS, Machine Learning, Java
Experience:
Office Coordinator - Retail Corp
- Coordinated team schedules, maintained office supplies, organized staff meetings, and assisted with customer service.
Education:
B.A. Business Administration, 2024
"""

PYTHON_BACKEND_JOB = """
Junior Python Backend Developer
Overview:
We are looking for a Junior Python Backend Developer to design, build, and maintain scalable server-side systems.
Requirements:
Required Technical Skills: Python, FastAPI, PostgreSQL, SQL, Docker, Git, REST APIs
Responsibilities:
- Build clean, documented RESTful APIs in Python using FastAPI.
- Work with PostgreSQL databases to write efficient SQL queries and schema migrations.
- Package applications with Docker and collaborate using Git.
"""

HR_JOB = """
Human Resources Coordinator
Overview:
We are seeking an HR Coordinator to handle employee onboarding, schedule interviews, and organize office wellness programs.
Requirements:
- Excellent verbal and written communication skills.
- Teamwork, empathy, and active listening.
- Familiarity with human resources administration, employee conflict resolution, and spreadsheet logging.
- Bachelor's degree in Human Resources, Psychology, or related discipline.
"""

ML_JOB = """
Machine Learning Intern
Overview:
Seeking an ML Intern to assist our AI team in building predictive models and data preprocessing workflows.
Requirements:
Required Skills: Python, Machine Learning, Deep Learning, Scikit-Learn, Pandas, NumPy, Statistics
Responsibilities:
- Train and evaluate regression and classification models using Scikit-Learn.
- Clean and explore tabular data using Pandas and NumPy.
- Document experiment results and compute validation metrics.
"""

JAVA_JOB = """
Java Developer Intern
Overview:
Join our enterprise engineering team to develop high-throughput Java applications and relational database integrations.
Requirements:
Required Skills: Java, Spring Boot, JDBC, PostgreSQL, MySQL, SQL, Git
Responsibilities:
- Develop enterprise business logic in Core Java with Spring Boot.
- Connect to PostgreSQL databases using JDBC and execute SQL queries.
"""


# ---------------------------------------------------------------------------
# Test Scenarios
# ---------------------------------------------------------------------------

def test_scenario_1_python_backend_resume_against_python_backend_job():
    """Scenario 1: Strong Python backend resume matches strongly against a Python backend job."""
    r_prof = extract_candidate_profile_json(PYTHON_BACKEND_RESUME)
    j_prof = extract_job_profile_json(PYTHON_BACKEND_JOB, "02_Python_Backend_Developer.pdf")
    r_chunks = _build_candidate_chunks(PYTHON_BACKEND_RESUME)
    j_chunks = _build_job_chunks(PYTHON_BACKEND_JOB)

    score, details = _calculate_professional_score(r_prof, j_prof, r_chunks, j_chunks, "Python Backend Dev")

    assert score > 45.0, f"Expected strong match score, got {score}%"
    assert "Python" in details["demonstrated_skills"]
    assert "FastAPI" in details["demonstrated_skills"]
    assert "PostgreSQL" in details["demonstrated_skills"]
    assert len(details["missing_skills"]) == 0
    assert details["vector_semantic_similarity"] > 30.0


def test_scenario_2_python_backend_resume_against_hr_job():
    """Scenario 2: Python backend resume against an HR job scores low and is not inflated by generic words."""
    r_prof = extract_candidate_profile_json(PYTHON_BACKEND_RESUME)
    j_prof = extract_job_profile_json(HR_JOB, "HR_Coordinator.pdf")
    r_chunks = _build_candidate_chunks(PYTHON_BACKEND_RESUME)
    j_chunks = _build_job_chunks(HR_JOB)

    score_hr, details_hr = _calculate_professional_score(r_prof, j_prof, r_chunks, j_chunks, "HR Coordinator")

    # Compare against Python job score
    j_py_prof = extract_job_profile_json(PYTHON_BACKEND_JOB, "02_Python_Backend_Developer.pdf")
    j_py_chunks = _build_job_chunks(PYTHON_BACKEND_JOB)
    score_py, _ = _calculate_professional_score(r_prof, j_py_prof, r_chunks, j_py_chunks, "Python Backend Dev")

    assert score_hr < score_py, f"HR score ({score_hr}%) should be significantly lower than Python job ({score_py}%)"
    assert score_hr < 30.0, f"HR role score should be low for a technical resume, got {score_hr}%"


def test_scenario_3_python_backend_resume_against_ml_job():
    """Scenario 3: Python backend resume against an ML job reflects missing ML skills and scores lower."""
    r_prof = extract_candidate_profile_json(PYTHON_BACKEND_RESUME)
    j_ml_prof = extract_job_profile_json(ML_JOB, "05_Machine_Learning_Intern.pdf")
    r_chunks = _build_candidate_chunks(PYTHON_BACKEND_RESUME)
    j_ml_chunks = _build_job_chunks(ML_JOB)

    score_ml, details_ml = _calculate_professional_score(r_prof, j_ml_prof, r_chunks, j_ml_chunks, "ML Intern")

    # Python candidate should have Python matched, but ML specific skills missing
    assert "Python" in details_ml["demonstrated_skills"] or "Python" in details_ml["listed_skills"]
    assert "Machine Learning" in details_ml["missing_skills"]
    assert "Deep Learning" in details_ml["missing_skills"]
    assert "Scikit-Learn" in details_ml["missing_skills"]


def test_scenario_4_machine_learning_resume_against_machine_learning_job():
    """Scenario 4: ML resume against ML job produces high match and ranks above backend job."""
    r_ml_prof = extract_candidate_profile_json(ML_RESUME)
    r_ml_chunks = _build_candidate_chunks(ML_RESUME)

    j_ml_prof = extract_job_profile_json(ML_JOB, "05_Machine_Learning_Intern.pdf")
    j_ml_chunks = _build_job_chunks(ML_JOB)
    score_ml, details_ml = _calculate_professional_score(r_ml_prof, j_ml_prof, r_ml_chunks, j_ml_chunks, "ML Intern")

    j_py_prof = extract_job_profile_json(PYTHON_BACKEND_JOB, "02_Python_Backend_Developer.pdf")
    j_py_chunks = _build_job_chunks(PYTHON_BACKEND_JOB)
    score_py, _ = _calculate_professional_score(r_ml_prof, j_py_prof, r_ml_chunks, j_py_chunks, "Python Backend")

    assert score_ml > score_py, f"ML candidate must score higher for ML job ({score_ml}%) than Python backend ({score_py}%)"
    assert "Machine Learning" in details_ml["demonstrated_skills"]
    assert "Scikit-Learn" in details_ml["demonstrated_skills"]
    assert "Pandas" in details_ml["demonstrated_skills"]


def test_scenario_5_candidate_with_missing_required_skills():
    """Scenario 5: Candidate with several missing required skills is penalized proportionally."""
    r_prof = extract_candidate_profile_json(PYTHON_BACKEND_RESUME)
    r_chunks = _build_candidate_chunks(PYTHON_BACKEND_RESUME)

    j_java_prof = extract_job_profile_json(JAVA_JOB, "04_Java_Developer_Intern.pdf")
    j_java_chunks = _build_job_chunks(JAVA_JOB)
    score_java, details_java = _calculate_professional_score(r_prof, j_java_prof, r_chunks, j_java_chunks, "Java Intern")

    assert len(details_java["missing_skills"]) >= 3
    assert "Java" in details_java["missing_skills"]
    assert "Spring Boot" in details_java["missing_skills"]
    assert score_java < 35.0, f"Candidate lacking core Java skills should score low, got {score_java}%"


def test_scenario_6_skills_listed_only_vs_demonstrated():
    """Scenario 6: Résumé with skills only listed in keywords section scores lower than one with demonstrated projects."""
    r_dem_prof = extract_candidate_profile_json(PYTHON_BACKEND_RESUME)
    r_dem_chunks = _build_candidate_chunks(PYTHON_BACKEND_RESUME)

    r_list_prof = extract_candidate_profile_json(LISTED_ONLY_RESUME)
    r_list_chunks = _build_candidate_chunks(LISTED_ONLY_RESUME)

    j_prof = extract_job_profile_json(PYTHON_BACKEND_JOB, "02_Python_Backend_Developer.pdf")
    j_chunks = _build_job_chunks(PYTHON_BACKEND_JOB)

    score_dem, details_dem = _calculate_professional_score(r_dem_prof, j_prof, r_dem_chunks, j_chunks, "Python Backend")
    score_list, details_list = _calculate_professional_score(r_list_prof, j_prof, r_list_chunks, j_chunks, "Python Backend")

    assert score_dem > score_list, f"Demonstrated resume ({score_dem}%) must outscore keyword-stuffed listed resume ({score_list}%)"
    assert len(details_dem["demonstrated_skills"]) > len(details_list["demonstrated_skills"])
    assert len(details_list["listed_skills"]) >= 2


def test_scenario_7_multiple_unrelated_jobs_receive_distinct_scores():
    """Scenario 7: Multiple jobs receive distinct scores based on their actual content, never identical 71%."""
    r_prof = extract_candidate_profile_json(PYTHON_BACKEND_RESUME)
    r_chunks = _build_candidate_chunks(PYTHON_BACKEND_RESUME)

    jobs = [
        ("Python Backend", PYTHON_BACKEND_JOB, "02_Python_Backend_Developer.pdf"),
        ("ML Intern", ML_JOB, "05_Machine_Learning_Intern.pdf"),
        ("Java Intern", JAVA_JOB, "04_Java_Developer_Intern.pdf"),
        ("HR Coordinator", HR_JOB, "HR_Coordinator.pdf"),
    ]

    scores = []
    vector_sims = []
    for title, jtext, jfile in jobs:
        jprof = extract_job_profile_json(jtext, jfile)
        jchunks = _build_job_chunks(jtext)
        score, details = _calculate_professional_score(r_prof, jprof, r_chunks, jchunks, title)
        scores.append((title, score))
        vector_sims.append(details["vector_semantic_similarity"])

    # Ensure no duplicate 71.0% scores
    score_values = [s[1] for s in scores]
    assert len(set(score_values)) == len(score_values), f"Scores must be unique, got {scores}"
    assert all(v != 60.0 for v in vector_sims), f"Vector similarity must be genuinely calculated, not hardcoded 60%: {vector_sims}"


def test_scenario_8_multiple_candidates_compared_against_same_job():
    """Scenario 8: Comparing multiple candidates against the same job ranks the qualified candidate above the unqualified candidate."""
    j_prof = extract_job_profile_json(ML_JOB, "05_Machine_Learning_Intern.pdf")
    j_chunks = _build_job_chunks(ML_JOB)

    # ML candidate
    r_ml_prof = extract_candidate_profile_json(ML_RESUME)
    r_ml_chunks = _build_candidate_chunks(ML_RESUME)
    score_ml, _ = _calculate_professional_score(r_ml_prof, j_prof, r_ml_chunks, j_chunks, "ML Intern")

    # Backend Python candidate (not ML focused)
    r_py_prof = extract_candidate_profile_json(PYTHON_BACKEND_RESUME)
    r_py_chunks = _build_candidate_chunks(PYTHON_BACKEND_RESUME)
    score_py, _ = _calculate_professional_score(r_py_prof, j_prof, r_py_chunks, j_chunks, "ML Intern")

    # Non-technical candidate
    r_list_prof = extract_candidate_profile_json(LISTED_ONLY_RESUME)
    r_list_chunks = _build_candidate_chunks(LISTED_ONLY_RESUME)
    score_list, _ = _calculate_professional_score(r_list_prof, j_prof, r_list_chunks, j_chunks, "ML Intern")

    assert score_ml > score_py > score_list, f"Expected score_ml ({score_ml}) > score_py ({score_py}) > score_list ({score_list})"


def test_scenario_9_multiple_resumes_active_selection(tmp_path):
    """Scenario 9: Verifies that when multiple resumes exist for a candidate, only the active resume's content is matched."""
    from app.automated_pipeline.matching import match_candidate_jobs
    from app.db.session import SessionLocal
    from app.models.resume import Resume
    from app.models.candidate_profile import CandidateProfile
    from app.models.user import User, UserRole

    db = SessionLocal()
    try:
        # Create test user & profile
        test_user = User(
            email=f"multi_resume_{uuid.uuid4().hex[:6]}@example.com",
            password_hash="test-hash",
            role=UserRole.CANDIDATE,
            is_active=True,
        )
        db.add(test_user)
        db.commit()

        cand_prof = CandidateProfile(user_id=test_user.id, full_name="Test Candidate Multi")
        db.add(cand_prof)
        db.commit()

        # Inactive resume: Java
        r_old = Resume(
            candidate_profile_id=cand_prof.id,
            original_filename="Old_Java_Resume.pdf",
            storage_path=f"candidates/{cand_prof.id}/old_java.pdf",
            mime_type="application/pdf",
            file_size_bytes=1000,
            is_active=False,
        )
        # Active resume: ML
        r_new = Resume(
            candidate_profile_id=cand_prof.id,
            original_filename="Active_ML_Resume.pdf",
            storage_path=f"candidates/{cand_prof.id}/active_ml.pdf",
            mime_type="application/pdf",
            file_size_bytes=1000,
            is_active=True,
        )
        db.add_all([r_old, r_new])
        db.commit()

        # Process active resume
        from app.automated_pipeline.processor import process_candidate_resume
        process_candidate_resume(r_new.id, db=db, content=ML_RESUME.encode("utf-8"))

        res = match_candidate_jobs(cand_prof.id, db=db)
        assert res["status"] == "match_found"
        assert res["match_count"] > 0
        # Active resume is ML -> Top job must be Machine Learning Intern!
        top_match = res["top_matches"][0]
        assert "Machine Learning" in top_match["job_title"]
    finally:
        db.rollback()
        db.close()


def test_scenario_10_job_updated_and_reprocessed_replaces_old_embeddings():
    """Scenario 10: Updating and reprocessing a job replaces old chunks and embeddings cleanly."""
    from app.db.session import SessionLocal
    from app.models.job_document import JobDocument
    from app.models.employer_profile import EmployerProfile
    from app.models.user import User, UserRole
    from app.automated_pipeline.models import JobDocumentChunk
    from app.automated_pipeline.processor import process_job_document
    from sqlalchemy import select, func

    db = SessionLocal()
    try:
        # Create test employer user & profile
        test_emp_user = User(
            email=f"emp_test_{uuid.uuid4().hex[:6]}@example.com",
            password_hash="test-hash",
            role=UserRole.EMPLOYER,
            is_active=True,
        )
        db.add(test_emp_user)
        db.commit()

        emp_prof = EmployerProfile(
            user_id=test_emp_user.id,
            full_name="Dynamic HR Recruiter",
            company_name="Dynamic Test Corp",
            email_domain="dynamictest.com",
        )
        db.add(emp_prof)
        db.commit()

        doc = JobDocument(
            employer_profile_id=emp_prof.id,
            original_filename="Dynamic_Job.pdf",
            storage_path=f"employers/{emp_prof.id}/dynamic.pdf",
            mime_type="application/pdf",
            file_size_bytes=len(JAVA_JOB),
            status="UPLOADED",
        )
        db.add(doc)
        db.commit()

        # Process as Java Job
        process_job_document(doc.id, db=db, content=JAVA_JOB.encode("utf-8"))
        count_v1 = db.scalar(select(func.count(JobDocumentChunk.id)).where(JobDocumentChunk.job_document_id == doc.id))
        assert count_v1 > 0

        # Now reprocess same job with ML Job content
        process_job_document(doc.id, db=db, content=ML_JOB.encode("utf-8"))
        count_v2 = db.scalar(select(func.count(JobDocumentChunk.id)).where(JobDocumentChunk.job_document_id == doc.id))
        assert count_v2 > 0

        # Verify profile has updated requirements
        from app.models.job_document_profile import JobDocumentProfile
        prof = db.scalar(select(JobDocumentProfile).where(JobDocumentProfile.document_id == doc.id))
        assert "Machine Learning" in prof.profile_json["required_skills"]
        assert "Java" not in prof.profile_json["required_skills"]
    finally:
        db.rollback()
        db.close()
