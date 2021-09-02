"""Operate main camera station processes."""

import datetime
import json
import logging
import os
import pathlib
import subprocess
import time
import typing as t

from . import config
from . import devices
from . import files
from . import lights
from . import photo
from . import transfer

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def area(dimensions: t.Tuple[float, float]) -> float:
    """Area based on a (width, height) dimension pair."""
    return dimensions[0] * dimensions[1]


x = area((3, 2))

# (str, str) or (float, float)?
def read_bounds(threshold: int = 0) -> t.Tuple[float, float]:
    """Obtain the bounds provided by the camera station."""
    try:
        sizes = devices.get_camera().get_processed_frame(threshold=threshold)[1]
    except Exception as e:
        logger.error(e)
        size = (0.0, 0.0)
    else:
        main = sorted(sizes, key=area, reverse=True)[0] if sizes else (0.0, 0.0)
        size = (
            round(float(main[0]), config.camera.precision),
            round(float(main[1]), config.camera.precision),
        )
    return size


def format_bounds(bounds: t.Tuple[float, float]) -> str:
    """Create formatted string version of bounds."""
    p = config.camera.precision
    return f"{bounds[0]:.{p}f} cm x {bounds[1]:.{p}f} cm"


def read_weight(tare: t.Optional[float] = None) -> float:
    """Obtain the weight provided by the camera station.

    If no tare is provided, returns the raw value read."""
    try:
        with devices.get_scale() as sc:
            if tare is not None:
                weight = sc.obtain(tare)
            else:
                weight = sc.read()
    except Exception as e:
        logger.error(e)
        weight = 0.0
    else:
        weight = round(weight, config.scale.precision)
    return weight


def format_weight(weight: float) -> str:
    """Create formatted string version of weight."""
    p = config.scale.precision
    return f"{weight:.{p}f} kg"


def read_height(base: t.Optional[float] = None) -> float:
    """Obtain the height provided by the camera station."""
    try:
        with devices.get_sensor() as sensor:
            if base is not None:
                height = sensor.obtain(base)
            else:
                height = sensor.read()
    except Exception as e:
        logger.error(e)
        height = 0
    else:
        height = round(height, config.measure.precision)
    return height


def format_height(height: float) -> str:
    """Create formatted string version of height."""
    p = config.measure.precision
    return f"{height:.{p}f} cm"


def take_photos(
    folder: t.Union[str, pathlib.Path],
    query: str,
    use_timestamp: bool = True,
    timestamp: t.Optional[datetime.datetime] = None,
    format: str = None,
) -> t.List[str]:
    """Takes a set of photos, saving onto disk and returning base64 encodings."""
    try:
        photo_paths = devices.get_cameras().capture_image_set(
            folder=str(folder),
            use_timestamp=use_timestamp,
            timestamp=timestamp,
            format=format,
            query=query,
        )
    except Exception as e:
        logger.error(e)
        return []
    else:
        return [photo.encode_image(path) for path in photo_paths]


def collect_photos(query: str) -> t.List[str]:
    """Take a set of photos, saving into the appropriate folder based on query."""
    return take_photos(
        query=query,
        folder=files.query_folder(
            query,
            generic=config.process.paths.generic,
            parent=config.process.paths.data,
        ).joinpath(config.process.paths.photos),
        use_timestamp=False,
    )


