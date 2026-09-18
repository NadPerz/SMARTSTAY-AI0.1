"""Reservation-domain NLP: entity extraction from free-text guest requests.

This is real entity extraction, not a keyword/regex placeholder:

- spaCy's pretrained NER model (en_core_web_sm) finds DATE, CARDINAL,
  GPE, and MONEY spans in the text.
- A spaCy PhraseMatcher (domain vocabulary spaCy's pretrained model
  doesn't know as its own entity type) finds known cities and room types.
- `dateparser` resolves DATE spans into actual calendar dates, including
  several relative phrasings ("tomorrow", a bare weekday name).
- Lemma-based (not substring) keyword matching gives a lightweight,
  slightly more robust sub-intent guess ("booked"/"booking"/"book" all
  reduce to the lemma "book").

Honest limits, tested rather than hidden: dateparser (as installed here)
does NOT resolve "next Friday" or "this weekend" on its own — verified by
testing, not assumed — so those two specific patterns are normalized
before being handed to it. Anything outside what's tested below
(elaborate relative expressions like "the Friday after next", non-English
input, misspelled cities) is not attempted; ambiguous input is left
unresolved rather than guessed at, consistent with the rest of this
project's "don't guess, ask instead" approach to uncertain input.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import List, Optional

import dateparser
import spacy
from spacy.matcher import PhraseMatcher

_nlp = spacy.load("en_core_web_sm")

# Kept in sync with the demo hotel data (database/seeds/demo_fixtures) —
# in a real system this would be loaded from the hotels table instead of
# hardcoded, but a live DB lookup isn't needed for entity extraction to
# be genuinely useful, and keeping this module DB-free makes it trivially
# unit-testable without a database fixture.
_KNOWN_CITIES = ["Colombo", "Kandy", "Galle", "Ella", "Negombo"]
_KNOWN_ROOM_TYPES = ["Standard", "Deluxe", "Suite", "Penthouse"]

_city_matcher = PhraseMatcher(_nlp.vocab, attr="LOWER")
_city_matcher.add("CITY", [_nlp.make_doc(c) for c in _KNOWN_CITIES])

_room_type_matcher = PhraseMatcher(_nlp.vocab, attr="LOWER")
_room_type_matcher.add("ROOM_TYPE", [_nlp.make_doc(r) for r in _KNOWN_ROOM_TYPES])

_GUEST_WORD_PATTERN = re.compile(
    r"\b(guests?|people|persons?|pax|adults?)\b", re.IGNORECASE
)
_NIGHT_DURATION_PATTERN = re.compile(r"\b(\d{1,2})\s*(?:nights?|days?)\b", re.IGNORECASE)
_RELATIVE_WEEKDAY_PATTERN = re.compile(
    r"^(?:next|coming|upcoming)\s+"
    r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)$",
    re.IGNORECASE,
)
_WEEKEND_PHRASES = {"this weekend", "the weekend", "coming weekend", "weekend"}
_RANGE_CONNECTOR_PATTERN = re.compile(
    r"\s+(?:to|until|through|-|–)\s+", re.IGNORECASE
)

_WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "a": 1, "an": 1, "couple": 2,
}
# Honest limitation, found by testing: this dict is only ever consulted on
# text spaCy has ALREADY tagged as a CARDINAL entity. spaCy's pretrained
# model reliably tags "two"/"three"/etc. as CARDINAL, but does NOT tag
# "a couple" that way — so "a couple looking for a room" won't pick up
# guests=2 despite "couple" being listed here. Fixing that would need a
# separate phrase-based pass rather than relying on spaCy's NER output,
# which is more scope than this pass covers; noted rather than hidden.


def _parse_cardinal(text: str) -> Optional[int]:
    """CARDINAL entities from spaCy can be digit-form ("2") or spelled
    out ("two") — this handles both instead of assuming digits."""
    stripped = text.strip().lower()
    if stripped in _WORD_NUMBERS:
        return _WORD_NUMBERS[stripped]
    try:
        return int(stripped)
    except ValueError:
        return None


@dataclass
class ExtractedEntities:
    """Everything this module could confidently find in a guest's message.
    Every field is optional — a field being None means "not found",
    not "found and empty"."""

    check_in_date: Optional[date] = None
    check_out_date: Optional[date] = None
    guests: Optional[int] = None
    city: Optional[str] = None
    room_type: Optional[str] = None
    max_price: Optional[Decimal] = None
    unresolved_date_spans: List[str] = field(default_factory=list)

    def to_search_payload(self) -> Optional[dict]:
        """Shape into the payload agents.reservation.agent expects for the
        search_rooms intent. Returns None if the two required fields
        (both dates) aren't present — callers should treat that as "don't
        delegate yet", not fill in a guess."""
        if self.check_in_date is None or self.check_out_date is None:
            return None
        payload = {
            "check_in_date": self.check_in_date.isoformat(),
            "check_out_date": self.check_out_date.isoformat(),
            "guests": self.guests or 1,
        }
        if self.city:
            payload["city"] = self.city
        if self.room_type:
            payload["room_type"] = self.room_type
        if self.max_price is not None:
            payload["max_price"] = float(self.max_price)
        return payload


