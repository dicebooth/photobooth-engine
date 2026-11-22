import os

from PIL import Image

from photobooth.api.printing.hotfolder_printer import HotfolderPrinter
from photobooth.logic.editing.editor_service import EditorService
from photobooth.logic.frames.frame_compositor import FrameCompositor
from photobooth.logic.printing.ports import PrintFailed
from photobooth.logic.printing.print_options_resolver import PrintOptionsResolver
from photobooth.logic.printing.print_service import PrintService
from photobooth.logic.printing.queue_service import QueueService
from photobooth.logic.session.folder_manager import FolderManager

ASSETS_DIR = os.path.join(os.path.dirname(__file__), 'assets')
SAMPLE_PHOTO = os.path.join(ASSETS_DIR, 'mock', 'photo.jpg')
SAMPLE_FRAME = os.path.join(ASSETS_DIR, 'frame.png')


def _never_called():
    raise AssertionError('the printer must not be queried')


# ------------------------------------------------------------------ resolver

def test_qw410_with_4x3_uses_dnp_media_and_cutter_without_asking_the_printer():
    resolver = PrintOptionsResolver('DNP-QW410', '4x3', {'user': 'option'})

    assert resolver.resolve(_never_called) == ['-o', 'media=dnp4x6', '-o', 'Cutter=2Inch']


def test_qw410_with_4x6_is_not_special_cased():
    resolver = PrintOptionsResolver('DNP-QW410', '4x6', {'fit-to-page': 'False'})

    assert resolver.resolve(_never_called) == ['-o', 'fit-to-page=False']


def test_user_options_win_over_probing():
    resolver = PrintOptionsResolver('any', '4x6', {'a': 1, 'b': 'x'})

    assert resolver.resolve(_never_called) == ['-o', 'a=1', '-o', 'b=x']


def test_first_supported_fit_option_is_used():
    resolver = PrintOptionsResolver('any', '4x6')

    # 'StpiShrinkOutput' comes before 'fit-to-page' in POSSIBLE_PRINTER_OPTIONS
    listing = 'fit-to-page/Fit: *True False\nStpiShrinkOutput/Shrink: Shrink Crop Expand'

    assert resolver.resolve(lambda: listing) == ['-o', 'StpiShrinkOutput=Shrink']


def test_no_supported_option_means_no_arguments():
    assert PrintOptionsResolver('any', '4x6').resolve(lambda: '') == []


# ------------------------------------------------------------ print service

class FakePrinter:
    def __init__(self, error=None):
        self.sent = []
        self._error = error

    def supported_options(self):
        return 'fit-to-page'

    def send(self, file_path, options):
        if self._error:
            raise self._error
        self.sent.append((file_path, options))


class FakeState:
    def __init__(self):
        self.queues = {'photos': [], 'edits': []}

    def load_queues(self):
        return {key: list(value) for key, value in self.queues.items()}

    def save_queues(self, photos, edits):
        self.queues = {'photos': list(photos), 'edits': list(edits)}


def _print_service(tmp_path, printer):
    folders = FolderManager(str(tmp_path))
    service = PrintService(QueueService(FakeState()), EditorService(FrameCompositor()), folders, printer,
                           PrintOptionsResolver('any', '4x6'))
    service.prepare()
    return service


def test_print_service_prints_a_pair_once_two_photos_are_queued(tmp_path):
    printer = FakePrinter()
    service = _print_service(tmp_path, printer)

    service.enqueue(SAMPLE_PHOTO, SAMPLE_FRAME, 1)
    assert not service.prints_pending()
    service.enqueue(SAMPLE_PHOTO, SAMPLE_FRAME, 1)
    assert service.prints_pending()

    result = service.print_next()

    assert result.ok
    assert printer.sent == [(result.photo_path, ['-o', 'fit-to-page=True'])]
    assert Image.open(result.photo_path).size == (2000, 3000)
    assert not service.prints_pending()


def test_print_service_reports_failures_instead_of_raising(tmp_path):
    service = _print_service(tmp_path, FakePrinter(error=PrintFailed('boom')))
    service.enqueue(SAMPLE_PHOTO, SAMPLE_FRAME, 2)

    result = service.print_next()

    assert not result.ok
    assert result.error == 'boom'
    assert os.path.exists(result.photo_path)


# ---------------------------------------------------------------- transports

def test_hotfolder_printer_copies_the_file(tmp_path):
    hotfolder = tmp_path / 'hot'
    hotfolder.mkdir()

    HotfolderPrinter(str(hotfolder)).send(SAMPLE_PHOTO, ['ignored'])

    assert os.listdir(hotfolder) == ['photo.jpg']


def test_hotfolder_printer_raises_if_the_folder_is_missing(tmp_path):
    printer = HotfolderPrinter(str(tmp_path / 'missing'))

    try:
        printer.send(SAMPLE_PHOTO, [])
    except PrintFailed as e:
        assert 'missing' in str(e)
    else:
        raise AssertionError('PrintFailed expected')
