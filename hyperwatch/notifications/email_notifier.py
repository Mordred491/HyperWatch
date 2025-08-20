import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import yaml
import logging
import asyncio

CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../config/notification.yaml"))
logger = logging.getLogger(__name__)

def load_config():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)

config = load_config().get("email", {})

def _send_email(subject: str, body: str) -> bool:
    if not config.get("enabled", False):
        logger.info("🚫 Email notifications disabled in config.")
        return False

    smtp_server = config.get("smtp_server")
    smtp_port = config.get("smtp_port")
    username = config.get("username")
    password = config.get("password")
    from_addr = config.get("from_addr")
    to_addrs = config.get("to_addrs")

    if not all([smtp_server, smtp_port, username, password, from_addr, to_addrs]):
        logger.warning("⚠️ Email config incomplete.")
        return False

    msg = MIMEMultipart()
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs) if isinstance(to_addrs, list) else to_addrs
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(username, password)
            server.sendmail(from_addr, to_addrs, msg.as_string())

        logger.info("✅ Email sent successfully.")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send email: {e}")
        return False

async def send_email(message: str, event: dict) -> bool:
    subject = "🔔 Hyperwatch Alert"
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _send_email, subject, message)