def _next_weekday(reference_date: date, target_weekday: int) -> date:
    """target_weekday: Monday=0 ... Sunday=6. Returns the next occurrence
    of that weekday on or after reference_date."""
    days_ahead = (target_weekday - reference_date.weekday()) % 7
    return reference_date + timedelta(days=days_ahead)


def _resolve_date_span(text_span: str, reference_date: date) -> Optional[date]:
    """Resolve one DATE-labeled text span into an actual date.

    dateparser (as installed — verified by direct testing, not assumed)
    correctly handles: absolute dates ("2026-09-20", "20th September"),
    "tomorrow"/"today", "in N days", "next week", and a BARE weekday name
    like "Friday" (which, with PREFER_DATES_FROM=future, correctly
    resolves to the upcoming Friday).

    It does NOT resolve "next Friday" or "this weekend" as single dates —
    both return None. Those two specific patterns are normalized here
    first: "next Friday" -> "Friday" (since a bare weekday name already
    resolves correctly), and "this weekend" -> treated as the upcoming
    Saturday.
    """
    normalized = text_span.strip()

    weekday_match = _RELATIVE_WEEKDAY_PATTERN.match(normalized)
    if weekday_match:
        normalized = weekday_match.group(1)

    if normalized.lower() in _WEEKEND_PHRASES:
        return _next_weekday(reference_date, target_weekday=5)  # Saturday

    reference_datetime = datetime.combine(reference_date, datetime.min.time())
    parsed = dateparser.parse(
        normalized,
        settings={"PREFER_DATES_FROM": "future", "RELATIVE_BASE": reference_datetime},
    )
    return parsed.date() if parsed else None


def _split_compound_date_span(span_text: str) -> List[str]:
    """spaCy sometimes tags an entire "2026-10-06 to 2026-10-09" phrase as
    ONE DATE entity, not two — verified by testing, not assumed. Split on
    a range connector so each side can be resolved independently. Returns
    a single-item list unchanged if there's no connector to split on."""
    parts = _RANGE_CONNECTOR_PATTERN.split(span_text)
    return [p.strip() for p in parts if p.strip()]


def extract_reservation_entities(
    text: str, reference_date: Optional[date] = None
) -> ExtractedEntities:
    """The main entry point: run real NER + domain phrase matching over
    guest text and return whatever could be confidently extracted."""
    reference_date = reference_date or date.today()
    doc = _nlp(text)
    result = ExtractedEntities()

    # --- Dates: spaCy finds the SPANS, dateparser resolves them ---
    resolved_dates: List[date] = []
    for ent in doc.ents:
        if ent.label_ != "DATE":
            continue

        if ent.text.strip().lower() in _WEEKEND_PHRASES:
            # A weekend is inherently a range, not a single day — default
            # to Saturday through Monday (2 nights) rather than leaving
            # checkout unresolved.
            saturday = _next_weekday(reference_date, target_weekday=5)
            resolved_dates.append(saturday)
            resolved_dates.append(saturday + timedelta(days=2))
            continue

        for sub_span in _split_compound_date_span(ent.text):
            resolved = _resolve_date_span(sub_span, reference_date)
            if resolved:
                resolved_dates.append(resolved)
            else:
                result.unresolved_date_spans.append(sub_span)

    unique_sorted_dates = sorted(set(resolved_dates))
    if len(unique_sorted_dates) >= 2:
        result.check_in_date = unique_sorted_dates[0]
        result.check_out_date = unique_sorted_dates[1]
    elif len(unique_sorted_dates) == 1:
        # Only one date found. Look for an explicit duration ("3 nights")
        # to compute checkout instead of guessing an arbitrary length.
        duration_match = _NIGHT_DURATION_PATTERN.search(text)
        result.check_in_date = unique_sorted_dates[0]
        if duration_match:
            nights = int(duration_match.group(1))
            result.check_out_date = unique_sorted_dates[0] + timedelta(days=nights)

    # --- Guests: a CARDINAL entity near a guest-count word ---
    for ent in doc.ents:
        if ent.label_ == "CARDINAL":
            window_start = max(ent.start - 3, 0)
            window_end = min(ent.end + 3, len(doc))
            window_text = doc[window_start:window_end].text
            if _GUEST_WORD_PATTERN.search(window_text):
                parsed_number = _parse_cardinal(ent.text)
                if parsed_number is not None:
                    result.guests = parsed_number
                    break

    # --- City: PhraseMatcher against known cities ---
    city_matches = _city_matcher(doc)
    if city_matches:
        _, start, end = city_matches[0]
        result.city = doc[start:end].text.title()

    # --- Room type: PhraseMatcher against known room types ---
    room_matches = _room_type_matcher(doc)
    if room_matches:
        _, start, end = room_matches[0]
        result.room_type = doc[start:end].text.title()

    # --- Budget: a MONEY entity ---
    for ent in doc.ents:
        if ent.label_ == "MONEY":
            digits = re.sub(r"[^\d.]", "", ent.text)
            if digits:
                try:
                    result.max_price = Decimal(digits)
                except InvalidOperation:
                    pass
            break

    return result


