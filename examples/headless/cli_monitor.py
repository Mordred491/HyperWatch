import logging
import asyncio
from hyperwatch.core.hypercore_client import HyperCoreClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)   
logger = logging.getLogger(__name__)

async def main():
    logger.info("🚀 Starting CLI monitor...")
    client = HyperCoreClient()
    try:
        await client.start()
    except asyncio.CancelledError:
        logger.info("👋 Exiting monitor due to cancellation.")
    except KeyboardInterrupt:
        logger.info("👋 Exiting monitor due to keyboard interrupt.")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Exiting CLI monitor.")
