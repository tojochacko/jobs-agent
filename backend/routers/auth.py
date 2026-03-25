from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from backend.config import settings
from backend.database import get_db
from backend.models import OAuthToken
import requests

router = APIRouter()

GMAIL_SCOPES = "https://www.googleapis.com/auth/gmail.send"


def build_gmail_auth_url() -> str:
    params = (
        f"client_id={settings.GMAIL_CLIENT_ID}"
        f"&redirect_uri={settings.OAUTH_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={GMAIL_SCOPES}"
        f"&access_type=offline"
        f"&prompt=consent"
    )
    return f"https://accounts.google.com/o/oauth2/auth?{params}"


def build_outlook_auth_url() -> str:
    params = (
        f"client_id={settings.OUTLOOK_CLIENT_ID}"
        f"&redirect_uri={settings.OAUTH_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=Mail.Send+offline_access"
    )
    return f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?{params}"


def exchange_gmail_code(code: str) -> dict:
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": settings.GMAIL_CLIENT_ID,
            "client_secret": settings.GMAIL_CLIENT_SECRET,
            "redirect_uri": settings.OAUTH_REDIRECT_URI,
            "grant_type": "authorization_code",
        },
    )
    response.raise_for_status()
    return response.json()


def exchange_outlook_code(code: str) -> dict:
    import msal
    app = msal.ConfidentialClientApplication(
        settings.OUTLOOK_CLIENT_ID,
        authority="https://login.microsoftonline.com/common",
        client_credential=settings.OUTLOOK_CLIENT_SECRET,
    )
    result = app.acquire_token_by_authorization_code(
        code, scopes=["Mail.Send"], redirect_uri=settings.OAUTH_REDIRECT_URI
    )
    if "error" in result:
        raise ValueError(result.get("error_description", "OAuth exchange failed"))
    return result


@router.post("/auth/email/connect")
def connect_email():
    """Return the OAuth provider authorization URL for the user to open."""
    if settings.EMAIL_PROVIDER == "gmail":
        url = build_gmail_auth_url()
    else:
        url = build_outlook_auth_url()
    return {"auth_url": url}


@router.get("/auth/email/callback")
def email_callback(code: str, db: Session = Depends(get_db)):
    """Exchange authorization code for tokens and persist to DB."""
    if settings.EMAIL_PROVIDER == "gmail":
        token_data = exchange_gmail_code(code)
    else:
        token_data = exchange_outlook_code(code)

    expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=token_data.get("expires_in", 3600))
    record = db.query(OAuthToken).filter(OAuthToken.provider == settings.EMAIL_PROVIDER).first()
    if not record:
        record = OAuthToken(provider=settings.EMAIL_PROVIDER)
        db.add(record)
    record.access_token = token_data["access_token"]
    record.refresh_token = token_data.get("refresh_token", "")
    record.expires_at = expires_at
    db.commit()
    return {"status": "connected", "provider": settings.EMAIL_PROVIDER}
