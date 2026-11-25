"""One exception type for every 'safe to show the user' problem."""


class ServiceError(Exception):
    """Raised by services for validation / permission problems. Message is user-safe."""
