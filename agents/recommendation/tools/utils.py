from pydantic import ValidationError


def format_validation_error(exc: ValidationError) -> str:
    first = exc.errors()[0]
    field = ".".join(str(p) for p in first["loc"])
    return f"{field}: {first['msg']}"