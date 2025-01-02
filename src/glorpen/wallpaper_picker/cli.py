#!/usr/bin/env python
import argparse
import functools
import itertools
import logging
import os
import pathlib

from glorpen.wallpaper_picker.image import ImageChooser, Attr, ImageManipulator, Wallpaper
from glorpen.wallpaper_picker.models import Offset


def backend_sway(ns):
    from glorpen.wallpaper_picker.backend.wayland import SwayMonitorInspector, SwaybgPictureWriter
    image_manipulator = ImageManipulator()
    return SwayMonitorInspector(), SwaybgPictureWriter(image_manipulator)


def backend_xorg(ns):
    from glorpen.wallpaper_picker.backend.xorg import XorgMonitorInspector, XorgPictureWriter
    image_manipulator = ImageManipulator()
    display = ns.display
    return XorgMonitorInspector(display=display), XorgPictureWriter(image_manipulator=image_manipulator,
                                                                    display=display)


backends = {
    "sway": backend_sway,
    "xorg": backend_xorg,
}


def update_wallpaper(backend_factory, attr: Attr, image_chooser: ImageChooser, offensive: bool = False):
    monitor_inspector, picture_writer = backend_factory()

    monitor_inspector.connect()
    try:
        screens = monitor_inspector.get_screens()
        wallpaper_files = image_chooser.choose_wallpaper_files(len(screens), offensive)
        wallpapers = []
        for output, wallpaper_file in itertools.zip_longest(screens, wallpaper_files):
            wallpapers.append(Wallpaper(
                path=wallpaper_file,
                monitor=output,
                poi=attr.get_poi(wallpaper_file)
            ))

        picture_writer.connect()
        try:
            picture_writer.write(wallpapers)
        finally:
            picture_writer.disconnect()

    finally:
        monitor_inspector.disconnect()


def to_offset(data: str):
    if data.lower() in ["none", "unset"]:
        return False
    return Offset(*(int(i) for i in data.split(",")))


def to_optional_bool(data: str):
    if data.lower() in ["none", "unset"]:
        return None
    return data.lower() in ["y", "yes", "1", "t"]


def cli_update_wallpaper(ns, attr, image_chooser: ImageChooser):
    update_wallpaper(
        backend_factory=functools.partial(ns.backend, ns=ns),
        offensive=ns.offensive,
        attr=attr,
        image_chooser=image_chooser
    )


def print_info_for_path(p: pathlib.Path, attr: Attr):
    poi = attr.get_poi(p)
    is_offensive = attr.is_offensive(p)

    print(f"Details for image {p}")
    if poi:
        print(f"POI: x:{poi.x}, y:{poi.y}")
    else:
        print("POI: not set")
    print(f"Offensive: {'yes' if is_offensive else 'no'}")


def cli_attr_set(ns, attr: Attr, image_chooser: ImageChooser):
    p = image_chooser.get_file(ns.image.expanduser())

    if ns.poi is False:
        attr.set_poi(p, None)
    elif ns.poi is not None:
        attr.set_poi(p, ns.poi)

    if ns.offensive is not None:
        attr.set_offensive(p, ns.offensive)

    print_info_for_path(p, attr)


def cli_attr_get(ns, attr, image_chooser: ImageChooser):
    p = image_chooser.get_file(ns.image.expanduser())
    print_info_for_path(p, attr)


def run():
    p = argparse.ArgumentParser("wallpaper-picker")
    p.add_argument("-v", "--verbose", action="count", default=0)
    p.add_argument(
        "--wallpaper-dir", "-w", help="Path to wallpapers directory, defaults to ~/wallpapers",
        default=None, type=pathlib.Path
    )
    sp = p.add_subparsers()
    pp = sp.add_parser("wallpaper")
    pp.set_defaults(func=cli_update_wallpaper)

    default_backend = "xorg"
    if os.environ.get("XDG_SESSION_TYPE") == "wayland":
        default_backend = "sway"

    pp.add_argument("--backend", "-b", help="Backend to use", default=default_backend,
                    choices=list(sorted(backends.keys())), type=backends.get)
    pp.add_argument("--display", "-d", help="Display to use, defaults to $DISPLAY, only for XOrg backend")
    pp.add_argument("--offensive", "-o", help="Include images marked as offensive", action="store_true", default=False)

    pp = sp.add_parser("attr-set")
    pp.set_defaults(func=cli_attr_set)
    pp.add_argument("image", type=pathlib.Path)
    pp.add_argument("--poi", help="Set point of interest (X,Y or none)", default=None, type=to_offset)
    pp.add_argument("--offensive", help="Mark as offensive or not", default=None, type=to_optional_bool)

    pp = sp.add_parser("attr-get")
    pp.set_defaults(func=cli_attr_get)
    pp.add_argument("image", type=pathlib.Path)

    ns = p.parse_args()

    levels = [logging.ERROR, logging.INFO, logging.DEBUG]
    logging.basicConfig(level=levels[min(ns.verbose, len(levels) - 1)])

    if not hasattr(ns, "func"):
        p.print_help()
        p.exit(1)

    attr = Attr()
    image_chooser = ImageChooser(wallpaper_dir=ns.wallpaper_dir.expanduser() if ns.wallpaper_dir else None, attr=attr)
    ns.func(ns, attr=attr, image_chooser=image_chooser)
