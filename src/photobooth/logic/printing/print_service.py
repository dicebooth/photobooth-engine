from dataclasses import dataclass

from photobooth.logic.editing.editor_service import EditorService
from photobooth.logic.printing.ports import PrinterError, PrinterPort
from photobooth.logic.printing.print_options_resolver import PrintOptionsResolver
from photobooth.logic.printing.queue_service import QueueService
from photobooth.logic.session.folder_manager import FolderManager


@dataclass(frozen=True)
class PrintResult:
    """Outcome of a print job, for the presentation layer to show."""

    photo_path: str
    error: str = ''

    @property
    def ok(self) -> bool:
        return not self.error


class PrintService:
    """
    PrintService manages the printing queue and prints the queued photos two
    at a time on a single sheet.

    It never writes to the terminal: the outcome of every job is returned as a
    PrintResult.
    """

    def __init__(self, queue: QueueService, editor: EditorService, folders: FolderManager,
                 printer: PrinterPort, options_resolver: PrintOptionsResolver):
        self._queue = queue
        self._editor = editor
        self._folders = folders
        self._printer = printer
        self._options_resolver = options_resolver
        self._options: list[str] = []

    def prepare(self):
        """
        Method which loads the queue and resolves the print options.
        """

        self._queue.load_queue()
        self._options = self._options_resolver.resolve(self._printer.supported_options)

    def dismiss(self):
        """
        Method which clears the queue at the end of the application.
        """

        self._queue.dismiss()

    def enqueue(self, photo_path: str, frame_path: str, copies: int):
        """
        Method which adds the photo and its frame to the printing queues.
        :param photo_path: photo path
        :param frame_path: frame path
        :param copies: number of copies to print
        """

        self._queue.add_photo(photo_path, copies)
        self._queue.add_edit(frame_path, copies)

    def prints_pending(self) -> bool:
        """
        Method which returns True if there are enough photos in the queue to print.
        """

        return self._queue.queue_is_ready()

    def print_next(self) -> PrintResult:
        """
        Method which edits the next pair of photos in the queue and prints them.
        :return: the outcome of the print job
        """

        photo_list = self._queue.get_photos()
        edit_list = self._queue.get_edits()
        joined_photo = self._editor.edit(photo_list, edit_list, self._folders.get_output_folder_path())
        try:
            self._printer.send(joined_photo, self._options)
        except PrinterError as e:
            return PrintResult(joined_photo, str(e))
        return PrintResult(joined_photo)
