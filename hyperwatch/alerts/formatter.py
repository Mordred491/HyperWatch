import logging
import inspect
from datetime import datetime, timezone

def shorten_wallet(wallet):
    """Shortens a wallet address for display."""
    if not wallet:
        return "N/A"
    wallet_str = str(wallet)
    return f"{wallet_str[:6]}...{wallet_str[-4:]}" if len(wallet_str) > 12 else wallet_str

def format_large_number(value):
    try:
        value = float(value)
        if value == 0:
            return "0.00"
        elif value < 0.001:
            return f"{value:.6f}"
        elif value < 1:
            return f"{value:.4f}"
        elif value >= 1_000_000_000:
            return f"{value/1_000_000_000:.2f}B"
        elif value >= 1_000_000:
            return f"{value/1_000_000:.2f}M"
        elif value >= 1_000:
            return f"{value/1_000:.2f}K"
        else:
            return f"{value:.2f}"
    except (ValueError, TypeError):
        return str(value)

def is_significant_order(usd_value, size=None, coin_name=None, threshold_usd=5000):
    """Enhanced significance detection - lowered threshold for better filtering"""
    try:
        usd_val = float(usd_value)
        return usd_val >= threshold_usd
    except (ValueError, TypeError):
        return False

def is_valid_order_for_notification(size, price, usd_value, min_usd=5.0):
    """Enhanced validation - increased minimum to reduce spam"""
    try:
        size_float = float(size)
        price_float = float(price)
        usd_float = float(usd_value)
        if size_float <= 0 or usd_float < min_usd or price_float <= 0:
            return False
        return True
    except (ValueError, TypeError):
        return False

def human_readable_timestamp(ts):
    """Converts timestamp to human-readable string in UTC."""
    if ts is None:
        return None
    if isinstance(ts, str):
        try:
            ts_float = float(ts)
        except ValueError:
            return ts
    else:
        ts_float = float(ts)
    if ts_float > 1e12:
        ts_float /= 1000.0
    try:
        dt = datetime.fromtimestamp(ts_float, tz=timezone.utc)
        return dt.strftime("%H:%M:%S UTC")  # Shorter format
    except Exception as e:
        logging.warning(f"⚠️ Failed to convert timestamp {ts}: {e}")
        return str(ts)

def get_significance_level(usd_value):
    """Determine significance level for better categorization"""
    try:
        value = float(usd_value)
        if value >= 1_000_000:
            return "🔥 WHALE", "#FF4444"
        elif value >= 100_000:
            return "🚀 LARGE", "#FF8800"
        elif value >= 10_000:
            return "⚡ MEDIUM", "#FFAA00"
        elif value >= 1_000:
            return "📈 NOTABLE", "#00AA00"
        else:
            return "", "#888888"
    except (ValueError, TypeError):
        return "", "#888888"

