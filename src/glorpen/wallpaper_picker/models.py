import dataclasses
import pathlib
import typing


@dataclasses.dataclass
class Offset:
    x: int
    y: int

    def __repr__(self):
        return f'<Offset: {self.x}:{self.y}>'


@dataclasses.dataclass
class Size:
    width: int
    height: int

    def __repr__(self):
        return f'<Size: {self.width}x{self.height}>'

