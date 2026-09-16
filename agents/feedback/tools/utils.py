from typing import Any, Dict

from pydantic import ValidationError

from agents.feedback.schemas.reviews import ReviewOut


def format_validation_error(exc: ValidationError) -> str:
    """Turn a Pydantic ValidationError into one short, guest-readable
    message instead of leaking the raw error structure back through the
    agent (which would look like an internal stack trace to the guest)."""
    first = exc.errors()[0]
    field = ".".join(str(p) for p in first["loc"])
    return f"{field}: {first['msg']}"


def serialize_review(review) -> Dict[str, Any]:
    """SQLAlchemy Review -> plain JSON-safe dict, via the ReviewOut schema."""
    return ReviewOut.model_validate(review).model_dump(mode="json")
