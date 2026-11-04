from __future__ import annotations

import re
import zipfile
from io import BytesIO
from typing import Any
from xml.etree import ElementTree

# Canonical skill definitions with regex match patterns and canonical names
CANONICAL_SKILL_PATTERNS: list[tuple[str, str]] = [
    (r"\bpython\b", "Python"),
    (r"\bfastapi\b", "FastAPI"),
    (r"\bdjango\b", "Django"),
    (r"\bflask\b", "Flask"),
    (r"\b(postgresql|postgres)\b", "PostgreSQL"),
    (r"\b(mysql|mariadb)\b", "MySQL"),
    (r"\bsql\b", "SQL"),
    (r"\bsqlite\b", "SQLite"),
    (r"\bmongodb\b", "MongoDB"),
    (r"\bredis\b", "Redis"),
    (r"\bkafka\b", "Kafka"),
    (r"\bcelery\b", "Celery"),
    (r"\bdocker\b", "Docker"),
    (r"\b(kubernetes|k8s)\b", "Kubernetes"),
    (r"\baws\b", "AWS"),
    (r"\bazure\b", "Azure"),
    (r"\bgcp\b", "GCP"),
    (r"\bgit\b", "Git"),
    (r"\bgithub\b", "GitHub"),
    (r"\blinux\b", "Linux"),
    (r"\bjava\b", "Java"),
    (r"\bspring\s*boot\b", "Spring Boot"),
    (r"\bspring\b", "Spring"),
    (r"\bjdbc\b", "JDBC"),
    (r"\bhibernate\b", "Hibernate"),
    (r"\bc\+\+\b", "C++"),
    (r"\b(golang|go)\b", "Go"),
    (r"\brust\b", "Rust"),
    (r"\bjavascript\b", "JavaScript"),
    (r"\btypescript\b", "TypeScript"),
    (r"\breact(\.js)?\b", "React"),
    (r"\bvue(\.js)?\b", "Vue"),
    (r"\bangular\b", "Angular"),
    (r"\bnext\.js\b", "Next.js"),
    (r"\bnode(\.js)?\b", "Node.js"),
    (r"\bhtml5?\b", "HTML"),
    (r"\bcss3?\b", "CSS"),
    (r"\btailwind(css)?\b", "TailwindCSS"),
    (r"\b(rest\s*apis?|restful\s*apis?|rest\s*web\s*services?)\b", "REST APIs"),
    (r"\bgraphql\b", "GraphQL"),
    (r"\bgrpc\b", "gRPC"),
    (r"\bmicroservices\b", "Microservices"),
    (r"\bci\s*/\s*cd\b", "CI/CD"),
    (r"\bunit\s*tests?\b", "Unit Testing"),
    (r"\b(oop|object\s*oriented\s*programming)\b", "OOP"),
    (r"\bdata\s*structures\b", "Data Structures"),
    (r"\balgorithms\b", "Algorithms"),
    (r"\bmachine\s*learning\b", "Machine Learning"),
    (r"\bdeep\s*learning\b", "Deep Learning"),
    (r"\b(scikit[\s_-]*learn|sklearn)\b", "Scikit-Learn"),
    (r"\bpandas\b", "Pandas"),
    (r"\bnumpy\b", "NumPy"),
    (r"\bpytorch\b", "PyTorch"),
    (r"\btensorflow\b", "TensorFlow"),
    (r"\bnlp\b|\bnatural\s*language\s*processing\b", "NLP"),
    (r"\bcomputer\s*vision\b", "Computer Vision"),
    (r"\bdata\s*analysis\b", "Data Analysis"),
    (r"\b(eda|exploratory\s*data\s*analysis)\b", "EDA"),
    (r"\bstatistics\b|\bstatistical\s*analysis\b", "Statistics"),
    (r"\bdata\s*visualization\b", "Data Visualization"),
    (r"\bmatplotlib\b", "Matplotlib"),
    (r"\bseaborn\b", "Seaborn"),
    (r"\bregression\b", "Regression"),
    (r"\bclassification\b", "Classification"),
    (r"\bdecision\s*trees\b", "Decision Trees"),
    (r"\bmodel\s*evaluation\b", "Model Evaluation"),
        (r"\bsupervised\s*learning\b", "Supervised Learning"),
    (r"\b(microsoft\s*excel|ms\s*excel|excel)\b", "Microsoft Excel"),
    (r"\b(microsoft\s*word|ms\s*word)\b", "Microsoft Word"),
    (r"\b(microsoft\s*office|ms\s*office|powerpoint)\b", "Microsoft Office"),
    (r"\b(human\s*resources|hr\s*administration|hr\s*operations)\b", "Human Resources"),
    (r"\b(employee\s*relations|employee\s*onboarding|onboarding)\b", "Employee Relations"),
    (r"\b(recruitment|talent\s*acquisition)\b", "Recruitment"),
    (r"\b(employment\s*law|labor\s*law|compliance)\b", "Employment Law"),
    (r"\b(communication\s*skills|written\s*communication|verbal\s*communication)\b", "Communication"),
    (r"\b(confidentiality|confidential\s*information)\b", "Confidentiality"),
    (r"\b(teamwork|collaboration)\b", "Teamwork"),
]

