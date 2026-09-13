from datetime import date, timedelta

from app.models.booking import Booking

from agents.reservation.tools import booking_tools, room_tools

TODAY = date.today()


def _dates(offset_in=10, nights=3):
    check_in = (TODAY + timedelta(days=offset_in)).isoformat()
    check_out = (TODAY + timedelta(days=offset_in + nights)).isoformat()
    return check_in, check_out


def test_search_rooms_tool_success(db_session, room):
    check_in, check_out = _dates()
    result = room_tools.search_rooms(
        db_session, check_in_date=check_in, check_out_date=check_out, guests=2
    )
    assert result["success"] is True
    assert result["data"]["count"] == 1


def test_search_rooms_tool_rejects_inverted_dates(db_session, room):
    check_in, check_out = _dates()
    # swap them
    result = room_tools.search_rooms(
        db_session, check_in_date=check_out, check_out_date=check_in, guests=2
    )
    assert result["success"] is False
    assert "error" in result


def test_check_availability_tool_room_not_found(db_session):
    check_in, check_out = _dates()
    result = room_tools.check_availability(
        db_session, room_id=9999, check_in_date=check_in, check_out_date=check_out, guests=1
    )
    assert result["success"] is False


def test_get_booking_summary_tool_does_not_write_to_db(db_session, room):
    check_in, check_out = _dates()
    result = booking_tools.get_booking_summary(
        db_session, room_id=room.id, check_in_date=check_in, check_out_date=check_out, guests=2
    )
    assert result["success"] is True
    assert db_session.query(Booking).count() == 0


def test_create_booking_tool_refuses_without_confirm(db_session, room, guest):
    check_in, check_out = _dates()
    result = booking_tools.create_booking(
        db_session,
        guest,
        room_id=room.id,
        check_in_date=check_in,
        check_out_date=check_out,
        guests=2,
        confirm=False,
    )
    assert result["success"] is False
    assert db_session.query(Booking).count() == 0


def test_create_booking_tool_succeeds_with_confirm(db_session, room, guest):
    check_in, check_out = _dates()
    result = booking_tools.create_booking(
        db_session,
        guest,
        room_id=room.id,
        check_in_date=check_in,
        check_out_date=check_out,
        guests=2,
        confirm=True,
    )
    assert result["success"] is True
    assert db_session.query(Booking).count() == 1
    assert result["data"]["status"] == "confirmed"


def test_cancel_booking_tool_refuses_without_confirm(db_session, room, guest):
    check_in, check_out = _dates()
    created = booking_tools.create_booking(
        db_session,
        guest,
        room_id=room.id,
        check_in_date=check_in,
        check_out_date=check_out,
        guests=2,
        confirm=True,
    )
    booking_id = created["data"]["id"]

    result = booking_tools.cancel_booking(db_session, guest, booking_id, confirm=False)
    assert result["success"] is False
    refreshed = db_session.query(Booking).filter(Booking.id == booking_id).first()
    assert refreshed.status == "confirmed"  # unchanged


def test_cancel_booking_tool_succeeds_with_confirm(db_session, room, guest):
    check_in, check_out = _dates()
    created = booking_tools.create_booking(
        db_session,
        guest,
        room_id=room.id,
        check_in_date=check_in,
        check_out_date=check_out,
        guests=2,
        confirm=True,
    )
    booking_id = created["data"]["id"]

    result = booking_tools.cancel_booking(db_session, guest, booking_id, confirm=True)
    assert result["success"] is True
    assert result["data"]["status"] == "cancelled"


def test_get_booking_tool_enforces_ownership(db_session, room, guest, other_guest):
    check_in, check_out = _dates()
    created = booking_tools.create_booking(
        db_session,
        guest,
        room_id=room.id,
        check_in_date=check_in,
        check_out_date=check_out,
        guests=2,
        confirm=True,
    )
    booking_id = created["data"]["id"]

    result = booking_tools.get_booking(db_session, other_guest, booking_id)
    assert result["success"] is False


def test_list_my_bookings_tool(db_session, room, guest):
    check_in, check_out = _dates()
    booking_tools.create_booking(
        db_session,
        guest,
        room_id=room.id,
        check_in_date=check_in,
        check_out_date=check_out,
        guests=2,
        confirm=True,
    )
    result = booking_tools.list_my_bookings(db_session, guest)
    assert result["success"] is True
    assert result["data"]["count"] == 1