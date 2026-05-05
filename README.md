# WG-Gesucht Listing Watcher

A minimal Python MVP that watches a WG-Gesucht search result URL, scores listings against simple preferences, stores seen listing IDs in SQLite, and sends matching new listings to Telegram.

This tool only watches listings and sends notifications. It does not auto-apply, auto-message landlords, or perform any automated contact actions.

## Setup

1. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Create your environment file:

   ```bash
   copy .env.example .env
   ```

4. Edit `.env`:

   ```env
   WG_SEARCH_URL=https://www.wg-gesucht.de/wg-zimmer-in-Berlin.8.0.1.0.html
   TELEGRAM_BOT_TOKEN=your-telegram-bot-token
   TELEGRAM_CHAT_ID=your-telegram-chat-id
   CHECK_INTERVAL_MINUTES=5
   SCORE_THRESHOLD=3
   SQLITE_DB_PATH=seen_listings.sqlite3
   LOG_LEVEL=INFO
   ```

## Run

```bash
python main.py
```

Stop with `Ctrl+C`.

## Configuration

- `WG_SEARCH_URL`: WG-Gesucht search result URL to check.
- `TELEGRAM_BOT_TOKEN`: Telegram bot token from BotFather. This value is never logged by the app.
- `TELEGRAM_CHAT_ID`: Telegram chat ID that should receive notifications.
- `CHECK_INTERVAL_MINUTES`: Polling interval. Values below `1` are treated as `1`.
- `SCORE_THRESHOLD`: Minimum listing score required for Telegram notification.
- `SQLITE_DB_PATH`: Path to the SQLite database file.
- `LOG_LEVEL`: Python logging level, for example `INFO` or `DEBUG`.

## Filtering and scoring

Rules live as editable constants at the top of `filters.py`.

Current preferences:

- Budget: 500 to 850 EUR warm rent.
- Preferred areas: Prenzlauer Berg, Mitte, Moabit, Schoeneberg.
- Strongly prefer Anmeldung possible.
- Prefer WG size up to 3 people.
- Prefer rooms 18m2 or larger, with an extra boost at 22m2.
- Prefer recent listings and clear descriptions.
- Female-only listings are compatible and allowed.
- Male-only listings are excluded.
- Exclude listings that clearly say Anmeldung is not possible.
- Exclude listings with suspicious payment wording such as deposit before viewing, cash only, Western Union, payment before contract, or Vorauszahlung before viewing.
- Exclude exchange-only listings such as Tauschwohnung, Wohnungstausch, or nur Tausch.

Only listings with `score >= SCORE_THRESHOLD` are sent. The default threshold is `3`.

## Notes

- The scraper uses polite request headers and a configurable interval.
- Listing IDs are extracted from WG-Gesucht listing URLs ending in `.html`.
- Detail pages are fetched only for newly discovered listings before scoring.
- A listing is marked as seen only after the Telegram notification succeeds.
- Excluded listings are marked as seen so they do not trigger repeated skip logs.
