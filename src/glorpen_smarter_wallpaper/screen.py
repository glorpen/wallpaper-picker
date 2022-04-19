import dataclasses
import logging
import os
import typing

import xcffib
import xcffib.randr
import xcffib.xproto
from xcffib.randr import Rotation as RandrRotation

from glorpen_smarter_wallpaper.models import Offset, Size

Flip = typing.Optional[typing.Literal['x', 'y']]


def _randr_rotation_as_flip(rotation) -> Flip:
    if rotation & RandrRotation.Reflect_X:
        return "x"
    if rotation & RandrRotation.Reflect_Y:
        return "y"
    return None


@dataclasses.dataclass
class Output(Offset, Size):
    name: str
    flip: Flip


def get_atom_id(con, name):
    return con.core.InternAtom(False, len(name), name).reply().atom


class MonitorInspector:
    _root = None
    _ext_r = None
    _conn: typing.Optional[xcffib.Connection]
    _display: str

    def __init__(self, display=None):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

        self._display = display or os.environ.get("DISPLAY")

    def connect(self):
        self._conn = xcffib.connect(self._display)
        self._ext_r = self._conn(xcffib.randr.key)

        self._root = self._conn.get_setup().roots[0].root

    def disconnect(self):
        self._conn.disconnect()
        self._ext_r = self._root = None

    def get_screens(self) -> tuple[Output]:
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
