"""Operate main camera station processes."""

import base64
import datetime
import json
import logging
import pathlib
import time
import typing as t

from . import config
from . import devices
from . import files
from . import lights
from . import photo

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# (str, str) or (float, float)?
def read_bounds(threshold: int = 0) -> t.Tuple[float, float]:
    """Obtain the bounds provided by the camera station."""
    try:
        sizes = devices.get_camera().get_processed_frame(threshold=threshold)[1]
    except Exception as e:
        logger.error(e)
        size = (0.0, 0.0)
    else:
        main = sizes[0] if sizes else (0.0, 0.0)
        size = (round(float(main[0]), 2), round(float(main[1]), 2))
    return size


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
    return weight


def read_height(base: t.Optional[int] = None) -> int:
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
    return height


def take_photos(
    folder: t.Union[str, pathlib.Path],
    timestamp: t.Optional[datetime.datetime] = None,
) -> t.List[str]:
    """Takes a set of photos, saving onto disk and returning base64 encodings."""
    try:
        photo_paths = photo.capture_image_set(folder=str(folder), timestamp=timestamp)
    except Exception as e:
        logger.error(e)
        return []
    else:
        return [photo.encode_image(path) for path in photo_paths]


def activate(*args: t.Any, **kwargs: t.Any) -> t.Mapping[str, object]:
    """Activate a round of the camera station."""
    # Turn on lights
    lights.Lights().ring().level = config.lights.level
    time.sleep(config.process.camera.wait)
    # Operate undercamera for sizing
    size = tuple(
        f"{val:.2f}" for val in read_bounds(threshold=kwargs.get("threshold", 0))
    )
    # Turn off lights
    lights.Lights().ring().off()

    # Use overhead tech to get depth
    height = read_height(base=kwargs.get("base_depth", 0))
    # Read scale
    weight = read_weight(tare=kwargs.get("tare", 0))

    # Save gathered data
    # Construct root folder
    now = datetime.datetime.now()
    data_folder = pathlib.Path(config.process.paths.data).joinpath(
        files.format_timestamp(now)
    )
    file_name = files.data_name(
        name=config.process.data_name,
        folder=data_folder,
        extension="json",
        use_timestamp=True,
        timestamp=now,
    )
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump({"size": size, "weight": weight, "height": height}, f)
    # Take photos
    encoded_images = take_photos(
        data_folder.joinpath(config.process.paths.photos), timestamp=now
    )

    # Return data
    return {
        "message": "success",
        "size": size,
        "weight": weight,
        "height": height,
        "photos": encoded_images,
    }
