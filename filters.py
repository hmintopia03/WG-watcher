import re
from dataclasses import dataclass, field

from scraper import Listing


MIN_PRICE = 500
MAX_PRICE = 850
PREFERRED_AREAS = [
    "prenzlauer berg",
    "mitte",
    "moabit",
    "schoeneberg",
    "schoneberg",
]
MAX_PREFERRED_WG_SIZE = 3
MIN_ROOM_SIZE_HARD = 13
MIN_PREFERRED_ROOM_SIZE = 18

ANMELDUNG_POSITIVE_PATTERNS = [
    r"\banmeldung\s+(?:ist\s+)?(?:moeglich|possible|ja|yes)\b",
    "\\banmeldung\\s+(?:ist\\s+)?(?:m\\u00f6glich)\\b",
    r"\bmit\s+anmeldung\b",
]
ANMELDUNG_NEGATIVE_PATTERNS = [
    r"\banmeldung\s+(?:ist\s+)?(?:nicht|not|no|nein|keine|unmoeglich)\b",
    "\\banmeldung\\s+(?:ist\\s+)?(?:unm\\u00f6glich)\\b",
    r"\bohne\s+anmeldung\b",
    r"\bno\s+registration\b",
]
FEMALE_ONLY_PATTERNS = [
    r"\bnur\s+frauen\b",
    r"\bnur\s+weiblich\b",
    "\\bnur\\s+f\\u00fcr\\s+frauen\\b",
    r"\bnur\s+fuer\s+frauen\b",
    r"\bfrauen\s*-?\s*wg\b",
    r"\bweibliche\s+person\b",
]
MALE_ONLY_PATTERNS = [
    "\\bnur\\s+m\\u00e4nner\\b",
    r"\bnur\s+maenner\b",
    "\\bnur\\s+m\\u00e4nnlich\\b",
    r"\bnur\s+maennlich\b",
    "\\bm\\u00e4nner\\s*-?\\s*wg\\b",
    r"\bmaenner\s*-?\s*wg\b",
    "\\bm\\u00e4nnliche\\s+person\\b",
    r"\bmaennliche\s+person\b",
]
SCAM_PATTERNS = [
    r"\bdeposit\s+before\s+(?:viewing|visit)\b",
    r"\bkaution\s+vor\s+besichtigung\b",
    r"\bwestern\s+union\b",
    r"\bcash\s+only\b",
    r"\bnur\s+barzahlung\b",
    r"\bpayment\s+before\s+contract\b",
    r"\bvorauszahlung\b.{0,40}\b(?:besichtigung|viewing|visit)\b",
]
EXCHANGE_ONLY_PATTERNS = [
    r"\btauschwohnung\b",
    r"\bwohnungstausch\b",
    r"\bnur\s+tausch\b",
]
STUDENT_ONLY_PATTERNS = [
    r"\bstudent\s+only\b",
    r"\bstudents\s+only\b",
    r"\bonly\s+students\b",
    r"\bfor\s+students\s+only\b",
    r"\bnur\s+studenten\b",
    r"\bnur\s+studentinnen\b",
    r"\bnur\s+fuer\s+studenten\b",
    r"\bnur\s+fuer\s+studentinnen\b",
    r"\bstudenten\s*-?\s*wg\b",
    r"\bstudentinnen\s*-?\s*wg\b",
    r"\bnur\s+immatrikulierte\b",
    r"\bnur\s+mit\s+immatrikulationsbescheinigung\b",
    r"\bnur\s+eingeschriebene\s+studenten\b",
]
RECENT_PATTERNS = [
    r"\bheute\b",
    r"\btoday\b",
    r"\bgerade\s+online\b",
    r"\bvor\s+\d+\s+(?:minute|minuten|std|stunde|stunden)\b",
    r"\b\d+\s+(?:minute|minutes|hour|hours)\s+ago\b",
]
MANY_RESTRICTIONS_PATTERNS = [
    r"\bnicht\s+rauchen\b",
    r"\bkeine\s+haustiere\b",
    r"\bkeine\s+paare\b",
    r"\bnur\s+student",
    r"\bwochenendheimfahrer\b",
    r"\bzweck\s*-?\s*wg\b",
]
UNCLEAR_RENTAL_PERIOD_PATTERNS = [
    r"\bzwischenmiete\b",
    r"\bbefristet\b",
    r"\btemporary\b",
    r"\bsublet\b",
]


