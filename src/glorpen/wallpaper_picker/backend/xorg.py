import os
import typing

import xcffib
import xcffib.randr
import xcffib.xproto
from xcffib.randr import Rotation as RandrRotation

from glorpen.wallpaper_picker.image import Wallpaper, ImageManipulator
from glorpen.wallpaper_picker.screen import MonitorInspector, Output, Flip
from glorpen.wallpaper_picker.wallpaper import PictureWriter


def _randr_rotation_as_flip(rotation) -> Flip:
    if rotation & RandrRotation.Reflect_X:
        return "x"
    if rotation & RandrRotation.Reflect_Y:
        return "y"
    return None


def get_atom_id(con, name):
    return con.core.InternAtom(False, len(name), name).reply().atom


class XorgMonitorInspector(MonitorInspector):
    _root = None
    _ext_r = None
    _conn: typing.Optional[xcffib.Connection]
    _display: str

    def __init__(self, display=None):
        super().__init__()
        self._display = display or os.environ.get("DISPLAY")

    def connect(self):
        self._conn = xcffib.connect(self._display)
        self._ext_r = self._conn(xcffib.randr.key)

        self._root = self._conn.get_setup().roots[0].root

    def disconnect(self):
        self._conn.disconnect()
        self._ext_r = self._root = None

    def get_screens(self) -> tuple[Output, ...]:
        ret = []
        screen_resources = self._ext_r.GetScreenResources(self._root).reply()

        for output in screen_resources.outputs:
            output_info = self._ext_r.GetOutputInfo(output, 0).reply()

            # skip outputs without monitors
            if output_info.connection != xcffib.randr.Connection.Connected:
                continue

            if output_info.crtc > 0:
                crtc_info = self._ext_r.GetCrtcInfo(output_info.crtc, 0).reply()
                ret.append(Output(
                    name=output_info.name.raw.decode(),
                    x=crtc_info.x,
                    y=crtc_info.y,
                    width=crtc_info.width,
                    height=crtc_info.height,
                    flip=_randr_rotation_as_flip(crtc_info.rotation)
                ))

        return tuple(ret)


class XorgPictureWriter(PictureWriter):
    _atom_xrootmap = None
    _atom_esetroot = None
    _conn = None

    def __init__(self, image_manipulator: ImageManipulator, display=None):
        super().__init__(image_manipulator=image_manipulator)
        self._display = display or os.environ.get("DISPLAY")

    def connect(self):
        self._conn = xcffib.connect(display=self._display)

        # don't remove pixmap after disconnecting
        self._conn.core.SetCloseDownMode(xcffib.xproto.CloseDown.RetainPermanent)

        self._atom_xrootmap = get_atom_id(self._conn, "_XROOTPMAP_ID")
        self._atom_esetroot = get_atom_id(self._conn, "ESETROOT_PMAP_ID")

    def _get_root_window(self):
        return self._conn.get_setup().roots[0]

    def _get_old_pixmaps(self, window):
        """Returns unique pixmap ids"""
        pixmaps = set()
        for i in [self._atom_xrootmap, self._atom_esetroot]:
            v = self._conn.core.GetPropertyUnchecked(
                False,
                window,
                i,
                xcffib.xproto.Atom.PIXMAP,
                0,
                1
            ).reply().value.to_atoms()
            if v:
                pixmaps.add(v[0])
        return tuple(pixmaps)

    def _copy_images(self, wallpapers: typing.Iterable[Wallpaper], destination, root, depth):
        max_req_length = self._conn.get_maximum_request_length()  # counted as int32 - one pixel

        gc = self._conn.generate_id()
        self._conn.core.CreateGC(gc, root, 0, None)

        for wallpaper in wallpapers:
            block_height = wallpaper.monitor.height
            block_width = int(max_req_length / block_height)
            offset = 0
            picture_for_mon = self._image_manipulator.resize_image(wallpaper)
            while offset < wallpaper.monitor.width:
                if block_width + offset > wallpaper.monitor.width:
                    # last iteration, just recalculate block_width
                    block_width = wallpaper.monitor.width - offset
                crop_box = (offset, 0, offset + block_width, wallpaper.monitor.height)

                data = picture_for_mon.crop(crop_box).tobytes('raw', 'BGRA')

                self.logger.debug(
                    f"Copying cropped image ({crop_box[0]},{crop_box[1]}),({crop_box[2]},{crop_box[3]}) from {wallpaper!r}")

                self._conn.core.PutImage(
                    xcffib.xproto.ImageFormat.ZPixmap,
                    destination,
                    gc,
                    block_width,
                    block_height,
                    wallpaper.monitor.x + offset,
                    wallpaper.monitor.y,
                    0,
                    depth,
                    len(data),
                    data
                )

                offset += block_width

        self._conn.core.FreeGC(gc)

    def write(self, wallpapers: typing.Iterable[Wallpaper]):

        r = self._get_root_window()

        root = r.root
        depth = r.root_depth
        # visual = r.root_visual
        width = r.width_in_pixels
        height = r.height_in_pixels

        # just in case it differs
        old_pixmaps = self._get_old_pixmaps(root)

        picture = self._conn.generate_id()
        self._conn.core.CreatePixmap(depth, picture, root, width, height)

        self._copy_images(wallpapers, picture, root, depth)

        self._conn.core.ChangeWindowAttributes(root, xcffib.xproto.CW.BackPixmap, [picture])
        self._conn.core.ClearArea(0, root, 0, 0, 0, 0)

        self._conn.core.ChangeProperty(
            xcffib.xproto.PropMode.Replace,
            root,
            self._atom_xrootmap,
            xcffib.xproto.Atom.PIXMAP,
            32,
            1,
            [picture]
        )
        self._conn.core.ChangeProperty(
            xcffib.xproto.PropMode.Replace,
            root,
            self._atom_esetroot,
            xcffib.xproto.Atom.PIXMAP,
            32,
            1,
            [picture]
        )

        # free old pixmaps
        for p in old_pixmaps:
            self._conn.core.KillClient(p)

        # conn.core.FreePixmap(a)
        # self.conn.core.SetCloseDownMode(xcffib.xproto.CloseDown.RetainPermanent)

        self._conn.flush()

    def disconnect(self):
        self._conn.disconnect()
