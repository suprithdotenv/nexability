import io
import zipfile

from nexability_ml.api_client import InternalMLClient
from nexability_ml.chunking import chunk_document_text
from nexability_ml.config import PROFESSIONAL_EVIDENCE_WEIGHTS
from nexability_ml.matcher import match_candidate_to_jobs
from nexability_ml.normalizer import normalize_job_description, normalize_resume_profile
from nexability_ml.parser import parse_document_bytes
from nexability_ml.pipeline import NexAbilityMLPipeline


def _build_docx_bytes(text: str) -> bytes:
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr(
            "word/document.xml",
            (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                "<w:body><w:p><w:r><w:t>" + text + "</w:t></w:r></w:p></w:body></w:document>"
            ),
        )
    return archive.getvalue()


def test_resume_profile_normalization():
    profile = normalize_resume_profile(
        "Jane Doe\nPython, SQL, communication\nSenior Data Analyst at Acme",
        candidate_id="cand-1",
    )
    assert profile["candidate_id"] == "cand-1"
    assert profile["full_name"] == "Jane Doe"
    assert "python" in profile["skills"]


def test_job_profile_normalization():
    profile = normalize_job_description(
        "Data Analyst Role\nRequired Skills\n- Python\n- SQL\n- problem solving\n",
        job_id="job-1",
    )
    assert profile["job_title"] == "Data Analyst Role"
    assert profile["required_skills"] == ["Python", "SQL", "problem solving"]
    assert len(profile["requirements"]) == 3


def test_professional_and_accessibility_matches_are_separate():
    match = match_candidate_to_jobs(
        {
            "skills": ["python"],
            "source_text": "TECHNICAL SKILLS\nPython\nPROJECTS\nBuilt a Python data tool.",
        },
        [{"job_id": "job-1", "required_skills": ["python"]}],
    )[0]

    assert match["professional_match"]["professional_evidence_score"]["value"] == 100
    assert match["professional_match"]["required"]["requirements"][0][
        "evidence_status"
    ] == "demonstrated"
    assert match["accessibility_match"] == {"requirements": []}
    assert "overall_score" not in match
    assert "overall_match_score" not in match


def test_every_matched_skill_has_an_exact_resume_quote():
    resume_text = (
        "TECHNICAL SKILLS\nJava (basic), SQL, Python programming\n"
        "PROJECTS\nBuilt a Python utility."
    )
    match = match_candidate_to_jobs(
        {
            "skills": ["java", "sql", "python"],
            "source_text": resume_text,
            "education": [],
        },
        [
            {
                "required_skills": ["java", "sql"],
                "preferred_skills": ["python"],
            }
        ],
    )[0]["professional_match"]

    for requirement in match["requirements"]:
        if requirement["quote"]:
            assert requirement["quote"] in resume_text


def test_profiled_skill_without_resume_quote_is_not_found():
    match = match_candidate_to_jobs(
        {"skills": ["java"], "source_text": "Worked on software projects."},
        [{"required_skills": ["java"]}],
    )[0]["professional_match"]

    assert match["required"]["requirements"][0]["evidence_status"] == "not_found"
    assert match["required"]["requirements"][0]["quote"] is None


def test_job_skills_are_separated_by_required_and_preferred_sections():
    profile = normalize_job_description(
        "Required Skills\n- Java programming\n- SQL fundamentals\n"
        "Preferred Skills\n- Spring Boot fundamentals\n- JDBC\n"
    )

    assert profile["required_skills"] == ["Java programming", "SQL fundamentals"]
    assert profile["preferred_skills"] == ["Spring Boot fundamentals", "JDBC"]
    assert [item["priority"] for item in profile["requirements"]] == [
        "required",
        "required",
        "preferred",
        "preferred",
    ]


def test_java_does_not_match_javascript():
    profile = normalize_resume_profile("JavaScript developer with React experience")
    assert "javascript" in profile["skills"]
    assert "java" not in profile["skills"]


def _professional_result(resume_text, job_text):
    profile = normalize_job_description(job_text)
    return match_candidate_to_jobs(
        {"source_text": resume_text},
        [profile],
    )[0]["professional_match"]


