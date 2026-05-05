import logging
import os
import time

from dotenv import load_dotenv

from db import SeenListingsDB
from filters import score_listing
from notifier import TelegramNotifier
from scraper import WGListingScraper


def get_interval_seconds() -> int:
    interval_minutes = os.getenv("CHECK_INTERVAL_MINUTES", "5")
    try:
        minutes = max(1, int(interval_minutes))
    except ValueError:
        logging.warning("Invalid CHECK_INTERVAL_MINUTES=%r, using 5 minutes", interval_minutes)
        minutes = 5
    return minutes * 60


def get_score_threshold() -> int:
    threshold = os.getenv("SCORE_THRESHOLD", "3")
    try:
        return int(threshold)
    except ValueError:
        logging.warning("Invalid SCORE_THRESHOLD=%r, using 3", threshold)
        return 3


def run_once(scraper: WGListingScraper, db: SeenListingsDB, notifier: TelegramNotifier) -> None:
    listings = scraper.fetch_listings()
    new_listings = [listing for listing in listings if not db.has_seen(listing.listing_id)]
    score_threshold = get_score_threshold()
    debug_filters = os.getenv("FILTER_DEBUG_MODE", "false").lower() == "true"

    if not new_listings:
        logging.info("No new listings found")
        return

    logging.info("Found %s new listing(s)", len(new_listings))

    for listing in new_listings:
        try:
            detailed_listing = scraper.fetch_listing_details(listing)
            listing_score = score_listing(detailed_listing)
            if listing_score.excluded:
                if debug_filters:
                    logging.info(
                        "Skipping excluded listing %s: %s",
                        listing.listing_id,
                        listing_score.exclude_reason,
                    )
                    notifier.send_listing(detailed_listing, listing_score)
                else:
                    logging.info("Skipping excluded listing %s", listing.listing_id)
                db.mark_seen(listing.listing_id)
                continue

            if listing_score.score < score_threshold:
                logging.info(
                    "Skipping listing %s below score threshold (%s < %s)",
                    listing.listing_id,
                    listing_score.score,
                    score_threshold,
                )
                db.mark_seen(listing.listing_id)
                continue

            notifier.send_listing(detailed_listing, listing_score)
            db.mark_seen(listing.listing_id)
        except Exception:
            logging.exception("Failed to process listing %s", listing.listing_id)


def main() -> None:
    load_dotenv()
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(message)s",
    )

    search_url = os.getenv("WG_SEARCH_URL")
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not search_url:
        raise RuntimeError("WG_SEARCH_URL is required")
    if not telegram_token or not telegram_chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required")

    interval_seconds = get_interval_seconds()
    db_path = os.getenv("SQLITE_DB_PATH", "seen_listings.sqlite3")

    scraper = WGListingScraper(search_url)
    notifier = TelegramNotifier(telegram_token, telegram_chat_id)

    with SeenListingsDB(db_path) as db:
        logging.info("Starting WG-Gesucht watcher with %s minute interval", interval_seconds // 60)
        while True:
            try:
                run_once(scraper, db, notifier)
            except KeyboardInterrupt:
                logging.info("Stopping watcher")
                break
            except Exception:
                logging.exception("Watcher cycle failed")

            time.sleep(interval_seconds)


if __name__ == "__main__":
    main()
