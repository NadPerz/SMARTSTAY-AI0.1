"""Tests for real spaCy-based reservation entity extraction.

REFERENCE is fixed (not date.today()) so date-resolution assertions are
deterministic regardless of what day the suite actually runs on.
"""

from datetime import date

from app.services.nlp_service import (
    classify_reservation_sub_intent,
    extract_reservation_entities,
    parse_reservation_request,
)

# A fixed Thursday, so "next Friday" / "this weekend" resolve predictably.
REFERENCE = date(2026, 9, 17)


def test_extracts_absolute_iso_dates():
    entities = extract_reservation_entities(
        "book a room from 2026-10-06 to 2026-10-09", reference_date=REFERENCE
    )
    assert entities.check_in_date == date(2026, 10, 6)
    assert entities.check_out_date == date(2026, 10, 9)


def test_splits_compound_date_range_span():
    """Regression test for a real bug found during development: spaCy
    tags '2026-10-06 to 2026-10-09' as ONE DATE entity, not two. Without
    the splitter, both dates end up in unresolved_date_spans instead of
    being resolved."""
    entities = extract_reservation_entities(
        "from 2026-10-06 to 2026-10-09 for 2 guests", reference_date=REFERENCE
    )
    assert entities.check_in_date == date(2026, 10, 6)
    assert entities.check_out_date == date(2026, 10, 9)
    assert entities.unresolved_date_spans == []


def test_resolves_next_weekday_phrasing():
    """Regression test: dateparser (as installed) does NOT resolve 'next
    Friday' on its own — verified by direct testing. This proves the
    normalization layer fixes it."""
    entities = extract_reservation_entities(
        "next Friday to next Sunday", reference_date=REFERENCE
    )
    assert entities.check_in_date == date(2026, 9, 18)  # the Friday after Sept 17
    assert entities.check_out_date == date(2026, 9, 20)  # the following Sunday


def test_resolves_tomorrow():
    entities = extract_reservation_entities("a room for tomorrow", reference_date=REFERENCE)
    assert entities.check_in_date == date(2026, 9, 18)


def test_this_weekend_implies_a_two_night_range():
    """A bare 'this weekend' should imply Saturday->Monday, not a single
    unresolved day — weekends are inherently a range."""
    entities = extract_reservation_entities(
        "available this weekend", reference_date=REFERENCE
    )
    assert entities.check_in_date == date(2026, 9, 19)  # Saturday
    assert entities.check_out_date == date(2026, 9, 21)  # Monday


def test_single_date_plus_duration_computes_checkout():
    entities = extract_reservation_entities(
        "a room for tomorrow, 5 nights", reference_date=REFERENCE
    )
    assert entities.check_in_date == date(2026, 9, 18)
    assert entities.check_out_date == date(2026, 9, 23)


def test_extracts_digit_form_guest_count():
    entities = extract_reservation_entities("a room for 2 guests", reference_date=REFERENCE)
    assert entities.guests == 2


def test_extracts_spelled_out_guest_count():
    """Regression test for a real bug: int('two') raises ValueError.
    spaCy correctly tags 'two' as CARDINAL; the code must convert the
    word, not assume digits."""
    entities = extract_reservation_entities(
        "a room for two guests", reference_date=REFERENCE
    )
    assert entities.guests == 2


def test_does_not_mistake_an_unrelated_number_for_guests():
    """A number not near a guest-count word shouldn't be misread as guests."""
    entities = extract_reservation_entities(
        "room 12 please, for tomorrow", reference_date=REFERENCE
    )
    assert entities.guests is None


def test_extracts_known_city():
    entities = extract_reservation_entities(
        "a room in Kandy for tomorrow", reference_date=REFERENCE
    )
    assert entities.city == "Kandy"


def test_extracts_known_room_type():
    entities = extract_reservation_entities(
        "a deluxe room for tomorrow", reference_date=REFERENCE
    )
    assert entities.room_type == "Deluxe"


def test_extracts_budget():
    entities = extract_reservation_entities(
        "a room under $150 for tomorrow", reference_date=REFERENCE
    )
    assert entities.max_price == 150


def test_no_dates_means_no_search_payload():
    """Underspecified input (no dates at all) must not produce a fake
    payload with guessed dates — to_search_payload() should return None."""
    entities = extract_reservation_entities(
        "find me a suite for 4 people, budget $300", reference_date=REFERENCE
    )
    assert entities.to_search_payload() is None


def test_classify_sub_intent_cancel():
    assert classify_reservation_sub_intent("I want to cancel my booking") == "cancel_booking"


def test_classify_sub_intent_handles_inflected_forms():
    """Lemma-based matching: 'booked' and 'book' (both VERB forms) reduce
    to the same lemma, unlike a plain substring keyword check that would
    only catch the exact word listed."""
    assert classify_reservation_sub_intent("I already booked a room") == "create_booking"
    assert classify_reservation_sub_intent("I want to book a room") == "create_booking"


def test_classify_sub_intent_distinguishes_noun_booking_from_verb_book():
    """spaCy lemmatizes 'booking' differently depending on part of
    speech: as a VERB ('booking a room') it reduces to 'book'; as a NOUN
    ('my booking' = my existing reservation) it stays 'booking'. This
    lets 'checking my booking' be correctly read as wanting to VIEW an
    existing reservation, not create a new one — a real, tested
    distinction, not a guess."""
    assert classify_reservation_sub_intent("checking my booking") == "list_bookings"
    assert classify_reservation_sub_intent("show me my booking") == "list_bookings"


def test_classify_sub_intent_list_hotels():
    assert classify_reservation_sub_intent("what hotels are there") == "list_hotels"


def test_parse_request_delegates_search_rooms_from_dates_alone():
    """Resolved dates are sufficient signal to delegate to search_rooms
    even with no explicit 'book'/'search' verb in the message — this was
    a real bug found during development (an overly strict gate discarded
    perfectly good extracted entities)."""
    result = parse_reservation_request(
        "a room for tomorrow, 5 nights, 1 guest", reference_date=REFERENCE
    )
    assert result["intent"] == "search_rooms"
    assert result["payload"]["check_in_date"] == "2026-09-18"
    assert result["payload"]["check_out_date"] == "2026-09-23"
    assert result["payload"]["guests"] == 1


def test_parse_request_delegates_list_hotels_with_city_and_no_dates():
    result = parse_reservation_request("what hotels do you have in Galle", reference_date=REFERENCE)
    assert result["intent"] == "list_hotels"
    assert result["payload"] == {"city": "Galle"}


def test_parse_request_delegates_list_bookings():
    result = parse_reservation_request("show me my booking", reference_date=REFERENCE)
    assert result["intent"] == "list_bookings"
    assert result["payload"] == {}


def test_parse_request_returns_none_intent_when_underspecified():
    """Cancellation intent is correctly classified, but since it needs a
    booking_id that free text can't provide, this must NOT delegate —
    leaving it unresolved is correct, not a bug."""
    result = parse_reservation_request("I want to cancel my booking", reference_date=REFERENCE)
    assert result["intent"] is None


def test_parse_request_full_realistic_sentence():
    result = parse_reservation_request(
        "I need a room for two guests in Colombo next Friday to next Sunday under $150",
        reference_date=REFERENCE,
    )
    assert result["intent"] == "search_rooms"
    assert result["payload"] == {
        "check_in_date": "2026-09-18",
        "check_out_date": "2026-09-20",
        "guests": 2,
        "city": "Colombo",
        "max_price": 150.0,
    }
