from datetime import date, timedelta

import pytest

from agents.reservation.schemas.rooms import RoomSearchRequest
from agents.reservation.services import availability_service
from agents.reservation.services.exceptions import RoomNotFoundError

TODAY = date.today()


def _dates(offset_in=10, nights=3):
    check_in = TODAY + timedelta(days=offset_in)
    check_out = check_in + timedelta(days=nights)
    return check_in, check_out


def test_search_finds_room_when_free(db_session, room):
    check_in, check_out = _dates()
    results = availability_service.search_available_rooms(
        db_session,
        RoomSearchRequest(check_in_date=check_in, check_out_date=check_out, guests=2),
    )
    assert len(results) == 1
    assert results[0].room.id == room.id
    assert results[0].nights == 3
    assert results[0].total_price == room.price_per_night * 3


def test_search_excludes_rooms_under_requested_capacity(db_session, room):
    check_in, check_out = _dates()
    results = availability_service.search_available_rooms(
        db_session,
        # room.capacity is 2, guests=3 should exclude it
        RoomSearchRequest(check_in_date=check_in, check_out_date=check_out, guests=3),
    )
    assert results == []


def test_has_overlapping_booking_true_for_overlapping_range(db_session, room, guest):
    from agents.reservation.services import booking_service
    from agents.reservation.schemas.bookings import CreateBookingRequest

    check_in, check_out = _dates()
    booking_service.create_booking(
        db_session,
        guest.id,
        CreateBookingRequest(
            room_id=room.id, check_in_date=check_in, check_out_date=check_out, guests=2
        ),
    )

    overlap_start = check_in + timedelta(days=1)
    overlap_end = overlap_start + timedelta(days=2)
    assert availability_service.has_overlapping_booking(
        db_session, room.id, overlap_start, overlap_end
    )


def test_has_overlapping_booking_false_for_back_to_back_dates(db_session, room, guest):
    from agents.reservation.services import booking_service
    from agents.reservation.schemas.bookings import CreateBookingRequest

    check_in, check_out = _dates()
    booking_service.create_booking(
        db_session,
        guest.id,
        CreateBookingRequest(
            room_id=room.id, check_in_date=check_in, check_out_date=check_out, guests=2
        ),
    )

    # A new booking starting exactly on the previous booking's checkout day
    # must NOT count as an overlap — this is the half-open interval rule.
    next_check_out = check_out + timedelta(days=2)
    assert not availability_service.has_overlapping_booking(
        db_session, room.id, check_out, next_check_out
    )


def test_check_room_availability_room_not_found(db_session):
    check_in, check_out = _dates()
    with pytest.raises(RoomNotFoundError):
        availability_service.check_room_availability(
            db_session, room_id=9999, check_in_date=check_in, check_out_date=check_out, guests=1
        )


def test_check_room_availability_over_capacity(db_session, room):
    check_in, check_out = _dates()
    result = availability_service.check_room_availability(
        db_session, room.id, check_in, check_out, guests=99
    )
    assert result.is_available is False
    assert "capacity" in result.reason.lower()


def test_get_room_not_found_raises(db_session):
    with pytest.raises(RoomNotFoundError):
        availability_service.get_room(db_session, 9999)