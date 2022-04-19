#!/usr/bin/env python
import itertools
import pathlib

from glorpen.wallpaper_picker.image import ImageChooser, Attr, ImageManipulator, Wallpaper
from glorpen.wallpaper_picker.models import Offset
from glorpen.wallpaper_picker.screen import MonitorInspector
from glorpen.wallpaper_picker.wallpaper import PictureWriter


def update_wallpaper(attr: Attr, image_chooser: ImageChooser, display: str = None, offensive: bool = False):
    image_manipulator = ImageManipulator()
    monitor_inspector = MonitorInspector(display=display)
    picture_writer = PictureWriter(image_manipulator=image_manipulator, display=display)

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
    if data.lower() == "none":
        return None
    return Offset(*(int(i) for i in data.split(":")))


def cli_update_wallpaper(ns, attr, image_chooser: ImageChooser):
    update_wallpaper(
        display=ns.display,
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

    if ns.poi is None:
        if ns.remove_poi:
            print("Clearing POI.")
            attr.set_poi(p, None)
    else:
        attr.set_poi(p, ns.poi)

    if ns.offensive is not None:
        attr.set_offensive(p, ns.offensive)

    print_info_for_path(p, attr)


def cli_attr_get(ns, attr, image_chooser: ImageChooser):
    p = image_chooser.get_file(ns.image.expanduser())
    print_info_for_path(p, attr)


def yes_no(v: str):
    return v.lower() in ["y", "yes", "1", "t"]
