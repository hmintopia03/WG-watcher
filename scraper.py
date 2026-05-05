from dataclasses import dataclass
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


@dataclass(frozen=True)
class Listing:
    listing_id: str
    title: str
    url: str
    text: str = ""


class WGListingScraper:
    def __init__(self, search_url: str) -> None:
        self.search_url = search_url
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "WG-Gesucht-Watcher/0.1 "
                    "(personal listing watcher; polite interval; contact via Telegram)"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
            }
        )

    def fetch_listings(self) -> list[Listing]:
        response = self.session.get(self.search_url, timeout=20)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        listings: dict[str, Listing] = {}

        for link in soup.select("a[href]"):
            href = link.get("href", "")
            listing_id = self._extract_listing_id(href)
            if not listing_id:
                continue

            url = urljoin(self.search_url, href)
            title = self._extract_title(link)
            text = self._extract_listing_text(link)
            listings[listing_id] = Listing(listing_id=listing_id, title=title, url=url, text=text)

        return list(listings.values())

    def fetch_listing_details(self, listing: Listing) -> Listing:
        response = self.session.get(listing.url, timeout=20)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        detail_text = " ".join(soup.get_text(" ", strip=True).split())
        combined_text = f"{listing.text} {detail_text}".strip()
        return Listing(
            listing_id=listing.listing_id,
            title=listing.title,
            url=listing.url,
            text=combined_text,
        )

    def _extract_listing_id(self, href: str) -> str | None:
        if ".html" not in href:
            return None

        filename = href.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]
        if not filename.endswith(".html"):
            return None

        parts = filename.removesuffix(".html").split(".")
        if not parts:
            return None

        listing_id = parts[-1]
        return listing_id if listing_id.isdigit() else None

    def _extract_title(self, link) -> str:
        title = " ".join(link.get_text(" ", strip=True).split())
        if title:
            return title

        aria_label = link.get("aria-label")
        if aria_label:
            return " ".join(aria_label.split())

        return "New WG-Gesucht listing"

    def _extract_listing_text(self, link) -> str:
        container = link.find_parent(["article", "li", "div"])
        if container:
            return " ".join(container.get_text(" ", strip=True).split())
        return " ".join(link.get_text(" ", strip=True).split())
