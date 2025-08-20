import logging
from hyperwatch.alerts.conditions import (
    is_order_update,
    is_order_open,
    is_order_filled,
    is_order_cancelled,
    is_vault_open,
    is_vault_closed,
    is_vault_deposit,
    is_vault_withdraw,
    is_collateral_changed,
    borrow_exceeds,
    price_above,
    price_below,
    pnl_above,
    pnl_below,
    volume_above,
    coin_match,
    side_match,
    is_non_user_cancel,
    is_trade_event,
    is_user_fill,
    is_liquidation_event,
    is_borrow_event,
    is_position_update,
    is_position_open,
    is_position_close,
    wallet_match,
    amount_above,
    amount_below,
    is_taker_order
)

logger = logging.getLogger(__name__)

# Comprehensive condition function mapping
default_conditions = {
    "is_order_update": is_order_update,
    "is_order_open": is_order_open,
    "is_order_filled": is_order_filled,
    "is_order_cancelled": is_order_cancelled,
    "is_vault_open": is_vault_open,
    "is_vault_closed": is_vault_closed,
    "is_vault_deposit": is_vault_deposit,
    "is_vault_withdraw": is_vault_withdraw,
    "is_collateral_changed": is_collateral_changed,
    "borrow_exceeds": borrow_exceeds,
    "price_above": price_above,
    "price_below": price_below,
    "pnl_above": pnl_above,
    "pnl_below": pnl_below,
    "volume_above": volume_above,
    "coin_match": coin_match,
    "side_match": side_match,
    "is_non_user_cancel": is_non_user_cancel,
    "is_trade_event": is_trade_event,
    "is_user_fill": is_user_fill,
    "is_liquidation_event": is_liquidation_event,
    "is_borrow_event": is_borrow_event,
    "is_position_update": is_position_update,
    "is_position_open": is_position_open,
    "is_position_close": is_position_close,
    "wallet_match": wallet_match,
    "amount_above": amount_above,
    "amount_below": amount_below,
    "is_taker_order": is_taker_order
}

def evaluate_conditions(event, conditions, condition_funcs=default_conditions):
    """
    Evaluate a list of conditions against an event.
    Returns list of matched conditions.
    """
    matched = []
    
    if not conditions:
        logger.debug("No conditions to evaluate")
        return matched
    
    for cond in conditions:
        cond_type = cond.get("type")
        if not cond_type:
            logger.warning("⚠️ Skipping condition without type.")
            continue
            
        func = condition_funcs.get(cond_type)
        if not func:
            logger.warning(f"⚠️ No function found for condition type: '{cond_type}'")
            continue
            
        try:
            args = cond.get("args", [])
            result = func(event, *args) if args else func(event)
            
            logger.debug(f"🔍 Condition '{cond_type}' with args {args} evaluated to {result}")
            
            if result:
                matched.append(cond)
                logger.debug(f"✅ Condition '{cond_type}' matched!")
                
        except Exception as e:
            logger.warning(f"⚠️ Condition '{cond_type}' raised error: {e}")
            logger.debug(f"Event data: {event}")
    
    return matched

def any_conditions_match(event, conditions):
    """Check if any conditions match (OR logic)"""
    return len(evaluate_conditions(event, conditions)) > 0

def all_conditions_match(event, conditions):
    """Check if all conditions match (AND logic)"""
    if not conditions:
        return False
    return len(evaluate_conditions(event, conditions)) == len(conditions)

def evaluate_rule_against_event(event, rule):
    """
    Evaluate a complete rule against an event.
    Returns tuple: (matched: bool, alert_data: dict)
    """
    try:
        # Import here to avoid circular imports
        from hyperwatch.alerts.rules import evaluate_rule_conditions, create_alert_from_rule
        
        if evaluate_rule_conditions(event, rule):
            alert_data = create_alert_from_rule(event, rule)
            return True, alert_data
        else:
            return False, None
            
    except Exception as e:
        logger.error(f"❌ Error evaluating rule {rule.get('id', 'unknown')}: {e}")
        return False, None

def process_event_against_rules(event, rules):
    """
    Process an event against multiple rules and return all matching alerts.
    """
    alerts = []
    
    for rule in rules:
        try:
            matched, alert_data = evaluate_rule_against_event(event, rule)
            if matched and alert_data:
                alerts.append(alert_data)
                logger.info(f"🎯 Rule '{rule.get('name')}' matched for event type '{event.get('type')}'")
        except Exception as e:
            logger.error(f"❌ Error processing rule {rule.get('id')}: {e}")
    
    return alerts

def get_condition_function(condition_type):
    """Get a condition function by name"""
    return default_conditions.get(condition_type)

def add_custom_condition(name, func):
    """Add a custom condition function"""
    if callable(func):
        default_conditions[name] = func
        logger.info(f"✅ Added custom condition: {name}")
    else:
        logger.error(f"❌ Custom condition {name} must be callable")

def remove_condition(name):
    """Remove a condition function"""
    if name in default_conditions:
        del default_conditions[name]
        logger.info(f"🗑️ Removed condition: {name}")

def list_available_conditions():
    """Get list of all available condition types"""
    return list(default_conditions.keys())

# Utility functions for complex condition logic
def create_and_condition(conditions):
    """Create a compound condition that requires ALL sub-conditions to match"""
    def and_condition(event):
        return all_conditions_match(event, conditions)
    return and_condition

def create_or_condition(conditions):
    """Create a compound condition that requires ANY sub-condition to match"""
    def or_condition(event):
        return any_conditions_match(event, conditions)
    return or_condition

def create_not_condition(condition):
    """Create a condition that negates another condition"""
    def not_condition(event):
        matched = evaluate_conditions(event, [condition])
        return len(matched) == 0
    return not_condition

# Event filtering utilities
def filter_events_by_wallet(events, wallet_address):
    """Filter events for a specific wallet"""
    return [event for event in events if event.get('wallet', '').lower() == wallet_address.lower()]

def filter_events_by_coin(events, coin_name):
    """Filter events for a specific coin"""
    return [event for event in events if event.get('coin', '').upper() == coin_name.upper()]

def filter_events_by_type(events, event_type):
    """Filter events by event type"""
    return [event for event in events if event.get('type') == event_type]

def filter_events_by_timeframe(events, start_timestamp, end_timestamp):
    """Filter events within a time range"""
    filtered = []
    for event in events:
        timestamp = event.get('timestamp')
        if timestamp and start_timestamp <= timestamp <= end_timestamp:
            filtered.append(event)
    return filtered