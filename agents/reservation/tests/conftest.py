import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.models.booking import Booking  # noqa: F401 (registers relationship)
from app.models.room import Room
from app.models.user import User


@pytest.fixture()
def db_session():
    """A fresh in-memory SQLite database for a single test.

    Each test gets its own engine/schema, so tests can't leak state into
    each other regardless of execution order.
    """
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
def guest(db_session):
    user = User(email="guest@test.com", password_hash="x", role="guest")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def other_guest(db_session):
    user = User(email="other@test.com", password_hash="x", role="guest")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def staff_user(db_session):
    user = User(email="staff@test.com", password_hash="x", role="receptionist")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def room(db_session):
    r = Room(room_number="201", room_type="Deluxe", capacity=2, price_per_night=100.00)
    db_session.add(r)
    db_session.commit()
    db_session.refresh(r)
    return r