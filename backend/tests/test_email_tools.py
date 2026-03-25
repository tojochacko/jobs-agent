# backend/tests/test_email_tools.py
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from backend.models import OAuthToken
from backend.tools.email_tools import get_valid_token


@pytest.fixture
def db_with_token(db_engine):
    """DB session with a valid Gmail token."""
    with Session(db_engine) as session:
        token = OAuthToken(
            provider="gmail",
            access_token="valid_access",
            refresh_token="valid_refresh",
            expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1),
        )
        session.add(token)
        session.commit()
        yield session


def test_get_valid_token_returns_access_token(db_with_token):
    token = get_valid_token("gmail", db_with_token)
    assert token == "valid_access"


def test_get_valid_token_refreshes_expired_token(db_engine):
    """Expired token triggers refresh and DB update."""
    with Session(db_engine) as session:
        token = OAuthToken(
            provider="gmail",
            access_token="old_access",
            refresh_token="valid_refresh",
            expires_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1),  # expired
        )
        session.add(token)
        session.commit()

    with patch("backend.tools.email_tools._refresh_gmail_token",
               return_value={"access_token": "new_access", "expires_in": 3600}):
        with Session(db_engine) as session:
            token = get_valid_token("gmail", session)
            assert token == "new_access"


def test_get_valid_token_raises_when_no_token(db_engine):
    with Session(db_engine) as session:
        with pytest.raises(ValueError, match="No OAuth token"):
            get_valid_token("gmail", session)
