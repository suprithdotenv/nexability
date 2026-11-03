from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from nexability_ml.chunking import chunk_document_text
from nexability_ml.config import EMBEDDING_DIM, GROQ_API_KEY, GROQ_MODEL
from nexability_ml.embeddings import (
    E5EmbeddingModel,
    E5Tokenizer,
    WhitespaceTokenizer,
    create_embedding_model,
)
from nexability_ml.groq_extraction import (
    GroqExtractionClient,
    GroqExtractionError,
    PrivacyFilterError,
)
from nexability_ml.matcher import match_candidate_to_jobs
from nexability_ml.normalizer import normalize_job_description
from nexability_ml.pipeline import NexAbilityMLPipeline
from nexability_ml.vectorstore import SimpleEmbeddingModel

FIXTURES = Path(__file__).parent / "fixtures"
ML_ROOT = Path(__file__).resolve().parents[1]


def test_configured_placeholder_is_labelled_non_semantic():
    model = create_embedding_model()
    assert isinstance(model, SimpleEmbeddingModel)
    assert model.model_name == "placeholder, not semantic"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _docx_bytes(text: str) -> bytes:
    import io
    import zipfile

    content = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body><w:p><w:r><w:t>" + text + "</w:t></w:r></w:p></w:body></w:document>"
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("word/document.xml", content)
    return output.getvalue()


class FakeGroqCompletions:
    def __init__(self, responses: list[str]):
        self.responses = list(responses)
        self.requests: list[dict] = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        response_text = self.responses.pop(0)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=response_text))]
        )


def _fake_groq_client(*responses: str):
    completions = FakeGroqCompletions(list(responses))
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=completions)
    )
    return client, completions


def test_missing_groq_key_falls_back_to_rule_based():
    client = GroqExtractionClient(api_key="")
    pipeline = NexAbilityMLPipeline(
        embedding_model=SimpleEmbeddingModel(),
        tokenizer=WhitespaceTokenizer(),
        extraction_client=client,
        enable_llm_extraction=True,
    )
    result = pipeline.process_resume_document(
        document_bytes=_docx_bytes("TECHNICAL SKILLS\nJava"),
        filename="resume.docx",
    )
    assert result["extraction_mode"] == "rule_based"
    assert result["llm_extraction"] is None


def test_groq_extraction_is_off_by_default(monkeypatch):
    class UnexpectedExtractor:
        def extract_resume(self, _text):
            raise AssertionError("Groq must remain disabled by default.")

    monkeypatch.setattr("nexability_ml.pipeline.NEXABILITY_LLM_EXTRACTION", False)
    pipeline = NexAbilityMLPipeline(
        embedding_model=SimpleEmbeddingModel(),
        tokenizer=WhitespaceTokenizer(),
        extraction_client=UnexpectedExtractor(),
    )
    result = pipeline.process_resume_document(
        document_bytes=_docx_bytes("TECHNICAL SKILLS\nJava"),
        filename="resume.docx",
    )
    assert result["extraction_mode"] == "rule_based"


def test_groq_failure_falls_back_without_logging_document_or_key(caplog):
    class FailingExtractor:
        def extract_resume(self, _text):
            raise GroqExtractionError("safe generic failure")

    resume = "PRIVATE RESUME TEXT TOKEN"
    pipeline = NexAbilityMLPipeline(
        embedding_model=SimpleEmbeddingModel(),
        tokenizer=WhitespaceTokenizer(),
        extraction_client=FailingExtractor(),
        enable_llm_extraction=True,
    )
    result = pipeline.process_resume_document(
        document_bytes=_docx_bytes(resume),
        filename="resume.docx",
    )
    assert result["extraction_mode"] == "rule_based"
    assert "PRIVATE RESUME TEXT TOKEN" not in caplog.text
    assert "safe generic failure" not in caplog.text