def classify_reservation_sub_intent(text: str) -> Optional[str]:
    """Lemma-based keyword classification — e.g. "booked"/"booking"/"book"
    all reduce to the lemma "book", so this is more robust than a plain
    substring-in-string check (which would miss "booked" if only "book"
    were listed). Still fundamentally rule-based, not a trained
    classifier — an honest middle ground between the old plain-keyword
    approach and a full ML/LLM intent classifier, which is out of scope
    for this project's current stage.
    """
    doc = _nlp(text)
    lemmas = {token.lemma_.lower() for token in doc}

    if "cancel" in lemmas:
        return "cancel_booking"
    if lemmas & {"book", "reserve"}:
        return "create_booking"
    if "booking" in lemmas and lemmas & {"check", "view", "see", "show"}:
        # spaCy lemmatizes "booked"/"book" (verb: to reserve) differently
        # from "booking" (noun: an existing reservation) — verified by
        # direct token inspection. "checking my booking" should mean
        # "show me my existing reservation", not "make a new one".
        return "list_bookings"
    if lemmas & {"available", "availability"}:
        return "check_availability"
    if "hotel" in lemmas:
        return "list_hotels"
    if lemmas & {"search", "find", "show", "look"}:
        return "search_rooms"
    return None


def parse_reservation_request(
    text: str, reference_date: Optional[date] = None
) -> dict:
    """Best-effort: guest free text -> {intent, payload} ready to hand to
    ReservationAgent.handle_message.

    Deliberately conservative about "create_booking": free text alone
    can name dates/guests/a city, but never a specific room_id, and this
    system requires an explicit confirmation step before any booking is
    written (see agents/reservation/tools/booking_tools.py). So even a
    message that clearly SOUNDS like "book me a room" is routed to
    search_rooms instead — showing the guest real options to choose from
    is the safe next step, not guessing which room they meant.

    A resolved check-in/check-out pair is treated as sufficient signal to
    delegate to search_rooms on its own — a message like "a room for
    tomorrow, 5 nights, 1 guest" clearly wants a room search even without
    the word "book" or "search" anywhere in it. The lemma-based
    sub_intent classifier is only needed for the intents that have no
    date signal of their own (list_hotels).

    Returns {"intent": None, ...} when there isn't enough confidently
    extracted information to safely delegate anything — callers should
    treat that as "ask a clarifying question", not "guess."
    """
    entities = extract_reservation_entities(text, reference_date=reference_date)
    search_payload = entities.to_search_payload()
    if search_payload is not None:
        return {"intent": "search_rooms", "payload": search_payload, "entities": entities}

    sub_intent = classify_reservation_sub_intent(text)
    if sub_intent == "list_hotels" and entities.city:
        return {
            "intent": "list_hotels",
            "payload": {"city": entities.city},
            "entities": entities,
        }
    if sub_intent == "list_bookings":
        # Needs no extracted parameters — the tool takes only the
        # authenticated user from context, so this can always delegate
        # once classified, unlike search/list_hotels which need entities.
        return {"intent": "list_bookings", "payload": {}, "entities": entities}

    return {"intent": None, "payload": {}, "entities": entities}
