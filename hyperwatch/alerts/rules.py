from hyperwatch.alerts.triggers import evaluate_conditions

def create_hyperscan_message_template(event_name, priority="medium"):
    """Create message templates"""
    def template(event):
        coin = event.get('coin', 'Unknown')
        method = event.get('method', event_name)
        
        
        if event.get('size_formatted') and event.get('price') and event.get('usd_formatted'):
            size_fmt = event.get('size_formatted')
            price = event.get('price')
            usd_fmt = event.get('usd_formatted')
            
            # Add urgency indicators based on USD value
            usd_value = event.get('usd_value', 0)
            if usd_value >= 10_000_000:  # 10M+
                icon = "🚨🚨"
            elif usd_value >= 1_000_000:  # 1M+
                icon = "🚨"
            elif usd_value >= 100_000:  # 100K+
                icon = "⚠️"
            else:
                icon = "📊"
            
            base_msg = f"{icon} {method} | {coin} | {size_fmt} @ ${price:,.2f} | ${usd_fmt}"
            
        elif event.get('amount_formatted'):
            amount_fmt = event.get('amount_formatted')
            base_msg = f"📊 {method} | {coin} | {amount_fmt}"
            
        else:
            base_msg = f"📊 {method} | {coin}"
        
        # Add wallet info (shortened)
        if event.get('wallet'):
            wallet = event.get('wallet')
            wallet_short = wallet[:6] + '...' + wallet[-4:] if len(wallet) > 12 else wallet
            base_msg += f"\n👛 {wallet_short}"
        
        # Add timestamp info
        if event.get('timestamp_readable'):
            base_msg += f"\n🕐 {event.get('timestamp_readable')}"
        
        return base_msg
    
    return template

def create_position_alert_template():
    """Special template for position alerts"""
    def template(event):
        method = event.get('method', 'Position Update')
        coin = event.get('coin', 'Unknown')
        size_fmt = event.get('size_formatted', event.get('size', ''))
        price = event.get('price', 0)
        usd_fmt = event.get('usd_formatted', '')
        usd_value = event.get('usd_value', 0)
        
        # Determine alert level
        if usd_value >= 10_000_000:
            alert_level = "🚨🚨 MEGA POSITION"
        elif usd_value >= 5_000_000:
            alert_level = "🚨 LARGE POSITION"
        elif usd_value >= 1_000_000:
            alert_level = "⚠️ SIGNIFICANT POSITION"
        else:
            alert_level = "📊 POSITION"
        
        # Format
        main_msg = f"{alert_level}\n"
        main_msg += f"Method: {method}\n"
        main_msg += f"Token: {coin}\n"
        main_msg += f"Amount: {size_fmt}\n"
        main_msg += f"Price: ${price:,.2f}\n"
        main_msg += f"USD Value: ${usd_fmt}\n"
        
        # Add wallet
        if event.get('wallet'):
            wallet = event.get('wallet')
            main_msg += f"Wallet: {wallet[:8]}...{wallet[-4:]}\n"
        
        # Add hash if available
        if event.get('orderId'):
            main_msg += f"Order ID: {event.get('orderId')}\n"
            
        return main_msg.strip()
    
    return template