@dataclass(frozen=True)
class ListingScore:
    score: int
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    excluded: bool = False
    exclude_reason: str | None = None


@dataclass(frozen=True)
class ListingFacts:
    price: int | None = None
    area: str | None = None
    wg_size: int | None = None
    room_size: float | None = None
    move_in_date: str | None = None


def score_listing(listing: Listing) -> ListingScore:
    text = _listing_text(listing)
    facts = extract_listing_facts(listing)
    score = 0
    reasons: list[str] = []
    warnings: list[str] = []

    exclude_reason = _get_exclude_reason(text, facts)
    if exclude_reason:
        return ListingScore(
            score=score,
            reasons=reasons,
            warnings=warnings,
            excluded=True,
            exclude_reason=exclude_reason,
        )

    if _matches_any(text, ANMELDUNG_POSITIVE_PATTERNS):
        score += 5
        reasons.append("Anmeldung clearly possible")
    else:
        score -= 2
        warnings.append("Anmeldung not mentioned")

    if facts.area and _is_preferred_area(facts.area):
        score += 3
        reasons.append(f"Preferred area: {facts.area}")

    if facts.price is not None:
        if facts.price <= 650:
            score += 3
            reasons.append(f"Strong price fit: {facts.price} EUR")
        elif facts.price <= 750:
            score += 2
            reasons.append(f"Good price fit: {facts.price} EUR")
        else:
            score += 1
            reasons.append(f"Budget-compatible price: {facts.price} EUR")

    if facts.wg_size is not None:
        if facts.wg_size <= 2:
            score += 3
            reasons.append(f"Small WG: {facts.wg_size}er WG")
        elif facts.wg_size == MAX_PREFERRED_WG_SIZE:
            score += 2
            reasons.append("Preferred WG size: 3er WG")
        elif facts.wg_size == 4:
            score -= 3
            warnings.append("4er WG")
        else:
            score -= 6
            warnings.append(f"Large WG: {facts.wg_size}er WG")

    if facts.room_size is not None:
        if facts.room_size >= 22:
            score += 3
            reasons.append(f"Large room: {facts.room_size:g}m2")
        elif facts.room_size >= MIN_PREFERRED_ROOM_SIZE:
            score += 2
            reasons.append(f"Room size fits: {facts.room_size:g}m2")
    else:
        warnings.append("room size unknown")

    if _matches_any(text, FEMALE_ONLY_PATTERNS):
        score += 1
        reasons.append("Female-only listing is compatible")

    if _matches_any(text, RECENT_PATTERNS):
        score += 3
        reasons.append("Listing appears very recent")

    if _is_description_too_short(listing):
        score -= 2
        warnings.append("Description is too short")

    if _has_unusually_high_deposit(text, facts.price):
        warnings.append("Deposit is unusually high")

    if _matches_any(text, UNCLEAR_RENTAL_PERIOD_PATTERNS) and not facts.move_in_date:
        warnings.append("Listing has unclear rental period")

    if _count_matches(text, MANY_RESTRICTIONS_PATTERNS) >= 3:
        warnings.append("Listing mentions many restrictions")

    return ListingScore(
        score=score,
        reasons=reasons,
        warnings=warnings,
        excluded=False,
        exclude_reason=None,
    )


def extract_listing_facts(listing: Listing) -> ListingFacts:
    text = _listing_text(listing)
    return ListingFacts(
        price=_extract_price(text),
        area=_extract_area(text),
        wg_size=_extract_wg_size(text),
        room_size=_extract_room_size(text),
        move_in_date=_extract_move_in_date(text),
    )


