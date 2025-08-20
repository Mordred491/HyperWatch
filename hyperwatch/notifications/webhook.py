import os
import yaml
import aiohttp
import logging

CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../config/notification.yaml"))
logger = logging.getLogger(__name__)

def load_config():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)

config = load_config().get("webhook", {})

async def send_webhook(message: str, event: dict):
    if not config.get("enabled", False):
        logger.warning("🚫 Webhook notifications disabled in config.")
        return

    url = config.get("url")
    if not url:
        logger.warning("⚠️ Missing webhook URL in config.")
        return

    payload = {
        "message": message,
        "event": event,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    logger.info("✅ Webhook sent successfully.")
                else:
                    logger.error(f"❌ Webhook failed with status {resp.status}: {await resp.text()}")
    except Exception as e:
        logger.exception(f"❌ Exception while sending webhook: {e}")
