from datetime import date, timedelta

import pytest

from agents.reservation.schemas.bookings import CreateBookingRequest, ModifyBookingRequest
from agents.reservation.services import booking_service
from agents.reservation.services.exceptions import (
    BookingNotFoundError,
    NotAuthorizedError,
    RoomNotFoundError,
    RoomUnavailableError,
)

TODAY = date.today()


def _dates(offset_in=10, nights=3):
    check_in = TODAY + timedelta(days=offset_in)
    check_out = check_in + timedelta(days=nights)
    return check_in, check_out


def test_create_booking_success(db_session, room, guest):
    check_in, check_out = _dates()
    booking = booking_service.create_booking(
        db_session,
        guest.id,
        CreateBookingRequest(
            room_id=room.id, check_in_date=check_in, check_out_date=check_out, guests=2
        ),
    )
    assert booking.id is not None
    assert booking.user_id == guest.id
    assert booking.status == "confirmed"
    assert booking.total_price == room.price_per_night * 3


def test_create_booking_rejects_overlapping_dates(db_session, room, guest, other_guest):
    check_in, check_out = _dates()
    booking_service.create_booking(
        db_session,
        guest.id,
        CreateBookingRequest(
            room_id=room.id, check_in_date=check_in, check_out_date=check_out, guests=2
        ),
    )

    overlap_start = check_in + timedelta(days=1)
    overlap_end = overlap_start + timedelta(days=1)
    with pytest.raises(RoomUnavailableError):
        booking_service.create_booking(
            db_session,
            other_guest.id,
            CreateBookingRequest(
                room_id=room.id,
                check_in_date=overlap_start,
                check_out_date=overlap_end,
                guests=1,
            ),
        )


def test_create_booking_rejects_over_capacity(db_session, room, guest):
    check_in, check_out = _dates()
    with pytest.raises(RoomUnavailableError):
        booking_service.create_booking(
            db_session,
            guest.id,
            CreateBookingRequest(
                room_id=room.id, check_in_date=check_in, check_out_date=check_out, guests=99
            ),
        )


def test_create_booking_room_not_found(db_session, guest):
    check_in, check_out = _dates()
    with pytest.raises(RoomNotFoundError):
        booking_service.create_booking(
            db_session,
            guest.id,
            CreateBookingRequest(
                room_id=9999, check_in_date=check_in, check_out_date=check_out, guests=1
            ),
        )


def test_owner_can_view_own_booking(db_session, room, guest):
    check_in, check_out = _dates()
    booking = booking_service.create_booking(
        db_session,
        guest.id,
        CreateBookingRequest(
            room_id=room.id, check_in_date=check_in, check_out_date=check_out, guests=2
        ),
    )
    fetched = booking_service.get_booking(db_session, booking.id, guest)
    assert fetched.id == booking.id


def test_other_guest_cannot_view_booking(db_session, room, guest, other_guest):
    check_in, check_out = _dates()
    booking = booking_service.create_booking(
        db_session,
        guest.id,
        CreateBookingRequest(
            room_id=room.id, check_in_date=check_in, check_out_date=check_out, guests=2
        ),
    )
    with pytest.raises(NotAuthorizedError):
        booking_service.get_booking(db_session, booking.id, other_guest)


def test_staff_can_view_any_booking(db_session, room, guest, staff_user):
    check_in, check_out = _dates()
    booking = booking_service.create_booking(
        db_session,
        guest.id,
        CreateBookingRequest(
            room_id=room.id, check_in_date=check_in, check_out_date=check_out, guests=2
        ),
    )
    fetched = booking_service.get_booking(db_session, booking.id, staff_user)
    assert fetched.id == booking.id


def test_get_booking_not_found(db_session, guest):
    with pytest.raises(BookingNotFoundError):
        booking_service.get_booking(db_session, 9999, guest)


def test_cancel_booking_frees_the_room(db_session, room, guest, other_guest):
    check_in, check_out = _dates()
    booking = booking_service.create_booking(
        db_session,
        guest.id,
        CreateBookingRequest(
            room_id=room.id, check_in_date=check_in, check_out_date=check_out, guests=2
        ),
    )

    booking_service.cancel_booking(db_session, booking.id, guest)
    assert booking.status == "cancelled"
    assert booking.cancelled_at is not None

    # Same dates should now be bookable again by someone else.
    new_booking = booking_service.create_booking(
        db_session,
        other_guest.id,
        CreateBookingRequest(
            room_id=room.id, check_in_date=check_in, check_out_date=check_out, guests=1
        ),
    )
    assert new_booking.id != booking.id


def test_cancel_already_cancelled_booking_raises(db_session, room, guest):
    check_in, check_out = _dates()
    booking = booking_service.create_booking(
        db_session,
        guest.id,
        CreateBookingRequest(
            room_id=room.id, check_in_date=check_in, check_out_date=check_out, guests=2
        ),
    )
    booking_service.cancel_booking(db_session, booking.id, guest)
    with pytest.raises(RoomUnavailableError):
        booking_service.cancel_booking(db_session, booking.id, guest)


def test_modify_booking_changes_dates(db_session, room, guest):
    check_in, check_out = _dates()
    booking = booking_service.create_booking(
        db_session,
        guest.id,
        CreateBookingRequest(
            room_id=room.id, check_in_date=check_in, check_out_date=check_out, guests=2
        ),
    )

    new_check_in = check_in + timedelta(days=30)
    new_check_out = new_check_in + timedelta(days=2)
    updated = booking_service.modify_booking(
        db_session,
        booking.id,
        guest,
        ModifyBookingRequest(check_in_date=new_check_in, check_out_date=new_check_out),
    )
    assert updated.check_in_date == new_check_in
    assert updated.check_out_date == new_check_out
    assert updated.total_price == room.price_per_night * 2


def test_modify_booking_rejects_conflicting_new_dates(db_session, room, guest, other_guest):
    check_in, check_out = _dates()
    booking_a = booking_service.create_booking(
        db_session,
        guest.id,
        CreateBookingRequest(
            room_id=room.id, check_in_date=check_in, check_out_date=check_out, guests=2
        ),
    )
    later_in = check_out + timedelta(days=5)
    later_out = later_in + timedelta(days=2)
    booking_b = booking_service.create_booking(
        db_session,
        other_guest.id,
        CreateBookingRequest(
            room_id=room.id, check_in_date=later_in, check_out_date=later_out, guests=1
        ),
    )

    # Trying to move booking_b to overlap booking_a's dates must fail.
    with pytest.raises(RoomUnavailableError):
        booking_service.modify_booking(
            db_session,
            booking_b.id,
            other_guest,
            ModifyBookingRequest(check_in_date=check_in, check_out_date=check_out),
        )


def test_modify_booking_over_capacity_rejected(db_session, room, guest):
    check_in, check_out = _dates()
    booking = booking_service.create_booking(
        db_session,
        guest.id,
        CreateBookingRequest(
            room_id=room.id, check_in_date=check_in, check_out_date=check_out, guests=2
        ),
    )
    with pytest.raises(RoomUnavailableError):
        booking_service.modify_booking(
            db_session, booking.id, guest, ModifyBookingRequest(guests=99)
        )