import argparse
import logging
import pathlib

from glorpen.wallpaper_picker.cli import cli_update_wallpaper, cli_attr_set, cli_attr_get, yes_no, to_offset
from glorpen.wallpaper_picker.image import Attr, ImageChooser

logging.basicConfig(level=logging.DEBUG)

p = argparse.ArgumentParser("wallpaper-picker")
p.add_argument(
    "--wallpaper-dir", "-w", help="Path to wallpapers directory, defaults to ~/wallpapers",
    default=None, type=pathlib.Path
)
sp = p.add_subparsers()
pp = sp.add_parser("wallpaper")
pp.set_defaults(func=cli_update_wallpaper)
pp.add_argument("--display", "-d", help="Display to use, defaults to $DISPLAY")
pp.add_argument("--offensive", "-o", help="Include images marked as offensive", action="store_true", default=False)

pp = sp.add_parser("attr-set")
pp.set_defaults(func=cli_attr_set)
pp.add_argument("image", type=pathlib.Path)
pp.add_argument("--poi", help="Set point of interest (X:Y or none)", default=None, type=to_offset)
pp.add_argument("--offensive", help="Mark as offensive or not", default=None, type=yes_no)

pp = sp.add_parser("attr-get")
pp.set_defaults(func=cli_attr_get)
pp.add_argument("image", type=pathlib.Path)

ns = p.parse_args()

attr = Attr()
image_chooser = ImageChooser(wallpaper_dir=ns.wallpaper_dir.expanduser() if ns.wallpaper_dir else None, attr=attr)
ns.func(ns, attr=attr, image_chooser=image_chooser)
