import abc
import logging
import typing

from glorpen.wallpaper_picker.image import Wallpaper, ImageManipulator


class PictureWriter(abc.ABC):

    def __init__(self, image_manipulator: ImageManipulator):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self._image_manipulator = image_manipulator

    def connect(self):
        pass

    @abc.abstractmethod
    def write(self, wallpapers: typing.Iterable[Wallpaper]):
        raise NotImplementedError()

    def disconnect(self):
        pass
