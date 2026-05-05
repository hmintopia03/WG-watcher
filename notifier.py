import html

import requests

from filters import ListingScore, extract_listing_facts
from scraper import Listing


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    def send_listing(self, listing: Listing, listing_score: ListingScore) -> None:
        facts = extract_listing_facts(listing)
        reasons = _format_lines("Reasons", listing_score.reasons)
        warnings = _format_lines("Warnings", listing_score.warnings)
        exclusion = ""
        if listing_score.excluded and listing_score.exclude_reason:
            exclusion = f"\n<b>Exclusion:</b> {html.escape(listing_score.exclude_reason)}"

        message = (
            "<b>New WG-Gesucht listing</b>\n"
            f"<b>Title:</b> {html.escape(listing.title)}\n"
            f"<b>Price:</b> {_format_value(_format_price(facts.price))}\n"
            f"<b>Area:</b> {_format_value(facts.area)}\n"
            f"<b>WG size:</b> {_format_value(_format_wg_size(facts.wg_size))}\n"
            f"<b>Room size:</b> {_format_value(_format_room_size(facts.room_size))}\n"
            f"<b>Move-in:</b> {_format_value(facts.move_in_date)}\n"
            f"<b>Score:</b> {listing_score.score}"
            f"{reasons}"
            f"{warnings}"
            f"{exclusion}\n\n"
            f"{html.escape(listing.url)}"
        )
        response = requests.post(
            self.api_url,
            data={
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            },
            timeout=20,
        )
        if not response.ok:
            raise RuntimeError(f"Telegram notification failed with HTTP {response.status_code}")


def _format_lines(label: str, lines: list[str]) -> str:
    if not lines:
        return ""
    escaped_lines = "\n".join(f"- {html.escape(line)}" for line in lines)
    return f"\n\n<b>{label}:</b>\n{escaped_lines}"


def _format_value(value: str | None) -> str:
    return html.escape(value or "Unknown")


def _format_price(price: int | None) -> str | None:
    if price is None:
        return None
    return f"{price} EUR warm"


def _format_wg_size(wg_size: int | None) -> str | None:
    if wg_size is None:
        return None
    return f"{wg_size}er WG"


def _format_room_size(room_size: float | None) -> str | None:
    if room_size is None:
        return None
    return f"{room_size:g}m2"
