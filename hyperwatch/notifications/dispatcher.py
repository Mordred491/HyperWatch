import logging
import asyncio
import time
from hyperwatch.notifications.webhook import send_webhook
from hyperwatch.notifications.telegram import send_telegram
from hyperwatch.notifications.discord import send_discord
from hyperwatch.notifications.email_notifier import send_email
from hyperwatch.alerts.formatter import format_notification

logger = logging.getLogger(__name__)

CHANNEL_HANDLERS = {
    "webhook": send_webhook,
    "telegram": send_telegram,
    "discord": send_discord,
    "email": send_email
}

# Better rate limiting for notifications only
CHANNEL_COOLDOWNS = {
    "webhook": 15,    # 15 seconds between webhook notifications
    "telegram": 45,   # 45 seconds between telegram messages  
    "discord": 45,    # 45 seconds between discord messages
    "email": 60      # 1 minutes between emails
}

class NotificationRateLimiter:
    """FIXED: Rate limiter specifically for notifications, not events"""
    def __init__(self, cooldowns: dict):
        self.cooldowns = cooldowns
        self.last_sent = {}  # {(channel, wallet_key): timestamp}
        self.pending_events = {}  # {(channel, wallet_key): [event, ...]}

    def _get_wallet_key(self, event: dict) -> str:
        """Extract a stable key from wallet for rate limiting"""
        wallet = event.get("wallet") or event.get("user", "global")
        if wallet and len(wallet) > 8:
            return wallet[:8] + "..."  # Use first 8 chars for grouping
        return wallet

    def _get_key(self, channel: str, wallet_key: str) -> tuple:
        return (channel, wallet_key)

    def can_send_notification(self, channel: str, wallet_key: str) -> bool:
        """Check if we can send a notification for this channel/wallet combo"""
        now = time.time()
        key = self._get_key(channel, wallet_key)
        last_time = self.last_sent.get(key, 0)
        cooldown = self.cooldowns.get(channel, 30)  # Default 30s cooldown
        
        can_send = (now - last_time) > cooldown
        
        if can_send:
            self.last_sent[key] = now
            logger.debug(f"✅ Notification allowed for {channel}:{wallet_key}")
        else:
            remaining = cooldown - (now - last_time)
            logger.debug(f"⏰ Notification rate limited for {channel}:{wallet_key} - {remaining:.1f}s remaining")
            
        return can_send

    def add_pending_event(self, channel: str, wallet_key: str, event: dict):
        """Add event to pending queue"""
        key = self._get_key(channel, wallet_key)
        if key not in self.pending_events:
            self.pending_events[key] = []
        self.pending_events[key].append(event)
        logger.debug(f"📌 Added event to pending queue for {channel}:{wallet_key} (total: {len(self.pending_events[key])})")

    def get_pending_events(self, channel: str, wallet_key: str) -> list:
        """Get pending events for a channel/wallet"""
        key = self._get_key(channel, wallet_key)
        return self.pending_events.get(key, [])

    def clear_pending_events(self, channel: str, wallet_key: str):
        """Clear pending events for a channel/wallet"""
        key = self._get_key(channel, wallet_key)
        if key in self.pending_events:
            count = len(self.pending_events[key])
            del self.pending_events[key]
            logger.debug(f"🧹 Cleared {count} pending events for {channel}:{wallet_key}")

    async def process_event_notification(self, channel: str, event: dict):
        """Main method to handle event notification with rate limiting"""
        wallet_key = self._get_wallet_key(event)
        
        if self.can_send_notification(channel, wallet_key):
            # Get any pending events and combine with current
            pending = self.get_pending_events(channel, wallet_key)
            all_events = pending + [event]
            
            # Clear pending since we're sending everything
            if pending:
                self.clear_pending_events(channel, wallet_key)
                logger.info(f"📤 Sending {len(all_events)} events ({len(pending)} pending + 1 current) to {channel}")
            else:
                logger.info(f"📤 Sending 1 event to {channel}")
            
            # Send combined notification
            await self._send_notification(channel, all_events)
        else:
            # Rate limited, add to pending
            self.add_pending_event(channel, wallet_key, event)

    async def _send_notification(self, channel: str, events: list):
        """Send notification to specific channel"""
        handler = CHANNEL_HANDLERS.get(channel)
        if not handler:
            logger.warning(f"⚠️ Unsupported notification channel: {channel}")
            return

        try:
            if len(events) == 1:
                # Single event - format normally
                message = format_notification(events[0])
            else:
                # Multiple events - create combined message
                message = self._combine_events_message(events)
            
            logger.debug(f"📨 Sending message to {channel}: {message[:100]}...")
            
            if asyncio.iscoroutinefunction(handler):
                await handler(message, events[-1])  # Pass latest event for context
            else:
                await asyncio.to_thread(handler, message, events[-1])
                
            logger.info(f"✅ Successfully sent {len(events)} event(s) via {channel}")
            
        except Exception as e:
            logger.error(f"❌ Failed to send notification via {channel}: {e}")

    def _combine_events_message(self, events: list) -> str:
        """Combine multiple events into a single message"""
        if not events:
            return "No events to display."
        
        if len(events) == 1:
            return format_notification(events[0])
        
        # Group events by type and coin for summary
        event_summary = {}
        total_value = 0
        
        for event in events:
            event_type = event.get("type", "unknown")
            coin = event.get("coin", "unknown")
            value = event.get("usd_value", 0)
            
            key = f"{event_type}_{coin}"
            if key not in event_summary:
                event_summary[key] = {"count": 0, "value": 0, "coin": coin, "type": event_type}
            
            event_summary[key]["count"] += 1
            event_summary[key]["value"] += value
            total_value += value
        
        # Create summary message
        wallet = events[0].get("wallet", "unknown")
        summary_lines = [f"📊 **Summary: {len(events)} events from {wallet[:8]}...**"]
        
        for key, info in event_summary.items():
            if info["value"] > 0:
                summary_lines.append(f"• {info['count']}x {info['type']} on {info['coin']} (${info['value']:,.2f})")
            else:
                summary_lines.append(f"• {info['count']}x {info['type']} on {info['coin']}")
        
        if total_value > 0:
            summary_lines.append(f"\n💰 **Total Value: ${total_value:,.2f}**")
        
        # Add latest event details
        latest_event = events[-1]
        summary_lines.append(f"\n📋 **Latest Event:**")
        summary_lines.append(format_notification(latest_event))
        
        return "\n".join(summary_lines)

    async def flush_pending_notifications(self):
        """Periodic task to flush pending notifications that can now be sent"""
        now = time.time()
        keys_to_flush = []
        
        for key, events in list(self.pending_events.items()):
            channel, wallet_key = key
            last_sent = self.last_sent.get(key, 0)
            cooldown = self.cooldowns.get(channel, 30)
            
            if (now - last_sent) > cooldown and events:
                keys_to_flush.append((channel, wallet_key, events))
        
        for channel, wallet_key, events in keys_to_flush:
            logger.info(f"⏰ Flushing {len(events)} pending notifications for {channel}:{wallet_key}")
            self.clear_pending_events(channel, wallet_key)
            self.last_sent[self._get_key(channel, wallet_key)] = now
            await self._send_notification(channel, events)