ACTION_VERBS = {
    "built", "developed", "implemented", "created", "designed", "tested",
    "used", "trained", "analyzed", "managed", "deployed", "integrated",
    "maintained", "engineered", "architected", "configured", "optimized",
    "queried", "wrote", "collaborated", "contributed", "debugged", "evaluated",
        "handled", "processed", "executed", "visualized", "modelled", "modeled",
    "coordinated", "maintained", "assisted", "prepared", "supported", "studied",
    "organized", "organised", "responded", "monitored", "collected", "tracked",
}

SECTION_HEADER_MAP = {
    "skills": ["skills", "technical skills", "core skills", "core competencies", "key skills", "technologies", "tech stack", "tools and technologies"],
    "experience": ["experience", "work experience", "professional experience", "employment history", "internship", "internships"],
    "projects": ["projects", "academic projects", "personal projects", "key projects", "project experience"],
    "education": ["education", "academic background", "qualifications", "academics"],
    "summary": ["summary", "professional summary", "about me", "profile", "objective"],
}


def extract_text_from_bytes(data: bytes, filename: str, mime_type: str = "") -> str:
    """Extracts clean text from PDF or DOCX file bytes."""
    lower_fn = filename.lower()
    lower_mime = mime_type.lower()

    if lower_fn.endswith(".docx") or "word" in lower_mime:
        return _extract_docx(data)
    elif lower_fn.endswith(".pdf") or "pdf" in lower_mime:
        return _extract_pdf(data)
    else:
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data.decode("latin-1", errors="ignore")


def _extract_docx(data: bytes) -> str:
    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            if "word/document.xml" not in archive.namelist():
                return ""
            root = ElementTree.fromstring(archive.read("word/document.xml"))
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
            paragraphs = []
            for p in root.findall(".//w:p", ns):
                text = "".join(t.text or "" for t in p.findall(".//w:t", ns))
                if text.strip():
                    paragraphs.append(text.strip())
            return "\n".join(paragraphs)
    except Exception:
        return ""


def _extract_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
        full_text = "\n\n".join(p for p in pages if p.strip())
        if full_text.strip():
            return full_text.replace("\x00", "")
    except Exception:
        pass

    raw = data.decode("latin-1", errors="ignore")
    matches = re.findall(r"BT\s*(.*?)\s*ET", raw, flags=re.DOTALL)
    blocks: list[str] = []
    for m in matches:
        clean = re.sub(r"\\\((.*?)\\\)", r"\1", m)
        clean = re.sub(r"\\[0-9]+", "", clean).replace("\\n", " ").strip()
        if clean:
            blocks.append(clean)
    if not blocks:
        try:
            decoded = data.decode("utf-8")
            if decoded.strip() and not decoded.startswith("%PDF"):
                return decoded.replace("\x00", "")
        except Exception:
            pass
        return ""
    return "\n".join(blocks).replace("\x00", "")