# Enhanced rules
DEFAULT_RULES = [
    {
        "id": 0,
        "name": "Position Opened",
        "description": "Large position opened (matches HyperScan Open Long)",
        "conditions": [
            {"type": "is_position_open"}
        ],
        "message_template": create_position_alert_template(),
        "channels": ["telegram", "email", "discord", "webhook"],
        "priority": "high"
    },
    {
        "id": 1,
        "name": "Position Closed", 
        "description": "Position closed",
        "conditions": [
            {"type": "is_position_close"}
        ],
        "message_template": create_position_alert_template(),
        "channels": ["telegram", "email", "discord", "webhook"],
        "priority": "high"
    },
    {
        "id": 2,
        "name": "Large Position Alert",
        "description": "Position over $1M (Critical Alert)",
        "conditions": [
            {"type": "volume_above", "args": [1000000]}  # $1M+
        ],
        "message_template": lambda event: f"🚨🚨 LARGE POSITION ALERT 🚨🚨\n{event.get('hyperscan_style', 'Large position detected')}\nUSD Value: ${event.get('usd_formatted', 'Unknown')}\nWallet: {event.get('wallet', 'Unknown')[:8]}...{event.get('wallet', '')[-4:] if event.get('wallet') else ''}",
        "channels": ["telegram", "email", "discord", "webhook"],
        "priority": "critical"
    },
    {
        "id": 3,
        "name": "Mega Position Alert",
        "description": "Position over $10M (Emergency Alert)",
        "conditions": [
            {"type": "volume_above", "args": [10000000]}  # $10M+
        ],
        "message_template": lambda event: f"🚨🚨🚨 MEGA POSITION - EMERGENCY ALERT 🚨🚨🚨\n{event.get('hyperscan_style', 'Mega position detected')}\nUSD Value: ${event.get('usd_formatted', 'Unknown')}\nThis is a ${int(event.get('usd_value', 0)/1000000)}M+ position!\nWallet: {event.get('wallet', 'Unknown')}",
        "channels": ["telegram", "email", "discord", "webhook"],
        "priority": "emergency"
    },
    {
        "id": 4,
        "name": "Order Filled",
        "description": "Order execution alert",
        "conditions": [
            {"type": "is_order_filled"}
        ],
        "message_template": create_hyperscan_message_template("Order Filled"),
        "channels": ["telegram"],
        "priority": "medium"
    },
    {
        "id": 5,
        "name": "User Fill",
        "description": "Trade fill notification",
        "conditions": [
            {"type": "is_user_fill"}
        ],
        "message_template": create_hyperscan_message_template("Fill"),
        "channels": ["telegram", "email", "discord", "webhook"],
        "priority": "medium"
    },
    {
        "id": 6,
        "name": "Significant Trade",
        "description": "Trade over $100K",
        "conditions": [
            {"type": "volume_above", "args": [100000]}  # $100K+
        ],
        "message_template": create_hyperscan_message_template("Significant Trade", "high"),
        "channels": ["telegram", "email", "discord", "webhook"],
        "priority": "high"
    },
    {
        "id": 7,
        "name": "Order Placed",
        "description": "New order placed",
        "conditions": [
            {"type": "is_order_open"}
        ],
        "message_template": create_hyperscan_message_template("Order Placed"),
        "channels": ["telegram", "email", "discord", "webhook"],
        "priority": "low"
    },
    {
        "id": 8,
        "name": "Order Cancelled",
        "description": "Order cancelled",
        "conditions": [
            {"type": "is_order_cancelled"}
        ],
        "message_template": create_hyperscan_message_template("Order Cancelled"),
        "channels": ["telegram", "email", "discord", "webhook"],
        "priority": "low"
    },
    {
        "id": 9,
        "name": "Vault Activity",
        "description": "Vault deposit/withdrawal",
        "conditions": [
            {"type": "is_vault_deposit"},
            {"type": "is_vault_withdraw"}
        ],
        "message_template": create_hyperscan_message_template("Vault Activity"),
        "channels": ["telegram", "email", "discord", "webhook"],
        "priority": "medium"
    },
    {
        "id": 10,
        "name": "ETH-USD Activity",
        "description": "Specific alerts for ETH-USD pair",
        "conditions": [
            {"type": "coin_match", "args": ["ETH"]},
            {"type": "volume_above", "args": [50000]}  # $50K+
        ],
        "message_template": lambda event: f"💎 ETH-USD Activity\n{event.get('hyperscan_style', 'ETH activity detected')}\nAmount: {event.get('size_formatted', 'Unknown')} ETH\nValue: ${event.get('usd_formatted', 'Unknown')}\nPrice: ${event.get('price', 0):,.2f}",
        "channels": ["telegram", "email", "discord", "webhook"],
        "priority": "high"
    }
]

