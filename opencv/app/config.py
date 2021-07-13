"""Handle configuration data."""

import dataclasses
import typing as t

import toml

PATHS = ["config.toml"]

def load_data(paths: t.Iterable[str]) -> t.Mapping[str, t.Any]:
    """Load data from all provided paths.
    
    Later paths have shallow key priority.
    """
    data = {}
    for path in paths:
        with open(path, "rt", encoding="utf-8") as fp:
            data.update(toml.load(fp))
    return data

# Raw, unfiltered config data
raw = load_data(PATHS)

# Schemas of fixed, expected, data structures.
# Provides fast-failing upon loading of this config module,
# rather than runtime failure upon key access
@dataclasses.dataclass()
class PhotoConfig:
    """PhotoConfig Schema.
    
    Usually not custom instantiated."""

    timeformat: str
    names: t.Mapping[str, str]

photo = PhotoConfig(raw["photo"]["timeformat"], dict(raw["photo"]["names"]))

@dataclasses.dataclass()
class WebConfig:
    """WebConfig Schema."""

    threshold: int

web = WebConfig(raw["web"]["threshold"])

@dataclasses.dataclass()
class ScaleConfig:
    """ScaleConfig Schema."""

    port: str
    baudrate: int
    timeout: float

    pause: float

scale = ScaleConfig(raw["scale"]["port"], raw["scale"]["baudrate"], raw["scale"]["timeout"], raw["scale"]["pause"])