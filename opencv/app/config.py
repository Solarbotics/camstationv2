"""Handle configuration data."""

import dataclasses
import typing as t

import toml

PATHS = ["config.toml"]


def load_data(paths: t.Iterable[str]) -> t.Mapping[str, t.Any]:
    """Load data from all provided paths.

    Later paths have shallow key priority.
    """
    data: t.MutableMapping[str, t.Any] = {}
    for path in paths:
        with open(path, "rt", encoding="utf-8") as fp:
            data.update(toml.load(fp))
    return data


# Raw, unfiltered config data
raw = load_data(PATHS)

#     # special annotations:
#     # mapping: not neccesarily need to be treated special
#     # sequence/iterable: not neccesarily need to be special
#     #   all config should be immutable anyways so we can just have
#     #   views from the raw data.
#     #   Ideally though we would have some checking
#     #   since thats the whole point of this config module
#     #   is to have some fail-fast behaviour.
#     #   even without it we would still have shallow name checking but thats it
#     # SOLUTION:
#     #   check raw object using isinstance(raw[key], anno_type);
#     #   throw error if false
#     #   provides fast-failing while making shallow reference to the raw data
#     # isinstance works with stuff like t.Mapping too
#     # Config-type class


def is_sub(cls: t.Any, other: type) -> bool:
    """Determine if the first argument is a subclass of the second.

    Returns False if the first argument is not a class,
    instead of throwing an exception.
    """
    try:
        return issubclass(cls, other)
    except TypeError:
        return False


MetaT = t.TypeVar("MetaT", bound=type)


class DataMeta(type):
    """Config metaclass.

    Instance classes are automatically decorated as dataclasses."""

    def __new__(
        cls: t.Type[MetaT],
        name: str,
        bases: t.Tuple[type, ...],
        namespace: t.Dict[str, t.Any],
        **kwargs: t.Any
    ) -> MetaT:
        """Create a new Config class."""
        new_class = type.__new__(cls, name, bases, namespace)
        new_class = dataclasses.dataclass(**kwargs)(new_class)
        return new_class


ConfigT = t.TypeVar("ConfigT", bound="Config")


class Config(metaclass=DataMeta):
    """Base Config class.

    Encodes behaviour for converting from raw data to an object,
    based on annotations.

    Expects the class to have an init method such as created by dataclasses.
    """

    def __init__(self, **kwargs: t.Any) -> None:
        """Initialize attributes from kwargs.

        Should be overridden by metaclass,
        provided to sooth mypy.
        """
        for name, value in kwargs.items():
            setattr(self, name, value)

    @classmethod
    def from_raw(cls: t.Type[ConfigT], raw: t.Mapping[str, t.Any]) -> ConfigT:
        """Construct the config class from raw mapping data."""
        data = {
            attr: raw[attr] if not is_sub(anno, Config) else anno.from_raw(raw[attr])
            for attr, anno in cls.__annotations__.items()
        }
        # Verify data
        # for attr, value in data.items():
        #     if not isinstance(value, cls.__annotations__[attr]):
        #         raise TypeError(
        #             f"Data for {cls}.{attr} is of type {type(value)},"
        #             f" expected {cls.__annotations__[attr]}."
        #         )
        return cls(**data)


@dataclasses.dataclass()
class FilesConfig:
    """FilesConfig Schema."""

    timeformat: str


files = FilesConfig(raw["files"]["timeformat"])

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


scale = ScaleConfig(
    raw["scale"]["port"],
    raw["scale"]["baudrate"],
    raw["scale"]["timeout"],
    raw["scale"]["pause"],
)

Colour = t.Tuple[int, int, int]


@dataclasses.dataclass()
class ColoursConfig:

    red: Colour
    blue: Colour
    green: Colour


@dataclasses.dataclass()
class CameraConfig:
    """CameraConfig Schema."""

    colours: ColoursConfig


camera = CameraConfig(
    ColoursConfig(
        **{name: tuple(colour) for name, colour in raw["camera"]["colours"].items()}  # type: ignore
    )
)


class PathsConfig(Config):

    photos: str
    data: str

class ProcessCameraConfig(Config):

    wait: int


class ProcessConfig(Config):
    """ProcessConfig Schema."""

    data_name: str
    paths: PathsConfig
    camera: ProcessCameraConfig

    cameraMatrix: str
    cameraScaleMatrix: str
    cameraDistortionMatrix: str


process = ProcessConfig.from_raw(raw["process"])


class LightsConfig(Config):
    """LightsConfig Schema."""

    pin: int


lights = LightsConfig.from_raw(raw["lights"])


class MeasureConfig(Config):
    """MeasureConfig Schema."""

    bus: int
    address: int

    range: int


measure = MeasureConfig.from_raw(raw["measure"])
