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

config = load_config().get("discord", {})

def _send_discord_message(message: str) -> bool:
    if not config.get("enabled", False):
        logger.info("🚫 Discord notifications disabled in config.")
        return False

    webhook_url = config.get("webhook_url")
    if not webhook_url:
        logger.warning("⚠️ Discord webhook_url missing.")
        return False

    data = {"content": message}

    try:
        response = requests.post(webhook_url, json=data)
        response.raise_for_status()
        logger.info("✅ Discord alert sent successfully.")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send Discord alert: {e}")
        return False

async def send_discord(message: str, event: dict) -> bool:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _send_discord_message, message)
