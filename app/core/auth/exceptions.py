"""Authentication exceptions."""

from app.core.exceptions import DomainException


class AuthenticationException(DomainException):
    """Base exception for authentication errors."""
    pass


class InvalidCredentialsException(AuthenticationException):
    """Raised when login credentials are invalid."""
    
    def __init__(self) -> None:
        super().__init__("Invalid username or password")


class UserNotFoundException(AuthenticationException):
    """Raised when user is not found."""
    
    def __init__(self, identifier: str) -> None:
        super().__init__(f"User not found: {identifier}")
        self.identifier = identifier


class UserAlreadyExistsException(AuthenticationException):
    """Raised when trying to create user that already exists."""
    
    def __init__(self, username: str) -> None:
        super().__init__(f"User already exists: {username}")
        self.username = username


class InvalidTokenException(AuthenticationException):
    """Raised when token is invalid or malformed."""
    
    def __init__(self, reason: str = "Invalid token") -> None:
        super().__init__(reason)


class ExpiredTokenException(AuthenticationException):
    """Raised when token has expired."""
    
    def __init__(self) -> None:
        super().__init__("Token has expired")


class RevokedTokenException(AuthenticationException):
    """Raised when token has been revoked."""
    
    def __init__(self) -> None:
        super().__init__("Token has been revoked")


class InactiveUserException(AuthenticationException):
    """Raised when user account is inactive."""
    
    def __init__(self, username: str) -> None:
        super().__init__(f"User account is inactive: {username}")
        self.username = username