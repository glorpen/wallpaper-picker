import json
import os
import pathlib
import shutil
import signal
import subprocess
import typing
from os import environ

from daemon import DaemonContext
from daemon.pidfile import PIDLockFile

from glorpen.wallpaper_picker.image import Wallpaper
from glorpen.wallpaper_picker.screen import MonitorInspector, Output
from glorpen.wallpaper_picker.wallpaper import PictureWriter


class SwayMonitorInspector(MonitorInspector):
    def get_screens(self) -> tuple[Output, ...]:
        ret = []
        for data in json.loads(subprocess.check_output(["swaymsg", "-t", "get_outputs"])):
            rect = data["rect"]
            scale = data["scale"]
            ret.append(Output(
                name=data["name"],
                flip=None,
                x=round(rect["x"] * scale),
                y=round(rect["y"] * scale),
                width=round(rect["width"] * scale),
                height=round(rect["height"] * scale),
            ))
        return tuple(ret)


class SwaybgPictureWriter(PictureWriter):
    _xdg_runtime_dir = pathlib.Path(environ.get("XDG_RUNTIME_DIR")) / "wallpaper-picker"
    _pid_file = _xdg_runtime_dir / "writer.pid"
    _image_dir = _xdg_runtime_dir / "images"

    def connect(self):
        self._xdg_runtime_dir.mkdir(exist_ok=True)

    def write(self, wallpapers: typing.Iterable[Wallpaper]):
        if self._image_dir.exists():
            shutil.rmtree(self._image_dir)
        self._image_dir.mkdir()

        args = ["swaybg"]
        for index, wallpaper in enumerate(wallpapers):
            picture_for_mon = self._image_manipulator.resize_image(wallpaper)
            resized_image = self._image_dir / f"{index}.png"
            picture_for_mon.save(resized_image, "PNG")

            args.extend([
                "-o", wallpaper.monitor.name,
                "-i", str(resized_image),
                "-m", "fill"
            ])

        if self._pid_file.exists():
            try:
                os.kill(int(self._pid_file.read_text().strip()), signal.SIGKILL)
            except Exception as e:
                self.logger.exception(e)
            finally:
                self._pid_file.unlink()

        pid = os.fork()
        if pid == 0:
            with DaemonContext(working_directory=self._xdg_runtime_dir, pidfile=PIDLockFile(self._pid_file)):
                os.execlp(args[0], *args)
