import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app
from app.models.booking import Booking  # noqa: F401 (registers relationship)
from app.models.room import Room
from app.models.user import User  # noqa: F401


@pytest.fixture()
def db_session():
    # StaticPool is required here: FastAPI's TestClient runs each request
    # in a worker thread, and plain sqlite:///:memory: gives every new
    # connection (including ones from other threads) a fresh, separate,
    # empty database. StaticPool forces every connection to share the
    # same single in-memory database regardless of which thread asks.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
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
def client(db_session):
    """A real TestClient hitting the real FastAPI app, with only the
    database dependency swapped for an isolated in-memory one. Auth,
    validation, routing — everything else runs exactly as it does in
    production."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def seeded_room(db_session):
    room = Room(room_number="501", room_type="Suite", capacity=2, price_per_night=150.00)
    db_session.add(room)
    db_session.commit()
    db_session.refresh(room)
    return room


@pytest.fixture()
def auth_headers(client):
    """Registers a real user through the real /auth/register endpoint and
    returns headers with a real, valid JWT — not a mocked token."""
    response = client.post(
        "/auth/register", json={"email": "pytest-guest@test.com", "password": "password123"}
    )
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def other_auth_headers(client):
    response = client.post(
        "/auth/register", json={"email": "pytest-other@test.com", "password": "password123"}
    )
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}