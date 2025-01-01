import abc
import dataclasses
import logging
import typing

from glorpen.wallpaper_picker.models import Offset, Size

Flip = typing.Optional[typing.Literal['x', 'y']]


@dataclasses.dataclass
class Output(Offset, Size):
    name: str
    flip: Flip


class MonitorInspector(abc.ABC):

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)

    def connect(self):
        pass

    def disconnect(self):
        pass

    @abc.abstractmethod
    def get_screens(self) -> tuple[Output, ...]:
        raise NotImplementedError()