def test_mocked_groq_structured_resume_and_job_extraction():
    fake, requests = _fake_groq_client(_fixture("groq_resume.json"), _fixture("groq_job.json"))
    client = GroqExtractionClient(api_key="test-key", client=fake)
    pipeline = NexAbilityMLPipeline(
        embedding_model=SimpleEmbeddingModel(),
        tokenizer=WhitespaceTokenizer(),
        extraction_client=client,
        enable_llm_extraction=True,
    )
    resume = pipeline.process_resume_document(
        document_bytes=_docx_bytes("TECHNICAL SKILLS\nJava"),
        filename="resume.docx",
    )
    job = pipeline.process_job_document(
        document_bytes=_docx_bytes("Required Skills\n- Java"),
        filename="job.docx",
    )

    assert resume["extraction_mode"] == "llm"
    assert resume["llm_extraction"]["full_name"] is None
    assert resume["llm_extraction"]["skills"] == []
    assert job["extraction_mode"] == "llm"
    assert job["structured_profile"]["requirements"] == [
        {
            "requirement": "Java",
            "category": "required_skills",
            "priority": "required",
            "normalized_skill": "java",
        }
    ]
    assert job["llm_extraction"]["requirement_enrichments"][0][
        "original_requirement"
    ] == "Java"
    assert requests.requests[0]["model"] == GROQ_MODEL


def test_groq_request_payload_excludes_accessibility_data():
    private_values = (
        "candidate-screenreader-private-value",
        "employer-caption-private-value",
    )
    fake, requests = _fake_groq_client(
        _fixture("groq_resume.json"),
        _fixture("groq_job.json"),
    )
    pipeline = NexAbilityMLPipeline(
        embedding_model=SimpleEmbeddingModel(),
        tokenizer=WhitespaceTokenizer(),
        extraction_client=GroqExtractionClient(api_key="test-key", client=fake),
        enable_llm_extraction=True,
    )
    pipeline.process_resume_document(
        document_bytes=_docx_bytes("TECHNICAL SKILLS\nJava"),
        filename="resume.docx",
        candidate_profile={
            "accessibility": {
                "candidate_accessibility_preferences": private_values[0],
                "details": private_values[0],
                "employer_accessibility_capabilities": private_values[1],
            }
        },
    )
    pipeline.process_job_document(
        document_bytes=_docx_bytes("Required Skills\n- Java"),
        filename="job.docx",
    )
    payload = json.dumps(requests.requests)
    for private_value in private_values:
        assert private_value not in payload
    assert "candidate_accessibility_preferences" not in payload
    assert "employer_accessibility_capabilities" not in payload

    text_fake, text_requests = _fake_groq_client(_fixture("groq_job.json"))
    text_client = GroqExtractionClient(api_key="test-key", client=text_fake)
    with pytest.raises(PrivacyFilterError):
        text_client.extract_resume(
            "Skills\nJava\nAccessibility Needs:\nScreen reader private detail value"
        )
    with pytest.raises(PrivacyFilterError):
        text_client.enrich_job(
            "Required Skills\n- Java\nAccessibility Capabilities:\n"
            "Employer caption private detail value",
            [
                {"requirement": "Java"},
                {"requirement": "Screen reader support"},
            ],
        )
    sanitized_payload = json.dumps(text_requests.requests)
    assert "Screen reader private detail value" not in sanitized_payload
    assert "Employer caption private detail value" not in sanitized_payload
    assert "Screen reader support" not in sanitized_payload


def test_groq_enrichment_cannot_drop_or_invent_requirements():
    fake, _ = _fake_groq_client(_fixture("groq_job.json"))
    pipeline = NexAbilityMLPipeline(
        embedding_model=SimpleEmbeddingModel(),
        tokenizer=WhitespaceTokenizer(),
        extraction_client=GroqExtractionClient(api_key="test-key", client=fake),
        enable_llm_extraction=True,
    )
    raw_job = "Required Skills\n- Java\n- PostgreSQL"
    result = pipeline.process_job_document(
        document_bytes=_docx_bytes(raw_job),
        filename="job.docx",
    )
    requirements = result["structured_profile"]["requirements"]
    assert result["extraction_mode"] == "rule_based"
    assert [item["requirement"] for item in requirements] == ["Java", "PostgreSQL"]


def test_e5_embedding_prefix_dimensions_normalization_and_lazy_loading():
    fixture = json.loads(_fixture("e5_embeddings.json"))

    class FakeSentenceModel:
        def __init__(self):
            self.inputs = []

        def encode(self, texts, *, normalize_embeddings, convert_to_numpy):
            assert normalize_embeddings is True
            assert convert_to_numpy is True
            self.inputs.extend(texts)
            rows = []
            for index, _ in enumerate(texts):
                vector = [0.0] * fixture["dimension"]
                vector[fixture["unit_vector_indices"][index % 2]] = 1.0
                rows.append(vector)
            return rows

    loaded = []
    fake_model = FakeSentenceModel()
    embedding = E5EmbeddingModel(
        model_loader=lambda name: loaded.append(name) or fake_model
    )
    assert loaded == []
    vectors = embedding.encode(["Java"], prefix="passage: ")
    vectors += embedding.encode(["Java"], prefix="query: ")
    assert loaded == ["intfloat/e5-base-v2"]
    assert fake_model.inputs == ["passage: Java", "query: Java"]
    assert len(vectors) == 2
    assert all(len(vector) == EMBEDDING_DIM for vector in vectors)
    assert all(math.isclose(sum(value * value for value in row), 1.0) for row in vectors)


