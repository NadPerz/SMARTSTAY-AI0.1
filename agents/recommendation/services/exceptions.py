class RecommendationError(Exception):
    """Base class for all recommendation domain errors."""


class PlaceNotFoundError(RecommendationError):
    """Raised when a place_id doesn't exist or is inactive."""