def collect_data(
    query: t.Optional[str] = None,
    threshold: int = 0,
    base_depth: t.Optional[float] = None,
    tare: t.Optional[float] = None,
    timestamp: t.Optional[datetime.datetime] = None,
    override_height: t.Optional[float] = None,
) -> t.Mapping[str, object]:
    """Collect numerical data."""
    # Read bounds from undercamera
    size = read_bounds(threshold=threshold)
    if override_height is not None:
        height = override_height
    else:
        # Use overhead tech to get depth
        height = read_height(base=base_depth)
    # Read scale
    weight = read_weight(tare=tare)

    folder = files.query_folder(
        query,
        generic=config.process.paths.generic,
        parent=config.process.paths.data,
    )

    logger.debug(folder)

    file_name = files.data_name(
        name=config.process.data_name,
        query=query,
        folder=folder,
        extension="json",
        use_timestamp=False,
    )

    data = {
        "size": size,
        "weight": weight,
        "height": height,
        "time": files.format_timestamp(timestamp),
        "ilc": query,
    }

    with open(file_name, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    return data


def activate(*args: t.Any, **kwargs: t.Any) -> t.Mapping[str, object]:
    """Activate a round of the camera station."""

    # Save gathered data
    # Construct root folder
    ilc: str = kwargs.get("ilc", "unknown")

    # Common timestamp for all files
    now = datetime.datetime.now()

    data_folder = files.query_folder(
        ilc, generic=config.process.paths.generic, parent=config.process.paths.data
    )

    data = collect_data(
        query=ilc,
        threshold=kwargs.get("threshold", 0),
        base_depth=kwargs.get("base_depth", None),
        tare=kwargs.get("tare", None),
        timestamp=now,
        override_height=kwargs.get("height_override", None),
    )

    # Turn on underside ringlights to improve light conditions
    lights.Lights().ring().level = kwargs.get("light_level", config.lights.level)
    # Wait a bit for lights to turn on properly
    time.sleep(config.process.camera.wait)

    # Take photos
    encoded_images = take_photos(
        query=ilc,
        folder=data_folder.joinpath(config.process.paths.photos),
        use_timestamp=False,
    )

    # Turn off lights
    lights.Lights().ring().off()

    # Return data
    return {
        "message": "success",
        "valid": True,
        "photos": encoded_images,
        **data,
    }


def retrieve(ilc: str) -> t.Optional[t.Mapping[str, object]]:
    """Retrieve data that was previously saved with the specified ILC."""
    data_folder = pathlib.Path(config.process.paths.data).joinpath(ilc)

    # Retrieve textual data
    data_file_name = files.data_name(
        name=config.process.data_name,
        query=ilc,
        folder=data_folder,
        extension="json",
        use_timestamp=False,
        ensure_folder=False,
    )

    try:
        with open(data_file_name, "r", encoding="utf-8") as data_file:
            data = json.load(data_file)
    except FileNotFoundError:
        return None

    # Retrieve images
    images = [
        photo.encode_image(str(path))
        for path in data_folder.joinpath(config.process.paths.photos).glob("*.jpg")
    ]

    data["photos"] = images
    data["message"] = "success"
    return data


def export_data(device: str) -> None:
    """Export local data to an external location."""
    transfer.export_data(
        data_folder=config.process.paths.data,
        destination=str(pathlib.Path(config.process.paths.external).joinpath(device)),
    )


def _handle_device(device: str, command: str) -> t.Mapping[str, object]:
    """(Attempt to) mount the given device."""
    try:
        message = subprocess.check_output(
            [command, device], stderr=subprocess.STDOUT
        ).decode("utf-8")
    except subprocess.CalledProcessError as e:
        message = e.output.decode("utf-8") if e.output else ""
        valid = False
        logger.error(e)
    else:
        message = "Success" + (": " if message else "") + message
        valid = True
    return {"message": message, "valid": valid}


def mount_device(device: str) -> t.Mapping[str, object]:
    """(Attempt to) mount the given device."""
    return _handle_device(device, "pmount")


def unmount_device(device: str) -> t.Mapping[str, object]:
    """(Attempt to) unmount the given device."""
    return _handle_device(device, "pumount")


def get_devices() -> t.Sequence[str]:
    """Return the seen block devices."""
    try:
        # s: invert dependencies, so partitions have device as children
        # d: don't output dependencies, so only partitions are output
        # n: don't output headers
        # o: only output specified column, i.e. NAME
        output = subprocess.check_output(
            ["lsblk", "-sdno", "NAME"], stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError as e:
        logger.error(e)
        devices = []
    else:
        # Example output to parse:
        # $ lsblk --pairs -o name
        # sda1
        # mmcblk0p1
        # mmcblk0p2
        # $
        # We make extra sure there is no extra whitespace
        devices = [line.strip() for line in output.decode("utf-8").strip().split()]
    return devices