def test_explicit_e5_model_failure_is_not_replaced_by_placeholder():
    model = E5EmbeddingModel(model_loader=lambda _name: (_ for _ in ()).throw(OSError()))
    with pytest.raises(RuntimeError, match="Could not load configured embedding model"):
        model.encode(["Java"])


def test_e5_rejects_wrong_vector_dimensions():
    class WrongDimensionModel:
        def encode(self, _texts, **_kwargs):
            return [[1.0, 0.0]]

    model = E5EmbeddingModel(model_loader=lambda _name: WrongDimensionModel())
    with pytest.raises(RuntimeError, match="configuration requires"):
        model.encode(["Java"])


def test_semantic_retrieval_only_reorders_evidence_and_preserves_assessments():
    class DeterministicE5Fixture:
        def encode(self, texts, **_kwargs):
            vectors = []
            for text in texts:
                vector = [0.0] * EMBEDDING_DIM
                for token in text.casefold().split():
                    vector[sum(token.encode("utf-8")) % EMBEDDING_DIM] += 1.0
                norm = math.sqrt(sum(value * value for value in vector)) or 1.0
                vectors.append([value / norm for value in vector])
            return vectors

    resume = (
        "TECHNICAL SKILLS\nJava (basic), Python\n"
        "PROJECTS\nDeveloped a beginner-level Java REST API."
    )
    jobs = [
        normalize_job_description("Required Skills\n- Java", job_id="java"),
        normalize_job_description(
            "Required Skills\n- Spring Boot\n- REST API design", job_id="senior"
        ),
    ]
    candidate = {"source_text": resume}
    before = {
        result["job_id"]: result for result in match_candidate_to_jobs(candidate, jobs)
    }
    after_list = NexAbilityMLPipeline(
        embedding_model=E5EmbeddingModel(
            model_loader=lambda _name: DeterministicE5Fixture()
        ),
        tokenizer=WhitespaceTokenizer(),
    ).match_candidates_to_jobs(candidate, jobs)["ranked_jobs"]
    after = {result["job_id"]: result for result in after_list}

    for job_id in before:
        before_items = before[job_id]["professional_match"]["requirements"]
        after_items = after[job_id]["professional_match"]["requirements"]
        assert [item["evidence_status"] for item in before_items] == [
            item["evidence_status"] for item in after_items
        ]
        assert all(item["quote"] is None or item["quote"] in resume for item in after_items)


def _assert_full_character_coverage(text: str, chunks: list[dict]) -> None:
    covered = bytearray(len(text))
    for chunk in chunks:
        start = chunk["metadata"]["char_start"]
        end = chunk["metadata"]["char_end"]
        assert text[start:end] == chunk["text"]
        covered[start:end] = b"\x01" * (end - start)
        assert chunk["metadata"]["section_name"]
        assert chunk["metadata"]["chunk_index"] == chunk["chunk_index"]
    assert all(covered)


def test_token_chunking_empty_and_short_inputs_with_fake_tokenizer():
    tokenizer = WhitespaceTokenizer()
    assert chunk_document_text("", tokenizer=tokenizer) == []
    short = "A short résumé line."
    chunks = chunk_document_text(short, tokenizer=tokenizer)
    assert len(chunks) == 1
    assert chunks[0]["text"] == short
    _assert_full_character_coverage(short, chunks)


def test_token_chunking_exact_boundary_and_overlap_with_fake_tokenizer():
    tokenizer = WhitespaceTokenizer()
    exact = "one two three four"
    exact_chunks = chunk_document_text(
        exact,
        chunk_size_tokens=4,
        chunk_overlap_tokens=1,
        tokenizer=tokenizer,
    )
    assert len(exact_chunks) == 1
    _assert_full_character_coverage(exact, exact_chunks)

    overlapping = "one two three four five six seven"
    chunks = chunk_document_text(
        overlapping,
        chunk_size_tokens=4,
        chunk_overlap_tokens=2,
        tokenizer=tokenizer,
    )
    assert len(chunks) > 1
    assert "three four" in chunks[0]["text"]
    assert "three four" in chunks[1]["text"]
    _assert_full_character_coverage(overlapping, chunks)


