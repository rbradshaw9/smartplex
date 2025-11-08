"""Custom exceptions for SmartPlex API."""

from typing import Optional


class SmartPlexException(Exception):
    """Base exception for SmartPlex API."""
    
    def __init__(
        self, 
        message: str, 
        status_code: int = 500, 
        details: Optional[str] = None
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class DatabaseException(SmartPlexException):
    """Database-related exceptions."""
    
    def __init__(self, message: str, details: Optional[str] = None) -> None:
        super().__init__(message, status_code=500, details=details)


class AuthenticationException(SmartPlexException):
    """Authentication-related exceptions."""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[str] = None) -> None:
        super().__init__(message, status_code=401, details=details)


class AuthorizationException(SmartPlexException):
    """Authorization-related exceptions."""
    
    def __init__(self, message: str = "Access denied", details: Optional[str] = None) -> None:
        super().__init__(message, status_code=403, details=details)


class ValidationException(SmartPlexException):
    """Validation-related exceptions."""
    
    def __init__(self, message: str, details: Optional[str] = None) -> None:
        super().__init__(message, status_code=422, details=details)


class ExternalAPIException(SmartPlexException):
    """External API integration exceptions."""
    
    def __init__(self, message: str, details: Optional[str] = None) -> None:
        super().__init__(message, status_code=502, details=details)