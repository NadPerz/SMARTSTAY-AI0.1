from agents.recommendation.services.nlp_service import extract_recommendation_entities


def test_extracts_cuisine_budget_and_proximity():
    entities = extract_recommendation_entities(
        "Find affordable seafood restaurants close to the hotel."
    )

    assert entities["category"] == "restaurant"
    assert entities["cuisine"] == "seafood"
    assert entities["budget_tier"] == "budget"
    assert entities["near_hotel"] is True


def test_extracts_city_and_category():
    entities = extract_recommendation_entities(
        "What are some good attractions in Kandy?"
    )

    assert entities["category"] == "attraction"
    assert entities["city"] == "Kandy"


def test_extracts_premium_budget_from_luxury_keyword():
    entities = extract_recommendation_entities("I want a luxury dining experience")

    assert entities["category"] == "restaurant"
    assert entities["budget_tier"] == "premium"


def test_empty_message_returns_empty_dict():
    assert extract_recommendation_entities("") == {}
    assert extract_recommendation_entities(None) == {}  # type: ignore[arg-type]


def test_no_recognizable_entities_returns_only_keywords():
    entities = extract_recommendation_entities("Tell me something interesting")

    assert "category" not in entities
    assert "cuisine" not in entities
    assert "city" not in entities
    assert "keywords" in entities