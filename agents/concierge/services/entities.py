"""Small, dependency-free entity extraction for Concierge messages."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional


_ROOM_TYPES = {
    "single": "single",
    "double": "double",
    "twin": "twin",
    "suite": "suite",
    "deluxe": "deluxe",
    "family": "family",
    "king": "king",
    "queen": "queen",
}
_MONTHS = {name.lower(): number for number, name in enumerate(
    ("January", "February", "March", "April", "May", "June",
     "July", "August", "September", "October", "November", "December"), 1
)}


def _parse_date(value: str, year: Optional[int] = None) -> Optional[str]:
    value = value.strip().replace("/", "-").replace(".", "-")
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m-%d-%Y", "%d-%m", "%m-%d"):
        try:
            parsed = datetime.strptime(value, fmt).date()
            if "%Y" not in fmt:
                parsed = parsed.replace(year=year or date.today().year)
            return parsed.isoformat()
        except ValueError:
            continue
    return None


def _extract_dates(text: str) -> List[str]:
    found: List[str] = []
    for match in re.finditer(r"\b\d{4}[-/.]\d{1,2}[-/.]\d{1,2}\b|\b\d{1,2}[-/.]\d{1,2}(?:[-/.]\d{2,4})?\b", text):
        parsed = _parse_date(match.group())
        if parsed and parsed not in found:
            found.append(parsed)

    month_pattern = r"\b(" + "|".join(_MONTHS) + r")\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?\b"
    for match in re.finditer(month_pattern, text, re.IGNORECASE):
        month, day, year = match.groups()
        parsed = _parse_date(
            f"{int(day):02d}-{_MONTHS[month.lower()]:02d}-{year or date.today().year}"
        )
        if parsed and parsed not in found:
            found.append(parsed)

    lowered = text.lower()
    today = date.today()
    if "tomorrow" in lowered:
        found.append((today + timedelta(days=1)).isoformat())
    if "today" in lowered:
        found.append(today.isoformat())
    if "this weekend" in lowered:
        saturday = today + timedelta(days=(5 - today.weekday()) % 7)
        found.extend([(saturday + timedelta(days=i)).isoformat() for i in range(2)])
    return found[:2]


def extract_entities(message: str) -> Dict[str, Any]:
    """Extract booking entities without pretending to be a general NER model.

    Dates are returned as ISO strings, guests as an integer, and room_type as
    a normalized domain value. Missing values are omitted.
    """
    if not message or not isinstance(message, str):
        return {}
    lowered = message.lower()
    result: Dict[str, Any] = {}
    dates = _extract_dates(message)
    if dates:
        result["check_in_date"] = dates[0]
    if len(dates) > 1:
        result["check_out_date"] = dates[1]

    guest_match = re.search(
        r"\b(?:for|party\s+of|with)\s+(\d+)\s+(?:adult\s+)?(?:guests?|people|persons?)\b"
        r"|\b(\d+)\s+(?:adult\s+)?(?:guests?|people|persons?)\b"
        r"|\b(\d+)\s+adults?\b",
        lowered,
    )
    if guest_match:
        result["guests"] = int(next(group for group in guest_match.groups() if group))

    for alias, room_type in _ROOM_TYPES.items():
        if re.search(r"\b" + re.escape(alias) + r"\b(?:\s+room)?", lowered):
            result["room_type"] = room_type
            break
    return result