def parse_resume_sections(text: str) -> list[tuple[str, str]]:
    """
    Splits resume text into (line_text, section_name) pairs.
    """
    lines = text.splitlines()
    result: list[tuple[str, str]] = []
    current_section = "general"

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        normalized_header = re.sub(r"[^a-z0-9 ]+", " ", line.lower()).strip()
        matched_section = None
        for section, keywords in SECTION_HEADER_MAP.items():
            if normalized_header in keywords:
                matched_section = section
                break
        if matched_section:
            current_section = matched_section
            continue

        result.append((line, current_section))
    return result


def extract_skills_with_evidence(text: str) -> list[dict[str, Any]]:
    """
    Extracts technical skills and categorizes each as:
      - 'demonstrated': Supported by work experience / projects and/or active verbs.
      - 'listed': Stated only in a skills list or header without practical context.
    """
    parsed_lines = parse_resume_sections(text)
    found_skills: list[dict[str, Any]] = []

    for pattern_str, canonical_name in CANONICAL_SKILL_PATTERNS:
        compiled_pattern = re.compile(pattern_str, re.IGNORECASE)
        matching_entries: list[tuple[str, str]] = []

        for line, section in parsed_lines:
            if compiled_pattern.search(line):
                matching_entries.append((line, section))

        if not matching_entries:
            continue

        # Check evidence type: demonstrated vs listed
        is_demonstrated = False
        evidence_quotes: list[str] = []

        for line, section in matching_entries:
            evidence_quotes.append(line)
            tokens = set(re.findall(r"[a-z]+", line.lower()))
            has_action = bool(tokens & ACTION_VERBS)
            if section in ("experience", "projects") or has_action:
                is_demonstrated = True

        evidence_status = "demonstrated" if is_demonstrated else "listed"
        confidence = 0.95 if is_demonstrated else 0.85

        found_skills.append({
            "name": canonical_name,
            "status": evidence_status,
            "evidence": evidence_quotes[:4],
            "confidence": confidence,
            "weight": 1.0 if is_demonstrated else 0.5,
        })

    return found_skills


def extract_candidate_profile_json(text: str) -> dict[str, Any]:
    """Extracts structured candidate profile for matching."""
    skills = extract_skills_with_evidence(text)
    demonstrated = [s["name"] for s in skills if s["status"] == "demonstrated"]
    listed = [s["name"] for s in skills if s["status"] == "listed"]

    exp_snippets = []
    for line in text.splitlines():
        line_clean = line.strip()
        if any(kw in line_clean.lower() for kw in ["engineer", "developer", "intern", "lead", "analyst", "manager", "architect"]):
            if len(line_clean) < 100 and not line_clean.lower().startswith("profile"):
                exp_snippets.append({"job_title": line_clean[:80], "company": ""})
                if len(exp_snippets) >= 4:
                    break

    return {
        "full_name": None,  # Sanitized for matching privacy
        "email": None,
        "phone": None,
        "location": None,
        "skills": skills,
        "demonstrated_skills": demonstrated,
        "listed_skills": listed,
        "experience": exp_snippets,
        "skills_count": len(skills),
        "raw_text_length": len(text),
    }


def extract_job_profile_json(text: str, filename: str = "") -> dict[str, Any]:
    """Extracts structured job requirements and details for matching."""
    skills = extract_skills_with_evidence(text)
    skill_names = [s["name"] for s in skills]

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    title = ""
    for line in lines[:10]:
        m = re.search(r"(?i)^\s*(?:Job\s+Title|Title|Role)\s*[:\-]?\s*(.+)$", line)
        if m:
            title = m.group(1).strip()
            break
    if not title:
        for line in lines[:5]:
            if any(role_term in line.lower() for role_term in [
                "developer", "engineer", "analyst", "intern", "internship",
                "architect", "consultant", "scientist", "manager", "assistant",
            ]):
                title = line[:80]
                break

    if not title:
        clean_fn = re.sub(r"^[0-9]+_", "", filename)
        clean_fn = re.sub(r"\.(pdf|docx)$", "", clean_fn, flags=re.IGNORECASE)
        title = clean_fn.replace("_", " ").strip()

    return {
        "job_title": title or "Software Professional",
        "required_skills": skill_names,
        "skills_evidence": skills,
        "overview": "\n".join(lines[:6]) if lines else "",
        "requirements_count": len(skill_names),
        "raw_text_length": len(text),
    }
