import io


def test_upload_resume(client, tmp_path, monkeypatch):
    monkeypatch.setattr("backend.routers.resume.settings.UPLOAD_DIR", str(tmp_path))
    response = client.post(
        "/resume",
        files={"file": ("my_resume.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "my_resume.pdf"
    assert "filepath" in data


def test_get_resume_returns_latest(client, tmp_path, monkeypatch):
    monkeypatch.setattr("backend.routers.resume.settings.UPLOAD_DIR", str(tmp_path))
    for name in ["v1.pdf", "v2.pdf"]:
        client.post("/resume", files={"file": (name, io.BytesIO(b"content"), "application/pdf")})
    response = client.get("/resume")
    assert response.status_code == 200
    assert response.json()["filename"] == "v2.pdf"


def test_get_resume_empty(client):
    response = client.get("/resume")
    assert response.status_code == 200
    assert response.json() is None
