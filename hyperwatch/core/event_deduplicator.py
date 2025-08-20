import time
import hashlib
import logging
from typing import Dict, Set, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class EventDeduplicator:
    """
    Enhanced deduplicator with better spam filtering for market bots.
    Prevents notification spam while ensuring important events get through.
    """
    
    def __init__(self, window_seconds: int = 120, max_similar_events: int = 2):
        """
        Args:
            window_seconds: Time window for grouping similar events
            max_similar_events: Max similar events to allow in the window (lowered to 2)
        """
        self.window_seconds = window_seconds
        self.max_similar_events = max_similar_events
        
        # Store event signatures with timestamps
        self.event_signatures: Dict[str, list] = {}  # signature -> [timestamp, ...]
        
        # Track suppressed events for later summary
        self.suppressed_events: Dict[str, list] = {}  # signature -> [event, ...]
        
        # Track per-wallet event counts
        self.wallet_event_counts: Dict[str, int] = {}
        
        # Last cleanup time
        self.last_cleanup = time.time()
        
        # Summary generation timer
        self.last_summary_time = time.time()
        self.summary_interval = 300  # 5 minutes

    def _generate_signature(self, event: Dict) -> str:
        """
        Generate a signature for an event to identify similar events.
        Enhanced to better group similar bot activities.
        """
        wallet = event.get("wallet", "unknown")[:12]  # Shorter wallet portion
        coin = event.get("coin", "unknown")
        event_type = event.get("type", "unknown")
        usd_value = event.get("usd_value", 0)
        
        # More granular USD value grouping to catch bot patterns
        if usd_value < 10:
            value_range = "micro"      # $0-10
        elif usd_value < 100:
            value_range = "small"      # $10-100
        elif usd_value < 1000:
            value_range = "medium"     # $100-1K
        elif usd_value < 10000:
            value_range = "large"      # $1K-10K
        elif usd_value < 100000:
            value_range = "xlarge"     # $10K-100K
        else:
            value_range = "whale"      # $100K+
        
        # Include time bucket for better bot detection (5-minute buckets)
        time_bucket = int(time.time() // 300)  # 5-minute intervals
        
        # Create signature from key components
        signature_data = f"{wallet}:{coin}:{event_type}:{value_range}:{time_bucket}"
        
        # Hash to create shorter key
        return hashlib.md5(signature_data.encode()).hexdigest()[:16]

    def _cleanup_old_entries(self):
        """Remove old entries to prevent memory bloat"""
        now = time.time()
        
        # Only cleanup every 2 minutes
        if now - self.last_cleanup < 120:
            return
            
        cutoff = now - self.window_seconds
        cleaned_signatures = 0
        cleaned_suppressed = 0
        
        # Clean up old signatures
        for signature in list(self.event_signatures.keys()):
            old_count = len(self.event_signatures[signature])
            self.event_signatures[signature] = [
                ts for ts in self.event_signatures[signature] if ts > cutoff
            ]
            if not self.event_signatures[signature]:
                del self.event_signatures[signature]
                cleaned_signatures += 1
            elif len(self.event_signatures[signature]) < old_count:
                cleaned_signatures += 1
        
        # Clean up old suppressed events
        for signature in list(self.suppressed_events.keys()):
            if signature not in self.event_signatures:
                del self.suppressed_events[signature]
                cleaned_suppressed += 1
        
        if cleaned_signatures > 0 or cleaned_suppressed > 0:
            logger.debug(f"🧹 Cleaned {cleaned_signatures} signatures, {cleaned_suppressed} suppressed events")
        
        self.last_cleanup = now

    def should_allow_event(self, event: Dict) -> bool:
        """
        Enhanced event filtering with better bot detection.
        Returns True if event should be processed, False if it should be suppressed.
        """
        self._cleanup_old_entries()
        
        signature = self._generate_signature(event)
        now = time.time()
        wallet = event.get("wallet", "unknown")
        usd_value = event.get("usd_value", 0)
        
        # Initialize signature tracking if needed
        if signature not in self.event_signatures:
            self.event_signatures[signature] = []
            self.suppressed_events[signature] = []
        
        # Count recent events with same signature
        recent_count = len([
            ts for ts in self.event_signatures[signature] 
            if now - ts <= self.window_seconds
        ])
        
        # Enhanced filtering logic
        
        # Always allow high-value transactions (likely not bots)
        if usd_value >= 50000:  # $50K+ always gets through
            self.event_signatures[signature].append(now)
            logger.debug(f"✅ High-value event allowed: ${usd_value:,.2f}")
            return True
        
        # Allow medium-value transactions with less restriction
        if usd_value >= 10000 and recent_count < self.max_similar_events * 2:
            self.event_signatures[signature].append(now)
            logger.debug(f"✅ Medium-value event allowed: ${usd_value:,.2f} (count: {recent_count})")
            return True
        
        # Standard filtering for smaller amounts
        if recent_count < self.max_similar_events:
            self.event_signatures[signature].append(now)
            
            # Track wallet activity
            if wallet not in self.wallet_event_counts:
                self.wallet_event_counts[wallet] = 0
            self.wallet_event_counts[wallet] += 1
            
            logger.debug(f"✅ Event allowed for {wallet[:8]}...: ${usd_value:,.2f} (similar events: {recent_count}/{self.max_similar_events})")
            return True
        else:
            # Suppress - add to suppressed events for summary
            self.suppressed_events[signature].append(event)
            logger.debug(f"🚫 Event suppressed for {wallet[:8]}...: ${usd_value:,.2f} (too many similar: {recent_count}/{self.max_similar_events})")
            return False

    def get_suppressed_summary(self, signature: str) -> Optional[Dict]:
        """Get summary of suppressed events for a signature"""
        if signature not in self.suppressed_events or not self.suppressed_events[signature]:
            return None
        
        events = self.suppressed_events[signature]
        if not events:
            return None
        
        # Create enhanced summary
        total_count = len(events)
        total_value = sum(e.get("usd_value", 0) for e in events)
        coins = set(e.get("coin", "unknown") for e in events)
        wallet = events[0].get("wallet", "unknown")
        event_types = set(e.get("type", "unknown") for e in events)
        
        # Determine summary type based on suppressed activity
        if total_count >= 10:
            activity_level = "High Bot Activity"
        elif total_count >= 5:
            activity_level = "Moderate Bot Activity"
        else:
            activity_level = "Similar Events"
        
        return {
            "type": "suppressed_summary",
            "wallet": wallet,
            "suppressed_count": total_count,
            "event_types": list(event_types),
            "coins": list(coins),
            "total_usd_value": total_value,
            "time_window": self.window_seconds,
            "activity_level": activity_level,
            "summary_message": (
                f"📕 {activity_level}: Suppressed {total_count} similar events "
                f"from {wallet[:8]}... on {', '.join(coins)} "
                f"(Total: ${total_value:,.2f} over {self.window_seconds//60} minutes)"
            )
        }

    def get_all_suppressed_summaries(self) -> list:
        """Get summaries for all signatures with suppressed events"""
        now = time.time()
        
        # Only generate summaries every 5 minutes to avoid spam
        if now - self.last_summary_time < self.summary_interval:
            return []
        
        summaries = []
        for signature in list(self.suppressed_events.keys()):
            summary = self.get_suppressed_summary(signature)
            if summary and summary["suppressed_count"] >= 3:  # Only summarize if 3+ events
                summaries.append(summary)
                # Clear after creating summary
                self.suppressed_events[signature] = []
        
        if summaries:
            self.last_summary_time = now
            logger.info(f"📊 Generated {len(summaries)} suppression summaries")
        
        return summaries

    def get_wallet_stats(self) -> Dict[str, int]:
        """Get per-wallet event statistics"""
        return self.wallet_event_counts.copy()

    def reset_wallet_stats(self):
        """Reset wallet statistics"""
        self.wallet_event_counts.clear()

    def get_status(self) -> Dict:
        """Get current deduplicator status"""
        return {
            "active_signatures": len(self.event_signatures),
            "suppressed_signatures": len(self.suppressed_events),
            "total_suppressed_events": sum(len(events) for events in self.suppressed_events.values()),
            "wallet_event_counts": self.wallet_event_counts,
            "window_seconds": self.window_seconds,
            "max_similar_events": self.max_similar_events
        }

# Global deduplicator instance with more aggressive settings
event_deduplicator = EventDeduplicator(
    window_seconds=180,  # 3 minute window (increased)
    max_similar_events=2  # Allow max 2 similar events per window (decreased)
)