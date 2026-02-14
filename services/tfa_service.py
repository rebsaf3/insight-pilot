"""Two-Factor Authentication service — TOTP, email codes, backup codes."""

import hashlib
import secrets
from typing import Optional

import pyotp
import qrcode
import io
import base64

from config.settings import ENCRYPTION_KEY, APP_TITLE, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM_NAME, SMTP_FROM_EMAIL
from db import queries


# ---------------------------------------------------------------------------
# Encryption helpers for TOTP secrets
# ---------------------------------------------------------------------------

def _encrypt_secret(secret: str) -> str:
    """Encrypt a TOTP secret for storage."""
    if not ENCRYPTION_KEY:
        return secret  # fallback: store plaintext in dev
    from cryptography.fernet import Fernet
    f = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)
    return f.encrypt(secret.encode()).decode()


def _decrypt_secret(encrypted: str) -> str:
    """Decrypt a stored TOTP secret."""
    if not ENCRYPTION_KEY:
        return encrypted
    from cryptography.fernet import Fernet
    f = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)
    return f.decrypt(encrypted.encode()).decode()


# ---------------------------------------------------------------------------
# TOTP Setup
# ---------------------------------------------------------------------------

def generate_totp_secret() -> str:
    """Generate a new TOTP secret."""
    return pyotp.random_base32()


def get_totp_qr_code(secret: str, email: str) -> str:
    """Generate a QR code as a base64-encoded PNG for the TOTP setup."""
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=email, issuer_name=APP_TITLE)
    img = qrcode.make(uri)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def enable_totp(user_id: str, secret: str, verification_code: str) -> tuple[bool, str]:
    """Enable TOTP for a user after verifying their first code.
    Returns (success, error_message)."""
    totp = pyotp.TOTP(secret)
    if not totp.verify(verification_code, valid_window=1):
        return False, "Invalid verification code. Please try again."

    encrypted = _encrypt_secret(secret)
    queries.update_user(user_id, totp_secret=encrypted, totp_enabled=1)

    # Generate backup codes
    backup_codes = generate_backup_codes(user_id)

    return True, ""


def disable_totp(user_id: str) -> None:
    """Disable TOTP for a user."""
    queries.update_user(user_id, totp_secret=None, totp_enabled=0)


def verify_totp(user_id: str, code: str) -> bool:
    """Verify a TOTP code for a user."""
    user = queries.get_user_by_id(user_id)
    if not user or not user.totp_enabled or not user.totp_secret:
        return False
    secret = _decrypt_secret(user.totp_secret)
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


# ---------------------------------------------------------------------------
# Email 2FA Codes
# ---------------------------------------------------------------------------

def send_email_2fa_code(user_id: str) -> tuple[bool, str]:
    """Generate and send a 6-digit code via email."""
    # Rate limit: max 3 codes per 15 minutes
    recent_count = queries.count_recent_verification_codes(user_id, "2fa", 15)
    if recent_count >= 3:
        return False, "Too many code requests. Please wait a few minutes."

    user = queries.get_user_by_id(user_id)
    if not user:
        return False, "User not found."

    code = f"{secrets.randbelow(1000000):06d}"

    from datetime import datetime, timedelta, timezone
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()

    queries.create_verification_code(user_id, code, "2fa", expires_at)

    # Send email
    success = _send_email(
        to_email=user.email,
        subject=f"{APP_TITLE} — Your verification code",
        body=f"Your verification code is: {code}\n\nThis code expires in 10 minutes.",
    )

    if not success:
        return False, "Failed to send email. Please try again."

    return True, ""


def verify_email_2fa_code(user_id: str, code: str) -> bool:
    """Verify an email 2FA code."""
    result = queries.get_valid_verification_code(user_id, code, "2fa")
    if not result:
        return False
    queries.mark_verification_code_used(result["id"])
    return True


# ---------------------------------------------------------------------------
# Backup Codes
# ---------------------------------------------------------------------------

def generate_backup_codes(user_id: str, count: int = 10) -> list[str]:
    """Generate backup codes for a user. Returns plaintext codes (shown once to user).
    Stores hashed versions in DB."""
    codes = [secrets.token_hex(4).upper() for _ in range(count)]  # e.g. "A1B2C3D4"
    hashes = [hashlib.sha256(c.encode()).hexdigest() for c in codes]
    queries.create_backup_codes(user_id, hashes)
    return codes


def verify_backup_code(user_id: str, code: str) -> bool:
    """Verify and consume a backup code."""
    code_hash = hashlib.sha256(code.strip().upper().encode()).hexdigest()
    result = queries.get_unused_backup_code(user_id, code_hash)
    if not result:
        return False
    queries.mark_backup_code_used(result["id"])
    return True


# ---------------------------------------------------------------------------
# Email sending helper
# ---------------------------------------------------------------------------

def _send_email(to_email: str, subject: str, body: str) -> bool:
    """Send an email via SMTP. Returns True on success."""
    if not SMTP_USER or not SMTP_PASSWORD:
        # In development, print to console instead
        print(f"[EMAIL] To: {to_email} | Subject: {subject}\n{body}")
        return True

    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart()
        msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False
