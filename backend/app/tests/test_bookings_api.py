from datetime import date, timedelta

TODAY = date.today()


def _dates(offset_in=15, nights=3):
    check_in = (TODAY + timedelta(days=offset_in)).isoformat()
    check_out = (TODAY + timedelta(days=offset_in + nights)).isoformat()
    return check_in, check_out


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_search_rooms_is_public(client, seeded_room):
    check_in, check_out = _dates()
    response = client.get(
        "/api/rooms/search",
        params={"check_in_date": check_in, "check_out_date": check_out, "guests": 2},
    )
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert results[0]["room"]["room_number"] == "501"


def test_search_rooms_rejects_malformed_dates(client, seeded_room):
    response = client.get(
        "/api/rooms/search",
        params={"check_in_date": "15.09.2026", "check_out_date": "18.09.2026", "guests": 2},
    )
    assert response.status_code == 422


def test_availability_check_room_not_found(client):
    check_in, check_out = _dates()
    response = client.get(
        "/api/rooms/99999/availability",
        params={"check_in_date": check_in, "check_out_date": check_out, "guests": 1},
    )
    assert response.status_code == 404


def test_booking_summary_requires_auth(client, seeded_room):
    check_in, check_out = _dates()
    response = client.post(
        "/api/bookings/summary",
        json={
            "room_id": seeded_room.id,
            "check_in_date": check_in,
            "check_out_date": check_out,
            "guests": 2,
        },
    )
    assert response.status_code in (401, 403)


def test_full_booking_lifecycle(client, seeded_room, auth_headers):
    check_in, check_out = _dates()
    payload = {
        "room_id": seeded_room.id,
        "check_in_date": check_in,
        "check_out_date": check_out,
        "guests": 2,
    }

    # Summary before booking, no side effects.
    response = client.post("/api/bookings/summary", json=payload, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["total_price"] == "450.00"

    # Create.
    response = client.post("/api/bookings", json=payload, headers=auth_headers)
    assert response.status_code == 201
    booking = response.json()
    booking_id = booking["id"]
    assert booking["status"] == "confirmed"

    # List.
    response = client.get("/api/bookings", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1

    # Get single.
    response = client.get(f"/api/bookings/{booking_id}", headers=auth_headers)
    assert response.status_code == 200

    # Modify.
    response = client.patch(
        f"/api/bookings/{booking_id}", json={"guests": 1}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["guests"] == 1

    # Cancel.
    response = client.delete(f"/api/bookings/{booking_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_double_booking_returns_409(client, seeded_room, auth_headers):
    check_in, check_out = _dates()
    payload = {
        "room_id": seeded_room.id,
        "check_in_date": check_in,
        "check_out_date": check_out,
        "guests": 1,
    }
    first = client.post("/api/bookings", json=payload, headers=auth_headers)
    assert first.status_code == 201

    second = client.post("/api/bookings", json=payload, headers=auth_headers)
    assert second.status_code == 409


def test_cannot_view_another_users_booking(
    client, seeded_room, auth_headers, other_auth_headers
):
    check_in, check_out = _dates()
    payload = {
        "room_id": seeded_room.id,
        "check_in_date": check_in,
        "check_out_date": check_out,
        "guests": 1,
    }
    created = client.post("/api/bookings", json=payload, headers=auth_headers)
    booking_id = created.json()["id"]

    response = client.get(f"/api/bookings/{booking_id}", headers=other_auth_headers)
    assert response.status_code == 403


def test_unauthenticated_request_to_protected_route_rejected(client):
    response = client.get("/api/bookings")
    assert response.status_code in (401, 403)