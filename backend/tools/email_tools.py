import base64
import logging
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
import requests
from sqlalchemy.orm import Session
from backend.config import settings
from backend.models import OAuthToken

logger = logging.getLogger(__name__)


def _refresh_gmail_token(refresh_token: str) -> dict:
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": settings.GMAIL_CLIENT_ID,
            "client_secret": settings.GMAIL_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
    )
    response.raise_for_status()
    return response.json()


def _refresh_outlook_token(refresh_token: str) -> dict:
    import msal
    app = msal.ConfidentialClientApplication(
        settings.OUTLOOK_CLIENT_ID,
        authority="https://login.microsoftonline.com/common",
        client_credential=settings.OUTLOOK_CLIENT_SECRET,
    )
    result = app.acquire_token_by_refresh_token(refresh_token, scopes=["Mail.Send"])
    if "error" in result:
        raise ValueError(f"Token refresh failed: {result['error_description']}")
    return result


def get_valid_token(provider: str, db: Session) -> str:
    """Return a valid access token, refreshing if expired. Persists updated token to DB."""
    record = db.query(OAuthToken).filter(OAuthToken.provider == provider).first()
    if not record:
        raise ValueError(f"No OAuth token found for provider '{provider}'. Connect via /auth/email/connect.")

    if datetime.utcnow() < record.expires_at:
        return record.access_token

    # Token expired — refresh
    logger.info(f"Refreshing {provider} OAuth token...")
    if provider == "gmail":
        refreshed = _refresh_gmail_token(record.refresh_token)
    else:
        refreshed = _refresh_outlook_token(record.refresh_token)

    record.access_token = refreshed["access_token"]
    record.expires_at = datetime.utcnow() + timedelta(seconds=refreshed.get("expires_in", 3600))
    db.commit()
    return record.access_token


def send_email_gmail(access_token: str, to: str, subject: str, body: str, attachment_path: str = "") -> bool:
    """Send an email via Gmail API."""
    msg = MIMEMultipart()
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    if attachment_path and Path(attachment_path).exists():
        with open(attachment_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={Path(attachment_path).name}")
        msg.attach(part)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    response = requests.post(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json={"raw": raw},
    )
    response.raise_for_status()
    return True


def send_email_outlook(access_token: str, to: str, subject: str, body: str, attachment_path: str = "") -> bool:
    """Send an email via Microsoft Graph API."""
    attachments = []
    if attachment_path and Path(attachment_path).exists():
        with open(attachment_path, "rb") as f:
            content = base64.b64encode(f.read()).decode()
        attachments.append({
            "@odata.type": "#microsoft.graph.fileAttachment",
            "name": Path(attachment_path).name,
            "contentBytes": content,
        })

    payload = {
        "message": {
            "subject": subject,
            "body": {"contentType": "Text", "content": body},
            "toRecipients": [{"emailAddress": {"address": to}}],
            "attachments": attachments,
        }
    }
    response = requests.post(
        "https://graph.microsoft.com/v1.0/me/sendMail",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        json=payload,
    )
    response.raise_for_status()
    return True


def send_email(to: str, subject: str, body: str, attachment_path: str, db: Session) -> bool:
    """Dispatch email via configured provider. Reads and refreshes token from DB."""
    access_token = get_valid_token(settings.EMAIL_PROVIDER, db)
    if settings.EMAIL_PROVIDER == "gmail":
        return send_email_gmail(access_token, to, subject, body, attachment_path)
    return send_email_outlook(access_token, to, subject, body, attachment_path)