def format_user_fill(event, platform="telegram", price_data=None):
    """Enhanced user fill formatter with better output"""
    side = str(event.get("side", "unknown")).upper()
    coin = event.get("coin", "UNKNOWN")
    price = event.get("price", 0)
    size = event.get("size", 0)
    wallet = event.get("wallet", "UNKNOWN")
    usd_value = event.get("usd_value", 0)
    position_action = event.get("position_action", "Trade")
    timestamp = human_readable_timestamp(event.get("timestamp") or event.get("timestamp_readable"))

    # Price correction using market data
    if price_data and coin in price_data:
        try:
            market_price = float(price_data[coin])
            if price == 0 or float(price) > market_price * 10 or float(price) < market_price / 10:
                logging.info(f"🔄 Using market price for {coin}: ${market_price} (was ${price})")
                price = market_price
                usd_value = float(size) * market_price
        except (ValueError, TypeError):
            pass
    
    # Enhanced validation
    if not is_valid_order_for_notification(size, price, usd_value):
        return None
    
    side_mapping = {
        "B": ("BUY", "🟢"), 
        "A": ("SELL", "🔴"), 
        "S": ("SELL", "🔴"), 
        "BUY": ("BUY", "🟢"), 
        "SELL": ("SELL", "🔴")
    }
    side_text, side_emoji = side_mapping.get(side, ("TRADE", "⚪"))
    
    try:
        price_float = float(price)
        if price_float < 1:
            price_str = f"${price_float:.6f}"
        elif price_float < 100:
            price_str = f"${price_float:.4f}"
        else:
            price_str = f"${price_float:,.2f}"
        
        size_str = format_large_number(size)
        usd_str = f"${format_large_number(usd_value)}"
    except (ValueError, TypeError):
        price_str, size_str, usd_str = f"${price}", str(size), f"${usd_value}"

    wallet_short = shorten_wallet(wallet)
    significance_badge, _ = get_significance_level(usd_value)
    time_str = f" • {timestamp}" if timestamp else ""
    
    # Simplified action text
    action_text = position_action.replace("(Large Position)", "").replace("(Medium Position)", "").strip()
    
    if platform in ("telegram", "discord"):
        msg = f"💹 **{action_text}** {significance_badge}\n"
        msg += f"{side_emoji} `{size_str}` {coin} @ `{price_str}`\n"
        msg += f"💵 **{usd_str}** • `{wallet_short}`{time_str}"
        return msg
    elif platform == "email":
        significance_html = f"<span style='color:#FF4444; font-weight:bold;'>{significance_badge}</span>" if significance_badge else ""
        time_html = f"<span style='color:#888;'>{timestamp}</span>" if timestamp else ""
        return f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.4; padding: 10px; border-left: 3px solid #00AA00;">
            <h4 style="margin:0; color:#333;">💹 {action_text} {significance_html}</h4>
            <p style="margin:5px 0; font-size:14px;">
                {side_emoji} {size_str} {coin} @ <strong>{price_str}</strong><br>
                💵 <strong style="color:#00AA00;">{usd_str}</strong> • <code>{wallet_short}</code>
                {time_html}
            </p>
        </div>
        """
    else:
        msg = f"💹 {action_text} {significance_badge}\n"
        msg += f"{side_text} {size_str} {coin} @ {price_str}\n"
        msg += f"Value: {usd_str} • {wallet_short}{time_str}"
        return msg

def format_order_update(event, platform="telegram", price_data=None):
    """Enhanced order update formatter"""
    side = str(event.get("side", "unknown")).upper()
    coin = event.get("coin", "UNKNOWN")
    price = event.get("price", 0)
    size = event.get("size", 0)
    status = str(event.get("status", "N/A")).upper()
    wallet = event.get("wallet", "UNKNOWN")
    usd_value = event.get("usd_value", 0)
    timestamp = human_readable_timestamp(event.get("timestamp") or event.get("timestamp_readable"))

    # Price correction
    if price_data and coin in price_data:
        try:
            market_price = float(price_data[coin])
            if price == 0 or float(price) > market_price * 10 or float(price) < market_price / 10:
                price = market_price
                usd_value = float(size) * market_price
        except (ValueError, TypeError):
            pass

    # Skip low-value orders except for cancellations
    if status not in ["CANCELED", "CANCELLED"] and not is_valid_order_for_notification(size, price, usd_value):
        return None

    side_mapping = {
        "B": ("BUY", "🟢"), 
        "A": ("SELL", "🔴"), 
        "S": ("SELL", "🔴"), 
        "BUY": ("BUY", "🟢"), 
        "SELL": ("SELL", "🔴"), 
        "ASK": ("SELL", "🔴"), 
        "BID": ("BUY", "🟢")
    }
    side_text, side_emoji = side_mapping.get(side, ("TRADE", "⚪"))

    status_info = {
        "FILLED": ("✅", "Filled"),
        "CANCELED": ("❌", "Canceled"),
        "CANCELLED": ("❌", "Canceled"),
        "OPEN": ("🟢", "Placed"),
        "RESTING": ("🟢", "Active"),
        "PARTIAL": ("🟡", "Partial"),
        "PARTIALLY_FILLED": ("🟡", "Partial"),
        "PENDING": ("⏳", "Pending"),
        "REJECTED": ("🚫", "Rejected"),
        "EXPIRED": ("⏰", "Expired"),
        "REPLACED": ("🔄", "Updated"),
        "SUSPENDED": ("⏸️", "Suspended")
    }
    status_emoji, clean_status = status_info.get(status, ("📊", status.title()))

    try:
        price_float = float(price)
        if price_float < 1:
            price_str = f"${price_float:.6f}"
        elif price_float < 100:
            price_str = f"${price_float:.4f}"
        else:
            price_str = f"${price_float:,.2f}"
        
        size_str = format_large_number(size)
        usd_str = f"${format_large_number(usd_value)}"
    except (ValueError, TypeError):
        price_str, size_str, usd_str = f"${price}", str(size), f"${usd_value}"

    wallet_short = shorten_wallet(wallet)
    significance_badge, _ = get_significance_level(usd_value)
    time_str = f" • {timestamp}" if timestamp else ""

    if platform in ("telegram", "discord"):
        msg = f"{status_emoji} **{clean_status} Order** {significance_badge}\n"
        msg += f"{side_emoji} `{size_str}` {coin} @ `{price_str}`\n"
        msg += f"💵 **{usd_str}** • `{wallet_short}`{time_str}"
        return msg
    elif platform == "email":
        significance_html = f"<span style='color:#FF4444; font-weight:bold;'>{significance_badge}</span>" if significance_badge else ""
        time_html = f"<span style='color:#888;'>{timestamp}</span>" if timestamp else ""
        return f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.4; padding: 10px; border-left: 3px solid #0066CC;">
            <h4 style="margin:0; color:#333;">{status_emoji} {clean_status} Order {significance_html}</h4>
            <p style="margin:5px 0; font-size:14px;">
                {side_emoji} {side_text} {size_str} {coin} @ <strong>{price_str}</strong><br>
                💵 <strong style="color:#0066CC;">{usd_str}</strong> • <code>{wallet_short}</code>
                {time_html}
            </p>
        </div>
        """
    else:
        msg = f"{status_emoji} {clean_status} Order {significance_badge}\n"
        msg += f"{side_text} {size_str} {coin} @ {price_str}\n"
        msg += f"Value: {usd_str} • {wallet_short}{time_str}"
        return msg

