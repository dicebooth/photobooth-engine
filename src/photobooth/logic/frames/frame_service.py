from photobooth.logic.frames.frame_catalog import FrameCatalog
from photobooth.logic.frames.frame_compositor import FrameCompositor
from photobooth.logic.settings.settings_models import FrameSettings


class FrameService:
    """
    FrameService decides which frame (effect) to apply to a photo and applies it.

    It is completely headless: it never shows a preview and never asks the user
    anything. The presentation layer asks for the strategy, the frame to apply
    and renders the previews when needed.
    """

    # Strategy used when no frame is configured in settings and more than one
    # frame is available in the assets folder.
    DEFAULT_STRATEGY = 'random'

    def __init__(self, catalog: FrameCatalog, compositor: FrameCompositor, settings: FrameSettings,
                 fallback_strategy: str = None):
        self._catalog = catalog
        self._compositor = compositor
        self._settings = settings
        self._frame_list = catalog.names()
        self._single_frame = catalog.is_single()
        self._fallback_strategy = fallback_strategy or self.DEFAULT_STRATEGY
        self._random_frame_index = 0

    def strategy(self) -> str:
        """
        Method which returns the frame strategy to follow:
        'configured' if a frame is set in settings, 'single' if only one frame
        is available, otherwise the fallback strategy ('random' by default,
        'manual' if the user has to choose).
        """

        if self._settings.frame_name:
            return 'configured'
        if self._single_frame:
            return 'single'
        return self._fallback_strategy

    def available_frames(self) -> list:
        """
        Method which returns the names of the available frames.
        """

        return list(self._frame_list)

    def configured_frame_name(self) -> str:
        """
        Method which returns the configured frame name normalized with the .png
        extension (empty string if no frame is configured).
        """

        frame_name = self._settings.frame_name
        if not frame_name:
            return ''
        if frame_name.endswith('.png'):
            return frame_name
        return frame_name + '.png'

    def next_frame_name(self) -> str:
        """
        Method which returns the next frame name according to the strategy:
        configured frame if set, the only available frame if single,
        otherwise the next frame in the consecutive rotation.
        """

        if self._settings.frame_name:
            return self.configured_frame_name()

        if self._single_frame:
            return self._frame_list[0] + '.png'

        frame_name = self._frame_list[self._random_frame_index]
        self._random_frame_index = (self._random_frame_index + 1) % len(self._frame_list)
        return frame_name + '.png'

    def frame_path(self, frame_name: str) -> str:
        """
        Method which returns the path of the given frame.
        """

        return self._catalog.path_of(frame_name)

    def should_preview(self) -> bool:
        """
        Method which returns True if the edited photo has to be confirmed by the
        user before going on.
        """

        return self._settings.preview_post_frame

    def compose(self, photo_path: str, frame_name: str):
        """
        Method which returns the photo edited with the given frame, without saving it.
        :param photo_path: photo path
        :param frame_name: frame name
        :return: edited photo (PIL image)
        """

        return self._compositor.compose(photo_path, self._catalog.path_of(frame_name))