def get_applicable_rules(wallet, coin=None, event_type=None, priority_filter=None):
    """
    Enhanced rule selection that prioritizes based on event significance
    """
    rules_to_check = DEFAULT_RULES
    
    # Filter by event type if provided
    if event_type:
        rules_to_check = get_rules_by_event_type(event_type)
    
    # Filter by priority if provided
    if priority_filter:
        rules_to_check = [rule for rule in rules_to_check if rule.get("priority") == priority_filter]
    
    return [
        {
            "id": rule["id"],
            "name": rule["name"],
            "wallet": wallet,
            "coin": coin,
            "event_type": event_type,
            "conditions": rule["conditions"],
            "message": rule["message_template"],
            "channels": rule.get("channels", ["telegram", "email", "discord", "webhook"]),
            "priority": rule.get("priority", "medium"),
            "description": rule.get("description", "")
        }
        for rule in rules_to_check
    ]

def get_rules_by_event_type(event_type):
    """Enhanced event type matching"""
    matching_rules = []
    for rule in DEFAULT_RULES:
        for condition in rule.get("conditions", []):
            condition_type = condition.get("type", "")
            
            # Enhanced matching logic
            if (event_type == "position_update" and "position" in condition_type) or \
               (event_type == "user_fill" and condition_type in ["is_user_fill", "volume_above"]) or \
               (event_type == "order_update" and "order" in condition_type) or \
               (event_type == "large_position_alert" and "volume_above" in condition_type) or \
               (condition_type in event_type or event_type in condition_type):
                matching_rules.append(rule)
                break
    
    return matching_rules

def evaluate_rule_conditions(event, rule):
    """
    Enhanced rule evaluation that considers event significance
    """
    from hyperwatch.alerts.triggers import evaluate_conditions
    
    conditions = rule.get("conditions", [])
    if not conditions:
        return False
    
    # Special handling for OR conditions (multiple conditions in same rule)
    matched_conditions = evaluate_conditions(event, conditions)
    
    # For rules with multiple conditions, we use OR logic by default
    # (at least one condition must match)
    return len(matched_conditions) > 0

def create_alert_from_rule(event, rule):
    """Enhanced alert creation with better error handling"""
    try:
        message_func = rule.get("message")
        if callable(message_func):
            message = message_func(event)
        else:
            # Fallback message format
            method = event.get('method', event.get('action', 'Activity'))
            coin = event.get('coin', 'Unknown')
            if event.get('usd_formatted'):
                message = f"📊 {method} | {coin} | ${event.get('usd_formatted')}"
            else:
                message = f"📊 {method} | {coin}"
        
        # Determine priority based on USD value if not set
        priority = rule.get("priority", "medium")
        usd_value = event.get("usd_value", 0)
        
        if usd_value >= 10_000_000:
            priority = "emergency"
        elif usd_value >= 1_000_000:
            priority = "critical"
        elif usd_value >= 100_000:
            priority = "high"
        
        return {
            "rule_id": rule.get("id"),
            "rule_name": rule.get("name"),
            "message": message,
            "channels": rule.get("channels", ["telegram"]),
            "priority": priority,
            "wallet": event.get("wallet"),
            "coin": event.get("coin"),
            "timestamp": event.get("timestamp"),
            "event_type": event.get("type"),
            "usd_value": event.get("usd_value"),
            "is_significant": event.get("is_significant", False)
        }
    except Exception as e:
        return {
            "rule_id": rule.get("id"),
            "rule_name": rule.get("name"),
            "message": f"Error creating alert: {str(e)}",
            "channels": ["telegram"],
            "priority": "low",
            "wallet": event.get("wallet"),
            "error": True
        }