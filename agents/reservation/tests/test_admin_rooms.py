import pytest

from agents.reservation.schemas.hotels import HotelCreateRequest
from agents.reservation.schemas.rooms import RoomCreateRequest
from agents.reservation.services import availability_service
from agents.reservation.services.exceptions import HotelNotFoundError, RoomAlreadyExistsError


def test_create_room_success(db_session, hotel):
    room = availability_service.create_room(
        db_session,
        RoomCreateRequest(
            hotel_id=hotel.id,
            room_number="999",
            room_type="Penthouse",
            capacity=4,
            price_per_night=500.00,
        ),
    )
    assert room.id is not None
    assert room.hotel_id == hotel.id
    assert room.room_number == "999"
    assert room.is_active is True


def test_create_room_rejects_duplicate_room_number_at_same_hotel(db_session, hotel, room):
    with pytest.raises(RoomAlreadyExistsError):
        availability_service.create_room(
            db_session,
            RoomCreateRequest(
                hotel_id=hotel.id,
                room_number=room.room_number,  # already taken at this hotel by the `room` fixture
                room_type="Standard",
                capacity=2,
                price_per_night=90.00,
            ),
        )


def test_create_room_allows_same_room_number_at_different_hotel(
    db_session, hotel, second_hotel, room
):
    """room_number only needs to be unique WITHIN a hotel — a different
    hotel can reuse the same number."""
    new_room = availability_service.create_room(
        db_session,
        RoomCreateRequest(
            hotel_id=second_hotel.id,
            room_number=room.room_number,  # same number, different hotel — should succeed
            room_type="Standard",
            capacity=2,
            price_per_night=70.00,
        ),
    )
    assert new_room.id is not None
    assert new_room.hotel_id == second_hotel.id


def test_create_room_rejects_nonexistent_hotel(db_session):
    with pytest.raises(HotelNotFoundError):
        availability_service.create_room(
            db_session,
            RoomCreateRequest(
                hotel_id=9999,
                room_number="1",
                room_type="Standard",
                capacity=2,
                price_per_night=50.00,
            ),
        )


def test_create_hotel_success(db_session):
    hotel = availability_service.create_hotel(
        db_session, HotelCreateRequest(name="New Hotel", city="Jaffna", star_rating=3)
    )
    assert hotel.id is not None
    assert hotel.city == "Jaffna"


def test_list_hotels_filters_by_city(db_session, hotel, second_hotel):
    results = availability_service.list_hotels(db_session, city=hotel.city)
    assert len(results) == 1
    assert results[0].id == hotel.id


def test_list_hotels_no_filter_returns_all(db_session, hotel, second_hotel):
    results = availability_service.list_hotels(db_session)
    assert len(results) == 2


def test_get_hotel_not_found(db_session):
    with pytest.raises(HotelNotFoundError):
        availability_service.get_hotel(db_session, 9999)