def test_job_parser_preserves_bullets_across_all_requested_sections():
    job_text = (
        "Required Skills\n- Java\n- SQL\n- Unrecognized build tool\n"
        "Preferred Skills\n- Spring Boot\n- JDBC\n"
        "Responsibilities\n- Review pull requests\n- Help onboard teammates\n"
        "Domain Knowledge\n- Event-driven systems\n- Distributed tracing\n"
        "Education\n- Bachelor's degree in Computer Science\n"
        "Experience\n- Fresher / Internship\n"
    )

    profile = normalize_job_description(job_text)

    assert len(profile["requirements"]) == 11
    assert profile["required_skills"] == [
        "Java",
        "SQL",
        "Unrecognized build tool",
    ]
    assert profile["preferred_skills"] == ["Spring Boot", "JDBC"]
    assert profile["responsibilities"] == [
        "Review pull requests",
        "Help onboard teammates",
    ]
    assert profile["domain_knowledge"] == ["Event-driven systems", "Distributed tracing"]
    assert profile["education_requirements"] == ["Bachelor's degree in Computer Science"]
    assert profile["experience_requirements"] == ["Fresher / Internship"]
    assert profile["requirements"][2]["normalized_skill"] is None


def test_python_evidence_does_not_demonstrate_java():
    result = _professional_result(
        "PROJECTS\nBuilt a Python data-cleaning tool.",
        "Required Skills\n- Java programming",
    )
    item = result["requirements"][0]
    assert item["evidence_status"] == "not_found"
    assert item["quote"] is None


def test_flask_does_not_demonstrate_fastapi_without_explicit_alternatives():
    result = _professional_result(
        "PROJECTS\nBuilt an expense application using Flask.",
        "Required Skills\n- FastAPI",
    )
    assert result["requirements"][0]["evidence_status"] == "not_found"


def test_java_evidence_does_not_demonstrate_javascript():
    result = _professional_result(
        "TECHNICAL SKILLS\nJava",
        "Required Skills\n- JavaScript",
    )
    assert result["requirements"][0]["evidence_status"] == "not_found"


def test_java_listing_does_not_demonstrate_java_collections():
    result = _professional_result(
        "TECHNICAL SKILLS\nJava",
        "Required Skills\n- Java collections framework",
    )
    item = result["requirements"][0]
    assert item["evidence_status"] == "partial"
    assert "Java is mentioned" in item["explanation"]
    assert item["quote"] == "Java"


def test_error_handling_is_only_partial_evidence_for_exception_handling():
    result = _professional_result(
        "PROJECTS\nUsed SQLite and practiced error handling.",
        "Required Skills\n- Exception handling",
    )
    item = result["requirements"][0]
    assert item["evidence_status"] == "partial"
    assert "exception-specific" in item["explanation"]
    assert item["quote"] == "Used SQLite and practiced error handling."


def test_sqlite_does_not_satisfy_mysql_or_postgresql_alternative():
    result = _professional_result(
        "PROJECTS\nUsed SQLite to persist records.",
        "Preferred Skills\n- MySQL or PostgreSQL",
    )
    assert result["requirements"][0]["evidence_status"] == "not_found"


def test_generic_code_mention_does_not_establish_code_review():
    result = _professional_result(
        "PROJECTS\nWrote readable code for a class project.",
        "Responsibilities\n- Participate in code reviews",
    )
    assert result["requirements"][0]["evidence_status"] == "not_found"


def test_junior_title_does_not_establish_mentoring_or_performance_tuning():
    result = _professional_result(
        "JUNIOR PYTHON DEVELOPER\nPROJECTS\nStudent Performance Analyzer",
        "Required Skills\n- Mentoring junior developers\n- Performance tuning",
    )
    assert [item["evidence_status"] for item in result["requirements"]] == [
        "not_found",
        "not_found",
    ]


def test_skills_only_java_is_listed_not_demonstrated():
    result = _professional_result(
        "TECHNICAL SKILLS\nJava",
        "Required Skills\n- Java",
    )
    assert result["requirements"][0]["evidence_status"] == "listed"


def test_explicit_framework_alternatives_accept_any_one_listed_option():
    result = _professional_result(
        "TECHNICAL SKILLS\nFlask (basic)",
        "Preferred Skills\n- Flask, FastAPI, or Django",
    )
    assert result["requirements"][0]["evidence_status"] == "listed"
    assert result["requirements"][0]["quote"] == "Flask (basic)"


