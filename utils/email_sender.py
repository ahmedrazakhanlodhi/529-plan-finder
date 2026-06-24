# utils/email_sender.py — The 529 Network
import smtplib, logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import date
logger = logging.getLogger(__name__)

def send_results_email(to_address, pdf_bytes, lang="en"):
    try:
        import streamlit as st
        s = st.secrets
        if "SENDGRID_API_KEY" in s:
            return _sendgrid(to_address, pdf_bytes, lang, s["SENDGRID_API_KEY"])
        if all(k in s for k in ("SMTP_HOST","SMTP_USER","SMTP_PASSWORD")):
            return _smtp(to_address, pdf_bytes, lang, s)
        logger.warning("No email credentials configured in secrets.toml")
        return False
    except Exception as e:
        logger.error(f"Email error: {e}")
        return False

def _html_body(lang):
    if lang == "es":
        return ("Tus Resultados del Buscador de Planes 529",
                "<html><body><h2>Tus resultados estan adjuntos.</h2><p>Datos compilados por The 529 Network.</p></body></html>")
    return ("Your 529 Plan Finder Results — The 529 Network",
            "<html><body><h2>Your results are attached.</h2><p>Data compiled by The 529 Network.</p></body></html>")

def _smtp(to_address, pdf_bytes, lang, s):
    subj, html = _html_body(lang)
    msg = MIMEMultipart("mixed")
    msg["Subject"] = subj
    msg["From"] = s.get("SMTP_FROM", s["SMTP_USER"])
    msg["To"] = to_address
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(html, "html"))
    msg.attach(alt)
    att = MIMEBase("application", "pdf")
    att.set_payload(pdf_bytes)
    encoders.encode_base64(att)
    att.add_header("Content-Disposition", "attachment",
                   filename=f"529_plan_results_{date.today().isoformat()}.pdf")
    msg.attach(att)
    with smtplib.SMTP(s["SMTP_HOST"], int(s.get("SMTP_PORT", 587))) as srv:
        srv.ehlo(); srv.starttls()
        srv.login(s["SMTP_USER"], s["SMTP_PASSWORD"])
        srv.sendmail(s["SMTP_USER"], to_address, msg.as_string())
    return True

def _sendgrid(to_address, pdf_bytes, lang, api_key):
    try:
        import sendgrid, base64
        from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
        subj, html = _html_body(lang)
        m = Mail(from_email="noreply@529network.org", to_emails=to_address, subject=subj, html_content=html)
        a = Attachment()
        a.file_content = FileContent(base64.b64encode(pdf_bytes).decode())
        a.file_type = FileType("application/pdf")
        a.file_name = FileName(f"529_plan_results_{date.today().isoformat()}.pdf")
        a.disposition = Disposition("attachment")
        m.attachment = a
        r = sendgrid.SendGridAPIClient(api_key=api_key).send(m)
        return r.status_code in (200, 202)
    except ImportError:
        return False
    except Exception as e:
        logger.error(f"SendGrid error: {e}")
        return False