def _get_exclude_reason(text: str, facts: ListingFacts) -> str | None:
    if facts.price is not None and facts.price < MIN_PRICE:
        return f"Price below budget floor ({facts.price} EUR)"
    if facts.price is not None and facts.price > MAX_PRICE:
        return f"Price above budget ceiling ({facts.price} EUR)"
    if facts.room_size is not None and facts.room_size < MIN_ROOM_SIZE_HARD:
        return "room_too_small"
    if _matches_any(text, ANMELDUNG_NEGATIVE_PATTERNS):
        return "Anmeldung is explicitly not possible"
    male_only = _first_match(text, MALE_ONLY_PATTERNS)
    if male_only:
        return f"Male-only listing ({male_only})"
    scam_signal = _first_match(text, SCAM_PATTERNS)
    if scam_signal:
        return f"Suspicious payment wording ({scam_signal})"
    exchange_signal = _first_match(text, EXCHANGE_ONLY_PATTERNS)
    if exchange_signal:
        return f"Exchange-only listing ({exchange_signal})"
    if _matches_any(text, STUDENT_ONLY_PATTERNS):
        return "student_only"
    return None


def _listing_text(listing: Listing) -> str:
    return _normalize_text(f"{listing.title} {listing.text}")


def _normalize_text(text: str) -> str:
    replacements = {
        "\u20ac": " eur ",
        "m\u00b2": "m2",
        "\u00e4": "ae",
        "\u00f6": "oe",
        "\u00fc": "ue",
        "\u00df": "ss",
    }
    normalized = text.lower()
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
    return " ".join(normalized.split())


def _matches_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def _first_match(text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)
    return None


def _count_matches(text: str, patterns: list[str]) -> int:
    return sum(1 for pattern in patterns if re.search(pattern, text, re.IGNORECASE))


def _extract_price(text: str) -> int | None:
    patterns = [
        r"(\d{3,4})\s*(?:eur|euro)\s*(?:warm|warmmiete|inkl)",
        r"(?:warm|warmmiete|gesamtmiete|miete)\D{0,20}(\d{3,4})\s*(?:eur|euro)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _extract_area(text: str) -> str | None:
    for area in PREFERRED_AREAS:
        if area in text:
            return area.title()

    berlin_area = re.search(r"\bberlin[-\s]+([a-z][a-z\s-]{2,30})\b", text, re.IGNORECASE)
    if berlin_area:
        return berlin_area.group(1).strip(" -").title()

    return None


def _is_preferred_area(area: str) -> bool:
    normalized_area = _normalize_text(area)
    return any(preferred in normalized_area for preferred in PREFERRED_AREAS)


def _extract_wg_size(text: str) -> int | None:
    patterns = [
        r"(\d+)\s*(?:er|personen|person|people|mitbewohner|bewohner)\s*-?\s*wg",
        r"wg\s*(?:mit|for|fuer)?\s*(\d+)\s*(?:personen|people|mitbewohner|bewohner)?",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _extract_room_size(text: str) -> float | None:
    match = re.search(r"(\d{1,2}(?:[,.]\d)?)\s*(?:m2|qm)", text, re.IGNORECASE)
    if not match:
        return None
    return float(match.group(1).replace(",", "."))


def _extract_move_in_date(text: str) -> str | None:
    patterns = [
        r"(?:ab|frei\s+ab|available\s+from)\s+(\d{1,2}[./]\d{1,2}(?:[./]\d{2,4})?)",
        r"(?:einzug|move-?in)\D{0,20}(\d{1,2}[./]\d{1,2}(?:[./]\d{2,4})?)",
        r"(?:ab|from)\s+([a-z]+\.?\s+\d{4})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def _is_description_too_short(listing: Listing) -> bool:
    return len(_normalize_text(listing.text).split()) < 35


def _has_unusually_high_deposit(text: str, price: int | None) -> bool:
    deposit = _extract_deposit(text)
    if deposit is None:
        return False
    if price is None:
        return deposit >= 2500
    return deposit > price * 3


def _extract_deposit(text: str) -> int | None:
    patterns = [
        r"(?:kaution|deposit)\D{0,20}(\d{3,5})\s*(?:eur|euro)?",
        r"(\d{3,5})\s*(?:eur|euro)\s*(?:kaution|deposit)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None