def test_fresher_internship_experience_is_not_applicable():
    profile = normalize_job_description(
        "Java Developer Intern\nExperience: Fresher / Internship\n"
        "Required Skills\n- Java"
    )
    result = match_candidate_to_jobs({"source_text": "TECHNICAL SKILLS\nJava"}, [profile])[0][
        "professional_match"
    ]
    experience = next(item for item in result["requirements"] if item["category"] == "experience")
    assert experience["evidence_status"] == "not_applicable"
    assert experience["requirement_assessment"] == "not_applicable"


def test_education_listing_and_qualification_assessment_are_separate():
    result = _professional_result(
        "EDUCATION\nB.Tech / B.E. in Computer Science",
        "Education\n- Bachelor's degree in Computer Science",
    )
    education = result["education"]
    assert education["evidence_status"] == "listed"
    assert education["requirement_assessment"] == "met"
    assert education["credential_verification"] == "not_independently_verified"
    assert education["quote"] == "B.Tech / B.E. in Computer Science"


def test_invented_requirement_is_not_found():
    result = _professional_result(
        "TECHNICAL SKILLS\nJava, Python, SQL",
        "Required Skills\n- certified scuba instructor",
    )
    assert result["requirements"][0]["evidence_status"] == "not_found"
    assert result["requirements"][0]["quote"] is None


def test_unevaluated_required_requirement_makes_score_unavailable():
    result = _professional_result(
        "TECHNICAL SKILLS\nJava",
        "Required Skills\n- and or with",
    )
    assert result["requirements"][0]["evidence_status"] == "unevaluated"
    assert result["professional_evidence_score"]["status"] == "unavailable"
    assert result["professional_evidence_score"]["value"] is None
    assert result["professional_evidence_score"]["required_counts"]["unevaluated"] == 1


def test_available_score_uses_configured_weights_and_reports_counts():
    result = _professional_result(
        "TECHNICAL SKILLS\nJava\nPROJECTS\nBuilt a Python data tool.",
        "Required Skills\n- Java\n- Kubernetes\n- Python",
    )
    score = result["professional_evidence_score"]
    expected = (
        PROFESSIONAL_EVIDENCE_WEIGHTS["listed"]
        + PROFESSIONAL_EVIDENCE_WEIGHTS["not_found"]
        + PROFESSIONAL_EVIDENCE_WEIGHTS["demonstrated"]
    ) / 3 * 100
    assert score["status"] == "available"
    assert score["value"] == expected
    assert score["required_counts"]["listed"] == 1
    assert score["required_counts"]["not_found"] == 1
    assert score["required_counts"]["demonstrated"] == 1


def test_empty_resume_is_unevaluated_not_a_missing_skill():
    result = _professional_result(
        "",
        "Required Skills\n- Java",
    )
    assert result["requirements"][0]["evidence_status"] == "unevaluated"
    assert result["professional_evidence_score"]["status"] == "unavailable"


def test_synthetic_senior_java_backend_control_job_is_evaluated_independently():
    senior_job = normalize_job_description(
        "Senior Java Backend Developer\n"
        "Experience: 6+ years\n"
        "Required: Java 17, Spring Boot, microservices architecture, REST API design, "
        "PostgreSQL query optimization, Kafka or RabbitMQ, Docker and Kubernetes, "
        "system design, mentoring junior developers\n"
        "Preferred: AWS, CI/CD pipelines, performance tuning\n"
        "Education: Bachelor's degree in Computer Science"
    )
    resume = (
        "TECHNICAL SKILLS\nPython, SQL, Java (basic), JavaScript (basic)\n"
        "Libraries & Tools\nPandas, NumPy, Matplotlib, Git, GitHub, VS Code\n"
        "Backend & Data\nFlask (basic), REST API fundamentals, MySQL\n"
        "Core Concepts\nOOP, data structures, debugging, exception handling\n"
        "PROJECTS\n"
        "Student Performance Analyzer | Python, Pandas\n"
        "Created a data-analysis tool to load student marks from CSV files.\n"
        "Personal Expense Tracker API | Python, Flask, SQLite\n"
        "Developed a beginner-level REST API to manage expense records.\n"
        "EDUCATION\nB.Tech / B.E. in Computer Science\n"
        "EXPERIENCE & ACTIVITIES\nAcademic Coding Projects & Team Collaboration | 2024–2026"
    )

    match = match_candidate_to_jobs(
        {"source_text": resume},
        [senior_job],
    )[0]["professional_match"]

    assert len(match["requirements"]) == 14
    assert match["professional_evidence_score"]["status"] == "available"
    experience = next(item for item in match["requirements"] if item["category"] == "experience")
    assert experience["evidence_status"] == "not_found"
    assert experience["quote"] is None
    for item in match["requirements"]:
        if item["quote"]:
            assert item["quote"] in resume


