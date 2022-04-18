#!/usr/bin/env python
import ctypes
import dataclasses
import errno
import itertools
import logging
import os
import pathlib
import random
import re
import subprocess
import typing

libc = ctypes.CDLL("libc.so.6")

_getxattr = ctypes.CFUNCTYPE(
    ctypes.c_ssize_t, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_size_t, use_errno=True
)(('getxattr', libc))

logger = logging.getLogger("wallpaper")


def getxattr(path: pathlib.Path, key: str):
    buff = ctypes.create_string_buffer(0, 21)
    size = _getxattr(ctypes.c_char_p(str(path).encode()), ctypes.c_char_p(key.encode()),
        ctypes.cast(buff, ctypes.c_void_p), 20)
    if size < 0:
        if ctypes.get_errno() == errno.ENODATA:
            return None
        raise Exception(f"getxattr returned {os.strerror(ctypes.get_errno())}")
    return bytes(ctypes.string_at(buff, size))


@dataclasses.dataclass
class Size:
    width: int
    height: int


@dataclasses.dataclass
class Poi:
    x: int
    y: int


@dataclasses.dataclass
class Wallpaper:
    path: pathlib.Path
    poi: typing.Optional[Poi]
    monitor: Size
    size: Size


re_xrandr_monitor = re.compile(r"\s*[0-9]+:\s*.*?\s*([0-9]+)/[0-9]+x([0-9]+)/[0-9]+\+.*", re.MULTILINE)


def get_monitors():
    logger.info("Finding active monitors")
    data = subprocess.check_output(["xrandr", "--listactivemonitors"]).decode()
    for i in re_xrandr_monitor.finditer(data):
        yield Size(width=int(i.group(1)), height=int(i.group(2)))


def choose_wallpaper_files(count: int):
    logger.info("Finding wallpapers")
    wallpaper_dir = pathlib.Path(os.environ.get("HOME")) / "wallpapers"

    def _only_file(x: pathlib.Path):
        return x.is_file()

    files = list(filter(_only_file, wallpaper_dir.iterdir()))
    return random.choices(files, k=count)


def get_poi(path: pathlib.Path):
    poi_data = getxattr(path, "user.glorpen.wallpaper.poi")
    if poi_data:
        return Poi(*tuple(int(v) for v in poi_data.decode().split("x")))
    return None


def get_wallpapers(files: typing.Iterable[pathlib.Path], monitors: typing.Iterable[Size]):
    logger.info("Collecting wallpapers info")
    for path, monitor in itertools.zip_longest(files, monitors):
        yield Wallpaper(
            path=path,
            poi=get_poi(path),
            monitor=monitor,
            size=get_image_size(path)
        )


def get_image_size(path: pathlib.Path):
    return Size(*tuple(int(i) for i in subprocess.check_output([
        "convert", str(path), "-format", "%[w]:%[h]", "info:"
    ]).split(b":")))


def convert_image(wallpaper: Wallpaper, target: pathlib.Path):
    # find Point of Interest to later center on
    if wallpaper.poi is None:
        poi = Poi(x=int(0.5 * wallpaper.size.width), y=int(0.5 * wallpaper.size.height))
    else:
        poi = wallpaper.poi

    logger.info(f"Using poi {poi} for {wallpaper.path}")

    # we should take image dimension that is smallest
    # and make it ratio value
    ratio = min(wallpaper.size.width / wallpaper.monitor.width, wallpaper.size.height / wallpaper.monitor.height)

    # numpy and multiplying arrays?
    cropped_size = Size(round(ratio * wallpaper.monitor.width), round(ratio * wallpaper.monitor.height))

    # center cropped box on poi and crop image
    # coords are based on original image
    offset = Size(0, 0)

    for dim in ["width", "height"]:
        half = getattr(cropped_size, dim) / 2
        o = max(getattr(poi, "x" if dim == "width" else "y") - half, 0)
        overflow = max(getattr(cropped_size, dim) + o - getattr(wallpaper.size, dim), 0)
        o -= overflow
        setattr(offset, dim, o)

    logger.info(f"Cropping {wallpaper.path} to {target}")

    subprocess.check_call([
        "convert", "-crop",
        f"{cropped_size.width}x{cropped_size.height}+{offset.width}+{offset.height}",
        str(wallpaper.path),
        target
    ])


def prepare_wallpapers(wallpapers: typing.Iterable[Wallpaper]):
    runtime_path = pathlib.Path(os.environ.get("XDG_RUNTIME_DIR")) / "wallpapers"
    runtime_path.mkdir(exist_ok=True)
    for i, w in enumerate(wallpapers):
        extension = w.path.suffix.lstrip('.')
        target = runtime_path / f"{i}.{extension}"
        convert_image(w, target)
        yield target


def set_wallpapers(paths: typing.Iterable[pathlib.Path]):
    logger.info("Setting wallpapers")
    subprocess.check_call(["feh", "--bg-fill", "--no-fehbg", "--"] + list(str(p) for p in paths))


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    monitors = list(get_monitors())
    wallpapers = list(get_wallpapers(choose_wallpaper_files(len(monitors)), monitors))
    prepared = list(prepare_wallpapers(wallpapers))
    set_wallpapers(prepared)
