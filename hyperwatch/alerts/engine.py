import logging
import asyncio
import json
import aiofiles
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from hyperwatch.alerts.triggers import evaluate_conditions
from hyperwatch.alerts.rules import DEFAULT_RULES
from hyperwatch.notifications.dispatcher import dispatch_notification

logger = logging.getLogger(__name__)


class AlertEngine:
    """
    Engine to process events and dispatch alerts.
    Rate limiting is now handled in the dispatcher layer for notifications only.
    """

    def __init__(self, alert_handler: Optional[Any] = None):
        """
        Initialize the AlertEngine.

        Args:
            alert_handler: Optional callable to handle alert dispatch.
                           Defaults to `dispatch_notification`.
        """
        self.alert_handler = alert_handler or dispatch_notification
        self._alert_queue: asyncio.Queue = asyncio.Queue()

        # File-based communication for CLI
        self.event_file = Path.home() / ".hyperwatch" / "events.jsonl"
        self.last_processed_line = 0
        self._ensure_event_file_exists()

    def _ensure_event_file_exists(self):
        """Create the events file directory if it doesn't exist."""
        self.event_file.parent.mkdir(exist_ok=True)
        if not self.event_file.exists():
            self.event_file.touch()

    async def inject_event_from_cli(self, event: Dict[str, Any]) -> None:
        """
        Method for CLI to inject events into the engine.
        This writes events to a shared file that the dashboard can read.
        FIXED: No rate limiting here - this is just event storage.
        """
        try:
            event_with_timestamp = {
                **event,
                'injected_at': datetime.now().isoformat(),
                'source': 'cli_monitor'
            }

            async with aiofiles.open(self.event_file, 'a') as f:
                await f.write(json.dumps(event_with_timestamp) + '\n')

            await self.process_event(event_with_timestamp)

        except Exception as e:
            logger.error(f"Failed to inject event from CLI: {e}")

    async def load_events_from_file(self) -> List[Dict[str, Any]]:
        """
        Load new events from the shared file (for dashboard).
        Only reads lines that haven't been processed yet.
        """
        new_events = []
        try:
            if not self.event_file.exists():
                return new_events

            async with aiofiles.open(self.event_file, 'r') as f:
                lines = await f.readlines()

            for i, line in enumerate(lines[self.last_processed_line:], self.last_processed_line):
                try:
                    event = json.loads(line.strip())
                    new_events.append(event)
                    self.last_processed_line = i + 1
                except json.JSONDecodeError:
                    continue

        except Exception as e:
            logger.error(f"Failed to load events from file: {e}")

        return new_events

    async def sync_with_cli_events(self) -> None:
        """Sync with events from CLI monitor (for dashboard use)."""
        new_events = await self.load_events_from_file()
        for event in new_events:
            await self.process_event(event)

    async def process_event(self, event: Dict[str, Any]) -> None:
        #Process a single event and dispatch alerts based on rules.
        logger.debug(f"Processing event: {event}")

        for rule in DEFAULT_RULES:
            try:
                conditions = rule.get("conditions", [])
                if evaluate_conditions(event, conditions):
                    channels = rule.get("channels", ["telegram", "email", "discord", "webhook"])
                    
                    await self.alert_handler(event, channels=channels)
                    
                    # Add to alert queue for dashboard
                    await self._alert_queue.put(event)
                    
                    logger.info(f"Processed alert for rule '{rule.get('name', 'unknown')}' - sent to dispatcher")

            except Exception as e:
                logger.exception(f"Error processing rule '{rule.get('name', 'unknown')}': {e}")

    async def alert_stream(self):
        """Async generator yielding alert messages for real-time dashboard streaming."""
        while True:
            try:
                # Sync with CLI events
                await self.sync_with_cli_events()
                
                # Wait for new alerts with timeout
                alert = await asyncio.wait_for(self._alert_queue.get(), timeout=1.0)
                yield alert
            except asyncio.TimeoutError:
                continue

    async def health_check(self) -> Dict[str, Any]:
        """Return health status of the alert engine."""
        return {
            "alert_engine": "healthy",
            "queue_size": self._alert_queue.qsize(),
            "event_file_path": str(self.event_file),
            "events_processed": self.last_processed_line
        }

    async def close(self) -> None:
        """Clean up resources and close the engine."""
        logger.info("✅ Alert engine closed")