def test_multiple_jobs_are_evaluated_separately():
    results = match_candidate_to_jobs(
        {"source_text": "TECHNICAL SKILLS\nJava"},
        [
            {"job_id": "java", "required_skills": ["Java"]},
            {"job_id": "python", "required_skills": ["Python"]},
        ],
    )
    by_id = {item["job_id"]: item["professional_match"] for item in results}
    assert by_id["java"]["requirements"][0]["evidence_status"] == "listed"
    assert by_id["python"]["requirements"][0]["evidence_status"] == "not_found"
    assert len(by_id) == 2


def test_no_overall_score_key_exists_anywhere():
    result = match_candidate_to_jobs(
        {"source_text": "TECHNICAL SKILLS\nJava"},
        [{"required_skills": ["Java"]}],
    )[0]

    def keys(value):
        if isinstance(value, dict):
            yield from value.keys()
            for child in value.values():
                yield from keys(child)
        elif isinstance(value, list):
            for child in value:
                yield from keys(child)

    assert "overall_score" not in set(keys(result))
    assert "overall_match_score" not in set(keys(result))


def test_resume_chunking_covers_every_character_without_model_loading():
    resume = "Résumé\n  " + ("Java and Python. " * 120) + "\n"
    chunks = chunk_document_text(resume, max_chars=64)
    assert "".join(chunk["text"] for chunk in chunks) == resume


def test_accessibility_details_never_enter_logs_or_resume_chunks(caplog):
    private_details = "private accessibility details must stay private"
    resume_text = "RIYA SHARMA\nTECHNICAL SKILLS\nPython"
    result = NexAbilityMLPipeline().process_resume_document(
        document_bytes=_build_docx_bytes(resume_text),
        filename="resume.docx",
        candidate_id="candidate-1",
        candidate_profile={"accessibility": {"details": private_details}},
    )
    assert private_details not in caplog.text
    assert all(private_details not in chunk["text"] for chunk in result["chunks"])


def test_bearer_header_uses_supplied_token_without_logging_it(caplog):
    supplied_token = "unit-test-token-never-log"
    headers = InternalMLClient("https://backend.example")._build_headers(
        access_token=supplied_token
    )
    assert headers["Authorization"] == "Be" + "arer " + supplied_token
    assert supplied_token not in caplog.text


def test_accessibility_marks_unlisted_need_missing_for_completed_profile():
    matches = match_candidate_to_jobs(
        {},
        [{"job_id": "job-1", "required_skills": []}],
        candidate_accessibility_preferences=[
            {"category": "SCREEN_READER", "preference": "Screen reader support", "is_active": True},
            {"category": "CAPTIONS", "preference": "Live captions", "is_active": True},
        ],
        employer_accessibility_capabilities=[
            {
                "category": "SCREEN_READER",
                "capability": "Screen reader support",
                "status": "AVAILABLE",
            }
        ],
        employer_profile_completed=True,
    )

    requirements = matches[0]["accessibility_match"]["requirements"]
    assert [item["status"] for item in requirements] == ["confirmed", "missing"]
    assert {item["status"] for item in requirements} <= {
        "confirmed",
        "unverified",
        "missing",
        "unknown",
    }


