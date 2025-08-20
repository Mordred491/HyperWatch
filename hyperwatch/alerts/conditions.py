def is_vault_open(event):
    return event.get("type") == "vault_open"

def is_vault_closed(event):
    return event.get("type") == "vault_close"

def is_vault_deposit(event):
    return event.get("type") == "vault_deposit"

def is_vault_withdraw(event):
    return event.get("type") == "vault_withdraw"

def is_collateral_changed(event):
    return event.get("type") == "collateral_adjust"

def borrow_exceeds(event, threshold):
    if event.get("type") in ["vault_open", "vault_update"]:
        try:
            debt = float(event.get("debt", 0))
            return debt > threshold
        except (TypeError, ValueError):
            return False
    return False

def price_above(event, threshold):
    if event.get("type") == "trade":
        try:
            price = float(event.get("price", 0))
            return price > threshold
        except (TypeError, ValueError):
            return False
    return False

def price_below(event, threshold):
    if event.get("type") == "trade":
        try:
            price = float(event.get("price", 0))
            return price < threshold
        except (TypeError, ValueError):
            return False
    return False

def pnl_above(event, threshold):
    try:
        pnl = float(event.get("closedPnl", 0))
        return pnl > threshold
    except (TypeError, ValueError):
        return False

def pnl_below(event, threshold):
    try:
        pnl = float(event.get("closedPnl", 0))
        return pnl < threshold
    except (TypeError, ValueError):
        return False

def volume_above(event, threshold):
    """Check if trade volume exceeds threshold"""
    try:
        if event.get("type") in ["user_fill", "trade"]:
            size = float(event.get("size", 0))
            price = float(event.get("price", 0))
            volume = size * price
            return volume > threshold
        return False
    except (TypeError, ValueError):
        return False

def coin_match(event, coin_name):
    return event.get("coin", "").upper() == coin_name.upper()

def side_match(event, side):
    """Check if order/trade side matches (B for buy, A for sell)"""
    return event.get("side", "").upper() == side.upper()

def is_non_user_cancel(event):
    return event.get("type") == "nonUserCancel"

def is_order_open(event):
    return event.get("type") == "order_update" and event.get("status") in ["open", "resting"]

def is_order_cancelled(event):
    return event.get("type") == "order_update" and event.get("status") == "canceled"

def is_order_filled(event):
    return event.get("type") == "order_update" and event.get("status") == "filled"

def is_trade_event(event):
    return event.get("type") == "trade"

def is_user_fill(event):
    return event.get("type") == "user_fill"

def is_liquidation_event(event):
    return event.get("type") == "liquidation"

def is_borrow_event(event):
    return event.get("type") == "vault_update" and float(event.get("debt", 0)) > 0

def is_order_update(event):
    return event.get("type") == "order_update"

def is_position_update(event):
    return event.get("type") == "position_update"

def is_position_open(event):
    return event.get("type") == "position_update" and "Open" in event.get("action", "")

def is_position_close(event):
    return event.get("type") == "position_update" and "Close" in event.get("action", "")

def wallet_match(event, wallet_address):
    """Check if event is for specific wallet"""
    return event.get("wallet", "").lower() == wallet_address.lower()

def amount_above(event, threshold):
    """Check if event amount exceeds threshold"""
    try:
        amount = float(event.get("amount", 0))
        return amount > threshold
    except (TypeError, ValueError):
        return False

def amount_below(event, threshold):
    """Check if event amount is below threshold"""
    try:
        amount = float(event.get("amount", 0))
        return amount < threshold
    except (TypeError, ValueError):
        return False

def is_taker_order(event):
    """Check if order/fill is taker (not maker)"""
    return event.get("isTaker", False) is True