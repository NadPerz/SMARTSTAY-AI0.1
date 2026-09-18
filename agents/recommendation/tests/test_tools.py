from agents.recommendation.tools import recommendation_tools


def test_search_recommendations_requires_at_least_one_criterion(seeded_places, db_session):
    result = recommendation_tools.search_recommendations(db=db_session)

    assert result["success"] is False
    assert "at least" in result["error"].lower()


def test_search_recommendations_rejects_invalid_category(seeded_places, db_session):
    result = recommendation_tools.search_recommendations(db=db_session, category="not-a-real-category")

    assert result["success"] is False
    assert "category" in result["error"].lower()


def test_search_recommendations_returns_ranked_results(seeded_places, db_session):
    result = recommendation_tools.search_recommendations(
        db=db_session, city="Colombo", category="restaurant"
    )

    assert result["success"] is True
    assert result["data"]["count"] == 2
    assert result["data"]["results"][0]["place"]["name"] == "Ministry of Crab"


def test_get_place_details_success(seeded_places, db_session):
    place_id = seeded_places[0].id

    result = recommendation_tools.get_place_details(db=db_session, place_id=place_id)

    assert result["success"] is True
    assert result["data"]["name"] == "Ministry of Crab"


def test_get_place_details_not_found(seeded_places, db_session):
    result = recommendation_tools.get_place_details(db=db_session, place_id=999999)

    assert result["success"] is False
    assert "999999" in result["error"]


def test_get_place_details_excludes_inactive_place(seeded_places, db_session):
    inactive = next(p for p in seeded_places if p.name == "Closed Down Diner")

    result = recommendation_tools.get_place_details(db=db_session, place_id=inactive.id)

    assert result["success"] is False