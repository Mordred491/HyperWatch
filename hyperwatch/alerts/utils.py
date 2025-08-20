def format_alert_message(event, matched_conditions=None):
    user = event.get("user", "unknown")
    coin = event.get("coin", "")
    event_type = event.get("type", "event")

    msg = f"⚠️ Alert for {user} on {coin} — {event_type}"
    if matched_conditions:
        condition_names = [c.get("type") for c in matched_conditions]
        msg += f"\n✅ Matched: {', '.join(condition_names)}"

    return msg
