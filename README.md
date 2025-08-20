# HyperWatch

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)  
[![PyPI version](https://badge.fury.io/py/hyperwatch.svg)](https://badge.fury.io/py/hyperwatch)  
[![CI/CD](https://github.com/Mordred491/HyperWatch/actions/workflows/python-package.yml/badge.svg)](https://github.com/Mordred491/HyperWatch/actions)

HyperWatch is a **real-time monitoring and alert system** for Hyperliquid wallets and cryptocurrency market data. It tracks wallet events, trades, and vault activity, providing **multi-channel notifications** while maintaining high reliability with automatic WebSocket health monitoring and event deduplication.

---

## Features

- 📈 Real-time wallet and market event monitoring  
- 🔔 Multi-channel notifications: Discord, Telegram, Email, Webhook  
- ⚙️ Configurable alert rules and condition-based triggers  
- 💾 Event deduplication and rate limiting  
- 🧪 Backtesting support for historical event simulation  
- 💚 WebSocket health checks with automatic reconnects  
- 🛠 Modular design for developer-friendly customization  

---

## Installation

```bash
pip install hyperwatch
```

## Configuration

1. Copy the example configuration:
```bash
cp config/notification.yaml.example config/notification.yaml
```

2. Edit `config/notification.yaml` with your credentials:
```yaml
discord:
  webhook_url: "your_discord_webhook_here"

telegram:
  bot_token: "your_bot_token_here"
  chat_id: "your_chat_id_here"

email:
  smtp_server: "smtp.example.com"
  smtp_port: 587
  username: "your_email@example.com"
  password: "your_password_here"

webhooks:
  - url: "https://your-webhook-endpoint.com"
```

3. Configure coin mappings in `coin_mappings.json`:
```json
{
  "BTC": "bitcoin",
  "ETH": "ethereum", 
  "SOL": "solana"
}
```

4. Configure wallets to monitor in `hyperwatch/core/config.py`:
```python
WATCHED_WALLETS = [
    "0x1234abcd5678efgh",
    "0x5678ijkl9012mnop"
]
```

## Usage

```python
from hyperwatch import HyperWatch

# Initialize monitor with configuration
monitor = HyperWatch(config_path="config/notification.yaml")

# Start monitoring
monitor.run()
```

Use `examples/headless/` for advanced usage scenarios, including multiple wallets and custom alert rules.

## Project Structure

```
hyperwatch/core/      # WebSocket client, event parsing, wallet tracking
hyperwatch/alerts/    # Alert engine, rules, conditions, rate limiting
hyperwatch/notifications/  # Notification dispatchers
tests/                # Unit tests
config/               # Configuration files
```

## Event Flow Architecture

```
+-------------------+
| HyperCore WebSocket |
+-------------------+
          |
          v
+-------------------+
|   Event Parser    |
|  (normalize &     |
|   validate data)  |
+-------------------+
          |
          v  
+-------------------+
|   Alert Engine    |
| (evaluate rules & |
|  trigger alerts)  |
+-------------------+
          |
          v
+-------------------+
| Notifications     |
| Dispatcher        |
| (Discord, Telegram,
| Email, Webhook)   |
+-------------------+
          |
          v
+-------------------+
| Rate Limiter &    |
| Deduplicator      |
+-------------------+
```

## Development Setup

```bash
git clone https://github.com/Mordred491/HyperWatch.git
cd HyperWatch
pip install -e .[dev]
pre-commit install
```

Run unit tests:
```bash
pytest tests/
```

## CI/CD Pipeline

GitHub Actions automate:
- Testing on Python 3.8+
- PyPI package publishing
- Security scanning (CodeQL)
- Dependency updates

## License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.
