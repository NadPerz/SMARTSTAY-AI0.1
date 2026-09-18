from typing import Any, Dict, List, Optional

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models.place import Place

from agents.recommendation.schemas.places import PlaceOut, PlaceSearchRequest
from agents.recommendation.services import retrieval_service
from agents.recommendation.services.exceptions import PlaceNotFoundError
from agents.recommendation.tools.utils import format_validation_error


def search_recommendations(
    db: Session,
    query: Optional[str] = None,
    city: Optional[str] = None,
    category: Optional[str] = None,
    cuisine: Optional[str] = None,
    budget_tier: Optional[str] = None,
    max_results: int = 5,
    use_llm_explanation: bool = False,
) -> Dict[str, Any]:
    try:
        request = PlaceSearchRequest(
            query=query,
            city=city,
            category=category,
            cuisine=cuisine,
            budget_tier=budget_tier,
            max_results=max_results,
            use_llm_explanation=use_llm_explanation,
        )
    except ValidationError as exc:
        return {"success": False, "error": format_validation_error(exc)}

    if not request.has_any_criteria():
        return {
            "success": False,
            "error": "Provide at least a search query, city, category, cuisine, or budget preference.",
        }

    results: List = retrieval_service.search_places(db, request)
    return {
        "success": True,
        "data": {
            "count": len(results),
            "results": [r.model_dump(mode="json") for r in results],
        },
    }


def get_place_details(db: Session, place_id: int) -> Dict[str, Any]:
    place = (
        db.query(Place)
        .filter(Place.id == place_id, Place.is_active.is_(True))
        .first()
    )
    if place is None:
        return {"success": False, "error": str(PlaceNotFoundError(f"Place {place_id} does not exist"))}

    return {"success": True, "data": PlaceOut.model_validate(place).model_dump(mode="json")}