import os
import yaml
import requests
import logging
import asyncio

CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../config/notification.yaml"))
logger = logging.getLogger(__name__)

def load_config():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)

config = load_config().get("telegram", {})

def _send_telegram_message(message: str) -> bool:
    if not config.get("enabled", False):
        logger.info("🚫 Telegram notifications disabled in config.")
        return False

    token = config.get("token")
    chat_id = config.get("chat_id")
    if not token or not chat_id:
        logger.warning("⚠️ Telegram token or chat_id missing.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": message}

    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        logger.info("✅ Telegram alert sent successfully.")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send Telegram alert: {e}")
        return False

async def send_telegram(message: str, event: dict) -> bool:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _send_telegram_message, message)
