from app.models.place import Place


def _seed_place(db_session, **overrides):
    defaults = dict(
        name="Ministry of Crab", category="restaurant", cuisine="seafood",
        city="Colombo", description="A landmark seafood restaurant.",
        budget_tier="premium", rating=4.7,
    )
    defaults.update(overrides)
    place = Place(**defaults)
    db_session.add(place)
    db_session.commit()
    db_session.refresh(place)
    return place


def test_search_requires_at_least_one_criterion(client):
    response = client.post("/api/recommendations/search", json={})
    assert response.status_code == 400


def test_search_returns_matching_place(client, db_session):
    _seed_place(db_session)

    response = client.post(
        "/api/recommendations/search", json={"city": "Colombo", "category": "restaurant"}
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["place"]["name"] == "Ministry of Crab"


def test_get_place_by_id(client, db_session):
    place = _seed_place(db_session)

    response = client.get(f"/api/recommendations/{place.id}")

    assert response.status_code == 200
    assert response.json()["name"] == "Ministry of Crab"


def test_get_missing_place_returns_404(client):
    response = client.get("/api/recommendations/999999")
    assert response.status_code == 404


def test_create_place_requires_staff(client, auth_headers):
    response = client.post(
        "/api/recommendations",
        json={
            "name": "Test Place", "category": "attraction", "city": "Colombo",
            "description": "A test place.", "budget_tier": "budget",
        },
        headers=auth_headers,
    )
    assert response.status_code == 403


def test_list_places_public(client, db_session):
    _seed_place(db_session)

    response = client.get("/api/recommendations", params={"city": "Colombo"})

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_update_place_requires_staff(client, db_session, auth_headers):
    place = _seed_place(db_session)
    response = client.patch(
        f"/api/recommendations/{place.id}", json={"rating": 5}, headers=auth_headers
    )
    assert response.status_code == 403


def test_update_place_requires_at_least_one_field(client, db_session, staff_auth_headers):
    place = _seed_place(db_session)
    response = client.patch(
        f"/api/recommendations/{place.id}", json={}, headers=staff_auth_headers
    )
    assert response.status_code == 400


def test_update_place_applies_provided_fields_only(client, db_session, staff_auth_headers):
    place = _seed_place(db_session)
    response = client.patch(
        f"/api/recommendations/{place.id}",
        json={"rating": 4.9, "tags": ["updated", "seafood"]},
        headers=staff_auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["rating"] == "4.9"
    assert set(body["tags"]) == {"updated", "seafood"}
    assert body["name"] == "Ministry of Crab"


def test_update_missing_place_returns_404(client, staff_auth_headers):
    response = client.patch(
        "/api/recommendations/999999", json={"rating": 5}, headers=staff_auth_headers
    )
    assert response.status_code == 404


def test_delete_place_requires_staff(client, db_session, auth_headers):
    place = _seed_place(db_session)
    response = client.delete(f"/api/recommendations/{place.id}", headers=auth_headers)
    assert response.status_code == 403


def test_delete_place_soft_deletes_and_hides_from_search(client, db_session, staff_auth_headers):
    place = _seed_place(db_session)
    delete_response = client.delete(
        f"/api/recommendations/{place.id}", headers=staff_auth_headers
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["is_active"] is False

    get_response = client.get(f"/api/recommendations/{place.id}")
    assert get_response.status_code == 404


def test_delete_missing_place_returns_404(client, staff_auth_headers):
    response = client.delete("/api/recommendations/999999", headers=staff_auth_headers)
    assert response.status_code == 404


def test_analytics_overview_requires_staff(client, auth_headers):
    response = client.get("/api/recommendations/analytics/overview", headers=auth_headers)
    assert response.status_code == 403


def test_analytics_overview_returns_composition(client, db_session, staff_auth_headers):
    _seed_place(db_session)
    _seed_place(
        db_session,
        name="Cafe Kumbuk",
        category="restaurant",
        budget_tier="moderate",
        rating=4.4,
    )
    response = client.get("/api/recommendations/analytics/overview", headers=staff_auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_places"] == 2
    assert body["by_category"]["restaurant"] == 2