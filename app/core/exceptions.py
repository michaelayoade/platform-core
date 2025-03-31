"""
Custom exception classes for the Platform Core application.
"""

class PlatformCoreException(Exception):
    """Base exception class for all custom exceptions in this application."""
    status_code = 500
    detail = "An internal server error occurred."

    def __init__(self, detail: str | None = None):
        self.detail = detail if detail is not None else self.detail

class NotFoundError(PlatformCoreException):
    """Raised when a requested resource is not found."""
    status_code = 404
    detail = "Resource not found."

class BadRequestError(PlatformCoreException):
    """Raised when the request data is invalid or malformed."""
    status_code = 400
    detail = "Bad request."

class UnauthorizedError(PlatformCoreException):
    """Raised when an action is attempted without proper authorization."""
    status_code = 401 # Or 403 depending on context (unauthenticated vs forbidden)
    detail = "Unauthorized access."

class ForbiddenError(PlatformCoreException):
    """Raised when an authenticated user attempts an action they don't have permission for."""
    status_code = 403
    detail = "Forbidden."

class ConflictError(PlatformCoreException):
    """Raised when an action conflicts with the current state of a resource (e.g., duplicate creation)."""
    status_code = 409
    detail = "Resource conflict."
