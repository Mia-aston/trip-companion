"""Domain errors. The API layer maps them to the error envelope (404 / 409 / 422)."""


class DomainError(Exception):
    def __init__(self, message: str, details: list | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or []


class NotFound(DomainError):
    """Entity does not exist (404)."""


class Conflict(DomainError):
    """Request is valid but clashes with stored state (409)."""


class InvalidChange(DomainError):
    """The change would leave the aggregate invalid (422)."""