def test_token_chunking_long_multisection_text_covers_all_characters():
    text = (
        "TECHNICAL SKILLS\n"
        + ("Java, Python, SQL. " * 120)
        + "\nPROJECTS\n"
        + ("Built a useful application. " * 100)
    )
    chunks = chunk_document_text(
        text,
        chunk_size_tokens=24,
        chunk_overlap_tokens=5,
        tokenizer=WhitespaceTokenizer(),
    )
    _assert_full_character_coverage(text, chunks)
    assert {chunk["metadata"]["section_name"] for chunk in chunks} >= {
        "skills",
        "projects",
    }


def test_e5_tokenizer_is_lazy_and_accepts_a_mock_tokenizer():
    loaded = []

    def tokenizer_loader(name):
        loaded.append(name)
        return lambda text, **_kwargs: {
            "offset_mapping": [match.span() for match in __import__("re").finditer(r"\S+", text)]
        }

    tokenizer = E5Tokenizer(tokenizer_loader=tokenizer_loader)
    assert loaded == []
    assert tokenizer.encode_with_offsets("one two") == [(0, 3), (4, 7)]
    assert loaded == ["intfloat/e5-base-v2"]


def test_model_selection_defaults_to_e5_and_dotenv_path_is_module_relative(tmp_path):
    script = """
import json
import dotenv
dotenv.load_dotenv = lambda **_kwargs: None
from nexability_ml import config
print(json.dumps({
    "model": config.EMBEDDING_MODEL,
    "groq_model": config.GROQ_MODEL,
    "dimension": config.EMBEDDING_DIM,
    "chunk_size": config.CHUNK_SIZE_TOKENS,
    "overlap": config.CHUNK_OVERLAP_TOKENS,
    "dotenv_absolute": config.DOTENV_PATH.is_absolute(),
}))
"""
    environment = os.environ.copy()
    for key in (
        "GROQ_MODEL",
        "EMBEDDING_MODEL",
        "EMBEDDING_DIM",
        "CHUNK_SIZE_TOKENS",
        "CHUNK_OVERLAP_TOKENS",
    ):
        environment.pop(key, None)
        environment[key] = ""
    environment.pop("GROQ_API_KEY", None)
    environment["GROQ_API_KEY"] = ""
    environment["PYTHONPATH"] = str(ML_ROOT)
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    settings = json.loads(result.stdout)
    assert settings == {
        "model": "intfloat/e5-base-v2",
        "groq_model": "openai/gpt-oss-120b",
        "dimension": 768,
        "chunk_size": 180,
        "overlap": 30,
        "dotenv_absolute": True,
    }


def test_config_does_not_depend_on_process_working_directory():
    script = """
import json
from nexability_ml import config
print(json.dumps({
    "embedding_model": config.EMBEDDING_MODEL,
    "groq_key_configured": bool(config.GROQ_API_KEY),
}))
"""
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ML_ROOT)
    environment["PYTHON_DOTENV_DISABLED"] = "1"
    environment["GROQ_API_KEY"] = "test-only-key"
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(sys.executable).parent,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    settings = json.loads(result.stdout)
    assert settings["groq_key_configured"] is True


@pytest.mark.integration
@pytest.mark.skipif(
    not GROQ_API_KEY or os.getenv("NEXABILITY_RUN_GROQ_INTEGRATION") != "1",
    reason="Requires GROQ_API_KEY and NEXABILITY_RUN_GROQ_INTEGRATION=1.",
)
def test_live_groq_integration():
    extracted = GroqExtractionClient().extract_resume(
        "Skills\n- Java\nEducation\n- Bachelor's degree in Computer Science"
    )
    assert extracted is not None
    assert extracted.skills


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("NEXABILITY_RUN_E5_INTEGRATION") != "1",
    reason="Requires NEXABILITY_RUN_E5_INTEGRATION=1; model downloads are not automatic.",
)
def test_live_e5_embedding_and_tokenizer_integration():
    vectors = E5EmbeddingModel().encode(
        ["A résumé sentence."], prefix="passage: "
    )
    offsets = E5Tokenizer().encode_with_offsets("A résumé sentence.")
    assert len(vectors) == 1
    assert len(vectors[0]) == EMBEDDING_DIM
    assert offsets
