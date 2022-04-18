import dataclasses
import logging
import pathlib
import typing

import PIL.Image
import xattr

from glorpen_smarter_wallpaper.models import Offset, Size
from glorpen_smarter_wallpaper.screen import Output


@dataclasses.dataclass
class Wallpaper:
    path: pathlib.Path
    poi: typing.Optional[Offset]
    monitor: Output


class ImageManipulator:

    # TODO: is_offensive
    # TODO: is_safe

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__qualname__)

    def resize_image(self, wallpaper: Wallpaper) -> PIL.Image:
        image = PIL.Image.open(wallpaper.path)

        req_mode = "RGBA"
        image = image if image.mode == req_mode else image.convert(req_mode)

        # find Point of Interest to later center on
        poi = wallpaper.poi if wallpaper.poi else Offset(x=round(0.5 * image.width), y=round(0.5 * image.height))

        self.logger.debug("POI is at %r on %r", poi, wallpaper)

        # we should take image dimension that is smallest
        # and make it ratio value
        ratio = min(image.width / wallpaper.monitor.width, image.height / wallpaper.monitor.height)

        # numpy and multiplying arrays?
        cropped_size = Size(width=round(ratio * wallpaper.monitor.width),
            height=round(ratio * wallpaper.monitor.height))

        # center cropped box on poi and crop image
        # coords are based on original image
        offset = Offset(x=0, y=0)

        for dim in ["width", "height"]:
            half = getattr(cropped_size, dim) / 2
            o = max(getattr(poi, "x" if dim == "width" else "y") - half, 0)
            overflow = max(getattr(cropped_size, dim) + o - getattr(image, dim), 0)
            o -= overflow
            setattr(offset, dim, o)

        image = image.crop((offset.x, offset.y, offset.x + cropped_size.width, offset.y + cropped_size.height))
        image = image.resize((wallpaper.monitor.width, wallpaper.monitor.height), resample=PIL.Image.LANCZOS)

        return image


class Attr:
    _xattr_poi = "user.glorpen.wallpaper.poi"
    _xattr_offensive = "user.glorpen.wallpaper.offensive"

    def get_poi(self, path: pathlib.Path):
        try:
            poi = xattr.get(path, self._xattr_poi)
            return Offset(*(int(i) for i in poi.split("x")))
        except OSError:
            return None

    def set_poi(self, path: pathlib.Path, poi: Offset):
        xattr.set(path, self._xattr_poi, f"{poi.x}x{poi.y}")

    def set_offensive(self, path: pathlib.Path, value: bool):
        xattr.set(path, self._xattr_poi, str(value))

    def is_offensive(self, path: pathlib.Path):
        try:
            value = xattr.get(path, self._xattr_offensive)
            return bool(value)
        except OSError:
            return False
