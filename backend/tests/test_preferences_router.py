def test_get_preferences_empty(client):
    response = client.get("/preferences")
    assert response.status_code == 200
    assert response.json() is None


def test_post_preferences(client):
    payload = {
        "job_titles": ["Python Engineer", "Backend Engineer"],
        "location": "Remote",
        "remote_hybrid": "remote",
        "experience_level": "senior",
        "domain": "backend",
        "company_size": ["startup"],
    }
    response = client.post("/preferences", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["location"] == "Remote"
    assert "poll_interval_hrs" not in data
    assert data["job_titles"] == ["Python Engineer", "Backend Engineer"]


def test_post_preferences_updates_existing(client):
    client.post("/preferences", json={"job_titles": ["Python Eng"], "location": "NYC", "remote_hybrid": "hybrid"})
    client.post("/preferences", json={"job_titles": ["Data Eng"], "location": "Remote", "remote_hybrid": "remote"})
    response = client.get("/preferences")
    assert response.status_code == 200
    assert response.json()["location"] == "Remote"
    # Exactly one record
    assert response.json()["job_titles"] == ["Data Eng"]
