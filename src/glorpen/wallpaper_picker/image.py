import dataclasses
import logging
import os
import pathlib
import random
import typing

import PIL.Image
import xattr

from glorpen.wallpaper_picker.models import Offset, Size
from glorpen.wallpaper_picker.screen import Output


@dataclasses.dataclass
class Wallpaper:
    path: pathlib.Path
    poi: typing.Optional[Offset]
    monitor: Output

    def __repr__(self):
        return f'<Wallpaper: {self.path.name}>'


class ImageManipulator:

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

    def resize_image(self, wallpaper: Wallpaper) -> PIL.Image:
        image = PIL.Image.open(wallpaper.path)
        # image_size = Size(*image.size)

        req_mode = "RGBA"
        image = image if image.mode == req_mode else image.convert(req_mode)

        # find Point of Interest to later center on
        poi = wallpaper.poi
        if poi is None:
            self.logger.debug("No POI - will center image")
            poi = Offset(x=round(0.5 * image.width), y=round(0.5 * image.height))

        self.logger.debug("POI is at %r on %r", poi, wallpaper)

        # we should take image dimension that is smallest
        # and make it ratio value
        ratio = min(image.width / wallpaper.monitor.width, image.height / wallpaper.monitor.height)

        cropped_size = Size(
            width=round(ratio * wallpaper.monitor.width),
            height=round(ratio * wallpaper.monitor.height)
        )

        # center cropped box on poi and crop image
        # coords are based on original image
        offset = Offset(x=0, y=0)

        for dim, offset_dim in [("width", "x"), ("height", "y")]:
            half = getattr(cropped_size, dim) / 2
            o = max(getattr(poi, offset_dim) - half, 0)
            overflow = max(getattr(cropped_size, dim) + o - getattr(image, dim), 0)
            o -= overflow
            setattr(offset, offset_dim, round(o))

        self.logger.debug(f"offset {offset}")

        image = image.crop((offset.x, offset.y, offset.x + cropped_size.width, offset.y + cropped_size.height))

        if wallpaper.monitor.flip == "x":
            image = image.transpose(PIL.Image.FLIP_LEFT_RIGHT)
        elif wallpaper.monitor.flip == "y":
            image = image.transpose(PIL.Image.FLIP_TOP_BOTTOM)

        image = image.resize((wallpaper.monitor.width, wallpaper.monitor.height), resample=PIL.Image.LANCZOS)

        return image


class Attr:
    _xattr_poi = "user.glorpen.wallpaper.poi"
    _xattr_offensive = "user.glorpen.wallpaper.offensive"

    def get_poi(self, path: pathlib.Path):
        try:
            poi = xattr.get(path, self._xattr_poi)
            return Offset(*(int(i) for i in poi.split(b"x")))
        except OSError:
            return None

    def set_poi(self, path: pathlib.Path, poi: typing.Optional[Offset]):
        if poi:
            xattr.set(path, self._xattr_poi, f"{poi.x}x{poi.y}")
        else:
            try:
                xattr.remove(path, self._xattr_poi)
            except OSError:
                pass

    def set_offensive(self, path: pathlib.Path, value: typing.Optional[bool]):
        if value is None:
            try:
                xattr.remove(path, self._xattr_offensive)
            except OSError:
                pass
        else:
            xattr.set(path, self._xattr_offensive, str(value))

    def is_offensive(self, path: pathlib.Path):
        try:
            value = xattr.get(path, self._xattr_offensive)
            return value == b'True'
        except OSError:
            return False


class ImageChooser:
    def __init__(
            self,
            attr: Attr,
            wallpaper_dir: typing.Optional[pathlib.Path] = None
    ):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

        self._attr = attr

        if wallpaper_dir is None:
            self._wallpaper_dir = pathlib.Path(os.environ.get("HOME")) / "wallpapers"
        else:
            self._wallpaper_dir = wallpaper_dir

    def get_file(self, name: pathlib.Path):
        return self._wallpaper_dir / name

    def choose_wallpaper_files(self, count: int, with_offensive: bool):
        self.logger.info("Finding wallpapers")

        def _only_approved_file(x: pathlib.Path):
            return x.is_file() and (with_offensive or not self._attr.is_offensive(x))

        files = list(filter(_only_approved_file, self._wallpaper_dir.iterdir()))
        return random.choices(files, k=count)
