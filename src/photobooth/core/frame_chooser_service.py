class FrameChooserService:
    """
    FrameChooserService decides which frame (effect) to apply to a photo.

    It is completely headless: it never shows a preview and never asks the user
    anything. The presentation layer drives it through the gateway, asking for
    the strategy, the frame to apply and rendering previews when needed.
    """

    # Strategy used when no frame is configured in settings and more than one
    # frame is available in the assets folder.
    DEFAULT_STRATEGY = 'random'

    def __init__(self, assets, configured_frame: str = '', fallback_strategy: str = None):
        self._assets = assets
        self._configured_frame = configured_frame
        self._frame_list = assets.get_corners_names()
        self._single_frame = assets.is_frame_single()
        self._fallback_strategy = fallback_strategy or self.DEFAULT_STRATEGY
        self._random_frame_index = 0

    def strategy(self) -> str:
        """
        Method which returns the frame strategy to follow:
        'configured' if a frame is set in settings, 'single' if only one frame
        is available, otherwise the fallback strategy ('random' by default,
        'manual' if the user has to choose).
        """

        if self._configured_frame:
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

        if not self._configured_frame:
            return ''
        if self._configured_frame.endswith('.png'):
            return self._configured_frame
        return self._configured_frame + '.png'

    def next_frame_name(self) -> str:
        """
        Method which returns the next frame name according to the strategy:
        configured frame if set, the only available frame if single,
        otherwise the next frame in the consecutive rotation.
        """

        if self._configured_frame:
            return self.configured_frame_name()

        if self._single_frame:
            return self._frame_list[0] + '.png'

        frame_name = self._frame_list[self._random_frame_index]
        self._random_frame_index = (self._random_frame_index + 1) % len(self._frame_list)
        return frame_name + '.png'