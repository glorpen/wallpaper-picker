import dataclasses
import pathlib
import typing


@dataclasses.dataclass
class Offset:
    x: int
    y: int


@dataclasses.dataclass
class Size:
    width: int
    height: int

