from agents.recommendation.services import analytics_service


def test_overview_counts_active_and_inactive_separately(seeded_places, db_session):
    overview = analytics_service.build_overview(db_session)
    assert overview.total_places == 4
    assert overview.active_places == 3
    assert overview.inactive_places == 1


def test_overview_breaks_down_by_category_city_and_budget(seeded_places, db_session):
    overview = analytics_service.build_overview(db_session)
    assert overview.by_category["restaurant"] == 3
    assert overview.by_category["attraction"] == 1
    assert overview.by_city["Colombo"] == 3
    assert overview.by_city["Kandy"] == 1
    assert overview.by_budget_tier["premium"] == 1


def test_overview_computes_average_rating_overall_and_per_category(seeded_places, db_session):
    overview = analytics_service.build_overview(db_session)
    assert overview.average_rating is not None
    assert overview.average_rating_by_category["attraction"] == 4.8


def test_overview_handles_empty_catalog(db_session):
    overview = analytics_service.build_overview(db_session)
    assert overview.total_places == 0
    assert overview.average_rating is None
    assert overview.by_category == {}