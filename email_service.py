# email_service.py — Resend integration (secrets kutoka .env)
import os
import random
from datetime import datetime, timedelta
import resend

resend.api_key = os.getenv("RESEND_API_KEY", "")
SENDER = os.getenv("SENDER_EMAIL", "onboarding@resend.dev")


def generate_code():
    return f"{random.randint(100000, 999999)}"


def send_verification_email(to_email: str, full_name: str, code: str):
    if not resend.api_key:
        return False, "RESEND_API_KEY haipo. Weka kwenye .env au Render Environment."

    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;padding:30px;background:#f5f7fa;">
      <div style="background:#0B1F33;color:white;padding:24px;border-radius:12px 12px 0 0;text-align:center;">
        <h1 style="margin:0;font-size:22px;">IT Level 4 Connect</h1>
        <p style="margin:6px 0 0;color:#cbd5e1;font-size:14px;">Email Verification</p>
      </div>
      <div style="background:white;padding:30px;border-radius:0 0 12px 12px;">
        <p style="font-size:16px;color:#0f172a;">Habari <strong>{full_name}</strong>,</p>
        <p style="color:#475569;">Asante kwa kujisajili. Tumia code hii kuthibitisha akaunti yako:</p>
        <div style="background:#F47721;color:white;font-size:36px;font-weight:800;text-align:center;padding:20px;border-radius:10px;letter-spacing:8px;margin:24px 0;">
          {code}
        </div>
        <p style="color:#475569;font-size:14px;">Code hii itaisha muda baada ya <strong>dakika 15</strong>.</p>
        <p style="color:#94a3b8;font-size:12px;margin-top:30px;">Kama hukujisajili, puuza email hii.</p>
      </div>
    </div>
    """

    try:
        resend.Emails.send({
            "from": SENDER,
            "to": to_email,
            "subject": "IT Level 4 Connect — Code yako ya uthibitisho",
            "html": html,
        })
        return True, None
    except Exception as e:
        return False, str(e)


def make_expiry(minutes=15):
    return (datetime.utcnow() + timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")