# backend/tests/test_auth_router.py
from unittest.mock import patch
from backend.models import OAuthToken


def test_connect_gmail_returns_auth_url(client):
    with patch("backend.routers.auth.build_gmail_auth_url", return_value="https://accounts.google.com/o/oauth2/auth?..."):
        response = client.post("/auth/email/connect")
    assert response.status_code == 200
    assert "auth_url" in response.json()


def test_callback_stores_token(client, db_session):
    mock_token = {
        "access_token": "acc_123",
        "refresh_token": "ref_456",
        "expires_in": 3600,
    }
    with patch("backend.routers.auth.exchange_gmail_code", return_value=mock_token):
        response = client.get("/auth/email/callback?code=authcode123")
    assert response.status_code == 200
    token = db_session.query(OAuthToken).filter_by(provider="gmail").first()
    assert token is not None
    assert token.access_token == "acc_123"
