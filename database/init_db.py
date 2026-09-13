"""Create all tables defined on the shared SQLAlchemy Base.

This repo doesn't use Alembic migrations yet, so this script is the
simplest way to get a local Postgres database into a runnable state.
Safe to re-run: create_all() only creates tables that don't already exist,
it never drops or alters existing ones.

Usage (from repo root, with backend/ on PYTHONPATH):
    PYTHONPATH=backend python database/init_db.py

Requires DATABASE_URL to be set in .env (see backend/app/db/database.py
for the default connection string used if it's not set).
"""

from app.db.database import Base, engine

# Every model must be imported here so SQLAlchemy registers it on
# Base.metadata before create_all() runs. Add new models to this list.
from app.models.user import User  # noqa: F401
from app.models.room import Room  # noqa: F401
from app.models.booking import Booking  # noqa: F401


def main() -> None:
    Base.metadata.create_all(bind=engine)
    print("Tables created:", ", ".join(Base.metadata.tables.keys()))


if __name__ == "__main__":
    main()