# ResearchBot

A Telegram research assistant that turns questions into evidence-backed, traceable answers.

## Current Status

Working prototype with modular architecture. See `ARCHITECTURE.md` for details.

## Installation

1. Clone the repository.
2. Create a virtual environment: `python -m venv venv`
3. Activate it: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Linux/Mac)
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and fill in your Telegram bot token and Gemini API key.
6. Run the bot: `python bot.py`

## Usage

- `/start` – welcome
- `/research <topic>` – start research
- `/history` – view past research
- `/get <id>` – retrieve a specific answer
- `/cancel` – cancel an active research

## License

MIT (see LICENSE file)