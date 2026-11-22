from typing import Protocol


class PrinterError(Exception):
    """A printer transport failed."""


class PrinterNotFound(PrinterError):
    """The print command (lp/CUPS) is not available."""


class PrintFailed(PrinterError):
    """The print job could not be delivered."""


class PrinterPort(Protocol):
    """
    PrinterPort is what the logic layer needs from a print transport.

    A transport only delivers a file: choosing the options is a logic concern.
    """

    def supported_options(self) -> str:
        """Return the raw option listing supported by the printer ('' if unknown)."""

    def send(self, file_path: str, options: list[str]) -> None:
        """Deliver the file to the printer. Raises PrinterError on failure."""


class QueueStatePort(Protocol):
    """Persistence of the photo and edit queues."""

    def load_queues(self) -> dict: ...

    def save_queues(self, photos: list, edits: list) -> None: ...
