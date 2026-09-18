import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.models.booking import Booking  # noqa: F401
from app.models.hotel import Hotel  # noqa: F401
from app.models.place import Place
from app.models.room import Room  # noqa: F401
from app.models.user import User  # noqa: F401


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def seeded_places(db_session):
    places = [
        Place(
            name="Ministry of Crab", category="restaurant", cuisine="seafood",
            city="Colombo", description="A landmark seafood restaurant famous for jumbo crab dishes.",
            budget_tier="premium", rating=4.7, tags="seafood,fine dining",
        ),
        Place(
            name="Cafe Kumbuk", category="restaurant", cuisine="cafe",
            city="Colombo", description="A relaxed garden cafe serving breakfast and coffee.",
            budget_tier="moderate", rating=4.4, tags="cafe,brunch",
        ),
        Place(
            name="Temple of the Sacred Tooth Relic", category="attraction", cuisine=None,
            city="Kandy", description="Sri Lanka's most revered Buddhist temple.",
            budget_tier="budget", rating=4.8, tags="temple,culture",
        ),
        Place(
            name="Closed Down Diner", category="restaurant", cuisine="seafood",
            city="Colombo", description="A seafood place that has since closed.",
            budget_tier="budget", rating=3.0, tags="seafood", is_active=False,
        ),
    ]
    db_session.add_all(places)
    db_session.commit()
    for p in places:
        db_session.refresh(p)
    return places