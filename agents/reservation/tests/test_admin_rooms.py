import pytest

from agents.reservation.schemas.rooms import RoomCreateRequest
from agents.reservation.services import availability_service
from agents.reservation.services.exceptions import RoomAlreadyExistsError


def test_create_room_success(db_session):
    room = availability_service.create_room(
        db_session,
        RoomCreateRequest(
            room_number="999",
            room_type="Penthouse",
            capacity=4,
            price_per_night=500.00,
        ),
    )
    assert room.id is not None
    assert room.room_number == "999"
    assert room.is_active is True


def test_create_room_rejects_duplicate_room_number(db_session, room):
    with pytest.raises(RoomAlreadyExistsError):
        availability_service.create_room(
            db_session,
            RoomCreateRequest(
                room_number=room.room_number,  # already taken by the `room` fixture
                room_type="Standard",
                capacity=2,
                price_per_night=90.00,
            ),
        )