def test_similar_but_different_employer_tool_is_unverified():
    matches = match_candidate_to_jobs(
        {},
        [{"job_id": "job-1", "required_skills": []}],
        candidate_accessibility_preferences=[
            {"category": "SCREEN_READER", "preference": "Screen reader support", "is_active": True}
        ],
        employer_accessibility_capabilities=[
            {
                "category": "SCREEN_READER",
                "capability": "Screen reader compatible systems",
                "status": "AVAILABLE",
            }
        ],
        employer_profile_completed=True,
    )

    requirement = matches[0]["accessibility_match"]["requirements"][0]
    assert requirement == {
        "requirement": "Screen reader support",
        "status": "unverified",
        "evidence": "Screen reader compatible systems",
    }


def test_accessibility_similarity_rule_examples_include_non_similar_tool():
    cases = [
        (
            "Screen reader support",
            "Screen reader compatible systems",
            "SCREEN_READER",
            "SCREEN_READER",
            "unverified",
        ),
        (
            "Live captions",
            "Captions available on request",
            "CAPTIONS",
            "CAPTIONS",
            "unverified",
        ),
        (
            "Screen reader support",
            "Wheelchair ramp access",
            "SCREEN_READER",
            "MOBILITY",
            "missing",
        ),
    ]
    for need, capability, need_category, capability_category, expected_status in cases:
        result = match_candidate_to_jobs(
            {},
            [{"job_id": "job-1", "required_skills": []}],
            candidate_accessibility_preferences=[
                {"category": need_category, "preference": need, "is_active": True}
            ],
            employer_accessibility_capabilities=[
                {
                    "category": capability_category,
                    "capability": capability,
                    "status": "AVAILABLE",
                }
            ],
            employer_profile_completed=True,
        )[0]["accessibility_match"]["requirements"][0]
        assert result["status"] == expected_status


def test_empty_employer_profile_is_unknown_even_if_completion_flag_is_true():
    matches = match_candidate_to_jobs(
        {},
        [{"job_id": "job-1", "required_skills": []}],
        candidate_accessibility_preferences=[
            {"category": "CAPTIONS", "preference": "Live captions", "is_active": True}
        ],
        employer_accessibility_capabilities=[],
        employer_profile_completed=True,
    )

    assert matches[0]["accessibility_match"]["requirements"][0]["status"] == "unknown"


def test_accessibility_profiles_use_internal_id_scoped_endpoints(monkeypatch):
    client = InternalMLClient("https://backend.example")
    calls = []

    def fake_request(path):
        calls.append(path)
        if "/candidates/candidate-123/" in path:
            return {
                "candidate_id": "candidate-123",
                "preferences": [{"preference": "Live captions", "is_active": True}],
            }
        return {
            "employer_id": "employer-456",
            "profile_completed": True,
            "capabilities": [{"capability": "Captions available", "status": "AVAILABLE"}],
        }

    monkeypatch.setattr(client, "_request", fake_request)
    pipeline = NexAbilityMLPipeline()
    result = pipeline.match_candidates_to_jobs_from_backend(
        {},
        [{"job_id": "job-1", "required_skills": []}],
        repository=client,
        candidate_id="candidate-123",
        employer_id="employer-456",
    )

    assert calls == [
        "/api/v1/internal/ml/employers/employer-456/accessibility",
        "/api/v1/internal/ml/candidates/candidate-123/accessibility",
    ]
    assert result["ranked_jobs"][0]["accessibility_match"]["requirements"] == [
        {
            "requirement": "Live captions",
            "status": "unverified",
            "evidence": "Captions available",
        }
    ]
    assert "/me/" not in str(calls)


def test_docx_parsing_and_pipeline():
    raw = _build_docx_bytes("Jane Doe\nPython SQL")
    extraction = parse_document_bytes(
        raw,
        "resume.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    assert "Jane Doe" in extraction.text

    pipeline = NexAbilityMLPipeline()
    result = pipeline.process_resume_document(
        document_bytes=raw, filename="resume.docx", candidate_id="cand-2"
    )
    assert result["structured_profile"]["candidate_id"] == "cand-2"
    assert result["document_status"] == "processed"


def test_docx_paragraph_runs_remain_a_full_quote():
    archive = io.BytesIO()
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body><w:p><w:r><w:t>Built Java</w:t></w:r>"
        "<w:r><w:t> projects for class.</w:t></w:r></w:p></w:body></w:document>"
    )
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("word/document.xml", xml)
    extraction = parse_document_bytes(archive.getvalue(), "resume.docx")
    assert extraction.text == "Built Java projects for class."
