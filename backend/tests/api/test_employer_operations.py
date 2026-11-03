import io

from fastapi.testclient import TestClient


def test_employer_profile_retrieval(client: TestClient, create_employer):
    emp = create_employer(name="John Smith", company="InclusivTech")
    response = client.get("/api/v1/employers/me", headers=emp["headers"])

    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "John Smith"
    assert data["company_name"] == "InclusivTech"
    assert data["verification_status"] == "PENDING"
    assert data["user_id"] == str(emp["user"].id)


def test_employer_profile_update(client: TestClient, create_employer):
    emp = create_employer(company="Old Corp")
    response = client.patch(
        "/api/v1/employers/me",
        headers=emp["headers"],
        json={"company_name": "New Inclusive Corp", "website": "https://newcorp.org"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["company_name"] == "New Inclusive Corp"
    assert data["website"] == "https://newcorp.org"
    # Verification status remains PENDING - cannot self-verify
    assert data["verification_status"] == "PENDING"


def test_job_document_upload_success_pdf(client: TestClient, create_employer, sample_pdf_bytes):
    emp = create_employer()
    files = {"file": ("senior_engineer_jd.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")}
    response = client.post(
        "/api/v1/employers/me/job-documents", headers=emp["headers"], files=files
    )

    assert response.status_code == 201
    data = response.json()
    assert data["original_filename"] == "senior_engineer_jd.pdf"
    assert data["mime_type"] == "application/pdf"
    assert data["status"] in ("UPLOADED", "PROCESSED")
    assert data["download_url"] is not None


def test_job_document_upload_success_docx(client: TestClient, create_employer, sample_docx_bytes):
    emp = create_employer()
    files = {
        "file": (
            "accessibility_analyst_jd.docx",
            io.BytesIO(sample_docx_bytes),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }
    response = client.post(
        "/api/v1/employers/me/job-documents", headers=emp["headers"], files=files
    )

    assert response.status_code == 201
    data = response.json()
    assert data["original_filename"] == "accessibility_analyst_jd.docx"


def test_job_document_upload_invalid_extension(client: TestClient, create_employer):
    emp = create_employer()
    files = {"file": ("job_description.txt", io.BytesIO(b"Job info"), "text/plain")}
    response = client.post(
        "/api/v1/employers/me/job-documents", headers=emp["headers"], files=files
    )

    assert response.status_code == 400
    assert "Unsupported file extension" in response.json()["detail"]


def test_job_document_list_and_get(client: TestClient, create_employer, sample_pdf_bytes):
    emp = create_employer()
    files = {"file": ("backend_dev.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")}
    up_res = client.post("/api/v1/employers/me/job-documents", headers=emp["headers"], files=files)
    doc_id = up_res.json()["id"]

    # List documents
    list_res = client.get("/api/v1/employers/me/job-documents", headers=emp["headers"])
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1
    assert any(d["id"] == doc_id for d in list_res.json())

    # Get specific document
    get_res = client.get(f"/api/v1/employers/me/job-documents/{doc_id}", headers=emp["headers"])
    assert get_res.status_code == 200
    assert get_res.json()["id"] == doc_id


def test_job_document_direct_download(client: TestClient, create_employer, sample_pdf_bytes):
    emp = create_employer()
    files = {"file": ("download_jd.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")}
    up_res = client.post("/api/v1/employers/me/job-documents", headers=emp["headers"], files=files)
    doc_id = up_res.json()["id"]

    dl_res = client.get(
        f"/api/v1/employers/me/job-documents/{doc_id}/download", headers=emp["headers"]
    )
    assert dl_res.status_code == 200
    assert dl_res.content == sample_pdf_bytes


def test_job_document_deletion(client: TestClient, create_employer, sample_pdf_bytes):
    emp = create_employer()
    files = {"file": ("delete_jd.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")}
    up_res = client.post("/api/v1/employers/me/job-documents", headers=emp["headers"], files=files)
    doc_id = up_res.json()["id"]

    del_res = client.delete(f"/api/v1/employers/me/job-documents/{doc_id}", headers=emp["headers"])
    assert del_res.status_code == 200

    get_res = client.get(f"/api/v1/employers/me/job-documents/{doc_id}", headers=emp["headers"])
    assert get_res.status_code == 404


def test_employer_cannot_access_other_employers_documents(
    client: TestClient, create_employer, sample_pdf_bytes
):
    emp_a = create_employer(company="Company A")
    emp_b = create_employer(company="Company B")

    # Employer A uploads a JD
    files = {"file": ("confidential_jd.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")}
    up_res = client.post(
        "/api/v1/employers/me/job-documents", headers=emp_a["headers"], files=files
    )
    doc_id = up_res.json()["id"]

    # Employer B cannot get document A
    get_res = client.get(f"/api/v1/employers/me/job-documents/{doc_id}", headers=emp_b["headers"])
    assert get_res.status_code == 404

    # Employer B cannot download document A
    dl_res = client.get(
        f"/api/v1/employers/me/job-documents/{doc_id}/download", headers=emp_b["headers"]
    )
    assert dl_res.status_code == 404

    # Employer B cannot delete document A
    del_res = client.delete(
        f"/api/v1/employers/me/job-documents/{doc_id}", headers=emp_b["headers"]
    )
    assert del_res.status_code == 404


def test_employer_accessibility_capabilities_crud(client: TestClient, create_employer):
    emp = create_employer()

    # 1. Add capability (AVAILABLE)
    add_res = client.post(
        "/api/v1/employers/me/accessibility",
        headers=emp["headers"],
        json={
            "category": "VISUAL",
            "capability": "Screen-reader-compatible systems",
            "status": "AVAILABLE",
            "details": "Internal software tested with NVDA and JAWS",
        },
    )
    assert add_res.status_code == 201
    cap = add_res.json()
    cap_id = cap["id"]
    assert cap["category"] == "VISUAL"
    assert cap["capability"] == "Screen-reader-compatible systems"
    assert cap["status"] == "AVAILABLE"

    # 2. Add second capability (ON_REQUEST)
    add_res2 = client.post(
        "/api/v1/employers/me/accessibility",
        headers=emp["headers"],
        json={
            "category": "AUDITORY",
            "capability": "Sign-language interpreter",
            "status": "ON_REQUEST",
            "details": "Arranged with 48 hours notice",
        },
    )
    assert add_res2.status_code == 201
    assert add_res2.json()["status"] == "ON_REQUEST"

    # 3. List capabilities
    list_res = client.get("/api/v1/employers/me/accessibility", headers=emp["headers"])
    assert list_res.status_code == 200
    assert len(list_res.json()) == 2

    # 4. Update capability status to UNAVAILABLE
    patch_res = client.patch(
        f"/api/v1/employers/me/accessibility/{cap_id}",
        headers=emp["headers"],
        json={"status": "UNAVAILABLE", "details": "Currently under maintenance"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "UNAVAILABLE"

    # 5. Delete capability
    del_res = client.delete(f"/api/v1/employers/me/accessibility/{cap_id}", headers=emp["headers"])
    assert del_res.status_code == 200

    # 6. Verify list decreased
    list_res2 = client.get("/api/v1/employers/me/accessibility", headers=emp["headers"])
    assert len(list_res2.json()) == 1


def test_employer_cannot_modify_other_employers_capabilities(client: TestClient, create_employer):
    emp_a = create_employer()
    emp_b = create_employer()

    add_res = client.post(
        "/api/v1/employers/me/accessibility",
        headers=emp_a["headers"],
        json={
            "category": "MOBILITY",
            "capability": "Wheelchair-accessible office",
            "status": "AVAILABLE",
        },
    )
    cap_id = add_res.json()["id"]

    # Employer B cannot modify Employer A's capability
    patch_res = client.patch(
        f"/api/v1/employers/me/accessibility/{cap_id}",
        headers=emp_b["headers"],
        json={"status": "UNAVAILABLE"},
    )
    assert patch_res.status_code == 404

    # Employer B cannot delete Employer A's capability
    del_res = client.delete(
        f"/api/v1/employers/me/accessibility/{cap_id}",
        headers=emp_b["headers"],
    )
    assert del_res.status_code == 404
