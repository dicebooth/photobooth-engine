from typing import Protocol


class NamingStatePort(Protocol):
    """Persistence of the photo session counter."""

    def load_naming_session_string(self) -> str: ...

    def save_naming_session_string(self, session: str) -> None: ...