# Global rate limiter instance
notification_rate_limiter = NotificationRateLimiter(CHANNEL_COOLDOWNS)

# Global task tracking for the periodic flush task
_flush_task = None

def _ensure_flush_task_running():
    """Ensure the periodic flush task is running (called when needed)"""
    global _flush_task
    try:
        loop = asyncio.get_running_loop()
        if _flush_task is None or _flush_task.done():
            _flush_task = loop.create_task(periodic_flush_task())
            logger.debug("🔄 Started periodic flush task")
    except RuntimeError:
        # No event loop running, will be started later when needed
        pass

async def dispatch_notification(event: dict, channels: list[str] = None):
    """
    Main entry point for dispatching notifications with proper rate limiting.
    Rate limiting only affects outgoing notifications, NOT incoming events.
    """
    # Ensure flush task is running when we actually need it
    _ensure_flush_task_running()
    
    if not channels:
        channels = list(CHANNEL_HANDLERS.keys())

    # Process notification for each channel
    for channel in channels:
        try:
            await notification_rate_limiter.process_event_notification(channel, event)
        except Exception as e:
            logger.error(f"❌ Error dispatching to {channel}: {e}")

async def periodic_flush_task():
    """Background task to periodically flush pending notifications"""
    while True:
        try:
            await asyncio.sleep(30)  # Check every 30 seconds
            await notification_rate_limiter.flush_pending_notifications()
        except Exception as e:
            logger.error(f"❌ Error in periodic flush task: {e}")