def format_suppressed_summary(event, platform="telegram", price_data=None):
    """Format suppressed events summary"""
    wallet = event.get("wallet", "unknown")
    count = event.get("suppressed_count", 0)
    total_value = event.get("total_usd_value", 0)
    coins = event.get("coins", [])
    activity_level = event.get("activity_level", "Bot Activity")
    
    wallet_short = shorten_wallet(wallet)
    value_str = format_large_number(total_value)
    coins_str = ", ".join(coins[:3])  # Show max 3 coins
    if len(coins) > 3:
        coins_str += f" +{len(coins)-3} more"
    
    if platform in ("telegram", "discord"):
        msg = f"📕 **{activity_level}**\n"
        msg += f"🤖 Filtered {count} similar events from `{wallet_short}`\n"
        msg += f"💰 Total: **${value_str}** on {coins_str}"
        return msg
    else:
        msg = f"📕 {activity_level}: Filtered {count} events\n"
        msg += f"Wallet: {wallet_short} • Total: ${value_str}\n"
        msg += f"Coins: {coins_str}"
        return msg

def format_unknown_event(event, platform="telegram", price_data=None):
    """Format unknown event types"""
    event_type = event.get("type", "unknown")
    wallet = event.get("wallet", "unknown")
    channel = event.get("channel", "unknown")
    
    wallet_short = shorten_wallet(wallet)
    
    return f"📢 {event_type.replace('_', ' ').title()}\nWallet: {wallet_short} • Channel: {channel}"

# Enhanced formatter registry
NOTIFICATION_FORMATTERS = {
    "user_fill": format_user_fill,
    "order_update": format_order_update,
    "suppressed_summary": format_suppressed_summary,
    "unknown_event": format_unknown_event,
}

def format_notification(event, platform="telegram", price_data=None):
    event_type = event.get("type", "unknown")
    
    # Get appropriate formatter
    formatter = NOTIFICATION_FORMATTERS.get(event_type, format_unknown_event)
    
    try:
        # Check if formatter accepts price_data parameter
        sig = inspect.signature(formatter)
        if 'price_data' in sig.parameters:
            result = formatter(event, platform, price_data)
        else:
            result = formatter(event, platform)
            
        # Validate result
        if not result or not isinstance(result, str) or len(result.strip()) == 0:
            return None
            
        return result.strip()
        
    except Exception as e:
        logging.error(f"❌ Error in formatter {event_type}: {e}")
        
        # Fallback formatter
        try:
            wallet = shorten_wallet(event.get("wallet", "unknown"))
            coin = event.get("coin", "N/A")
            usd_value = event.get("usd_value", 0)
            
            if usd_value > 0:
                return f"💹 {event_type.replace('_', ' ').title()}\n{coin} • ${format_large_number(usd_value)} • {wallet}"
            else:
                return f"📢 {event_type.replace('_', ' ').title()}\n{wallet}"
        except:
            return f"📢 Event: {event_type}"