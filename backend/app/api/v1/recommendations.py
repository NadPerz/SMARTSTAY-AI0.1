from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.place import Place
from app.models.user import User
from app.security.jwt import get_current_user

from agents.reservation.services.booking_service import is_staff

from agents.recommendation.agent import recommendation_agent
from agents.recommendation.agent_context import RecommendationContext
from agents.recommendation.schemas.places import (
    PlaceAnalyticsOverview,
    PlaceCreateRequest,
    PlaceOut,
    PlaceSearchRequest,
    PlaceSearchResult,
    PlaceUpdateRequest,
)
from agents.recommendation.services import analytics_service, retrieval_service

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def require_staff(current_user: User = Depends(get_current_user)) -> User:
    if not is_staff(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Staff access required"
        )
    return current_user


@router.post("/search", response_model=List[PlaceSearchResult])
def search_recommendations(request: PlaceSearchRequest, db: Session = Depends(get_db)):
    if not request.has_any_criteria():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least a search query, city, category, cuisine, or budget preference.",
        )
    return retrieval_service.search_places(db, request)


class RecommendationAskRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)


@router.post("/ask")
async def ask_recommendation_agent(request: RecommendationAskRequest, db: Session = Depends(get_db)):
    return await recommendation_agent.handle_message(
        RecommendationContext(db=db, current_user=None), request.message
    )


# --- Analytics (staff-only) --------------------------------------------

@router.get("/analytics/overview", response_model=PlaceAnalyticsOverview)
def get_recommendation_analytics(
    db: Session = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    return analytics_service.build_overview(db)


@router.get("/{place_id}", response_model=PlaceOut)
def get_place(place_id: int, db: Session = Depends(get_db)):
    place = (
        db.query(Place)
        .filter(Place.id == place_id, Place.is_active.is_(True))
        .first()
    )
    if place is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Place not found")
    return place


@router.patch("/{place_id}", response_model=PlaceOut)
def update_place(
    place_id: int,
    request: PlaceUpdateRequest,
    db: Session = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    place = db.query(Place).filter(Place.id == place_id).first()
    if place is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Place not found")

    fields = request.provided_fields()
    if not fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one field to update.",
        )

    for key, value in fields.items():
        if key == "tags":
            value = ",".join(value) if value else None
        elif key in ("category", "budget_tier"):
            value = value.value if hasattr(value, "value") else value
        setattr(place, key, value)

    db.commit()
    db.refresh(place)
    return place


@router.delete("/{place_id}", response_model=PlaceOut)
def soft_delete_place(
    place_id: int,
    db: Session = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Sets is_active=False rather than deleting the row — a hard delete
    would break any past search result's id still referenced elsewhere,
    and erase analytics history for that place."""
    place = db.query(Place).filter(Place.id == place_id).first()
    if place is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Place not found")

    place.is_active = False
    db.commit()
    db.refresh(place)
    return place


@router.post("", response_model=PlaceOut, status_code=status.HTTP_201_CREATED)
def create_place(
    request: PlaceCreateRequest,
    db: Session = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    place = Place(
        name=request.name,
        category=request.category.value,
        cuisine=request.cuisine,
        city=request.city,
        address=request.address,
        description=request.description,
        budget_tier=request.budget_tier.value,
        rating=request.rating,
        tags=",".join(request.tags) if request.tags else None,
        is_active=request.is_active,
    )
    db.add(place)
    db.commit()
    db.refresh(place)
    return place


@router.get("", response_model=List[PlaceOut])
def list_places(
    city: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(Place).filter(Place.is_active.is_(True))
    if city:
        query = query.filter(Place.city.ilike(city))
    if category:
        query = query.filter(Place.category == category)
    return query.order_by(Place.city, Place.name).all()