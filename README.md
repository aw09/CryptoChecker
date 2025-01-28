# Crypto Checker Bot

A Telegram bot that monitors Gate.io account balances using Streamlit for configuration management.

## Features
- Monitor multiple Gate.io accounts simultaneously
- Secure configuration management using Streamlit secrets
- Telegram bot interface for checking balances
- User authentication via whitelist

## Setup Instructions

1. **Clone the repository**
```bash
git clone <repository-url>
cd CryptoChecker
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure Secrets**
- Create a `.streamlit` folder in the project directory if it doesn't exist
- Copy `secret.toml.example` to `.streamlit/secrets.toml`
```bash
mkdir -p .streamlit
cp secret.toml.example .streamlit/secrets.toml
```
- Edit `.streamlit/secrets.toml` with your:
  - Telegram bot token
  - Gate.io API keys
  - Authorized usernames/user IDs
  - Account names

4. **Run the Application**
```bash
streamlit run streamlit_app.py
```

## Usage

### Telegram Commands
- `/info` - Get current balance for all accounts

### Security Features
- Only whitelisted users can interact with the bot
- API keys are stored securely in Streamlit secrets
- No data is stored locally

## Configuration Example

```toml
[telegram]
token = "your_bot_token"

[whitelist]
usernames = [
    "telegram_username",
    "telegram_user_id"
]

[gate_io.account1]
api_key = "gate_api_key"
api_secret = "gate_api_secret"
name = "Main Account"
```

## Requirements
- Python 3.8+
- Streamlit
- python-telegram-bot
- gate-api

## Security Notes
- Never commit your `secrets.toml` file
- Keep your API keys secure
- Only share bot access with trusted users

## Troubleshooting
1. If the bot doesn't respond:
   - Check if your Telegram token is correct
   - Verify that your username is in the whitelist

2. If balances don't show:
   - Verify Gate.io API keys
   - Check account permissions on Gate.io

## Contributing
Feel free to submit issues and pull requests.
