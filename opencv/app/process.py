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


def activate(*args: t.Any, **kwargs: t.Any) -> t.Mapping[str, object]:
    """Activate a round of the camera station."""
    # Turn on lights
    lights.Lights().ring().level = config.lights.level
    time.sleep(config.process.camera.wait)
    # Operate undercamera for sizing
    sizes = devices.get_camera().get_processed_frame(
        threshold=kwargs.get("threshold", None)
    )[1]
    size = tuple(f"{val:.2f}" for val in sizes[0]) if sizes else (0, 0)
    # Turn off lights
    lights.Lights().ring().off()

    # Use overhead tech to get depth
    try:
        with devices.get_sensor() as sens:
            height = sens.obtain(base=kwargs.get("base_depth", 0))
    except Exception as e:
        logger.error(e)
        height = 0

    # Read scale
    try:
        with devices.get_scale() as sc:
            weight = sc.read()
    except Exception as e:
        logger.error(e)
        weight = 0

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
    try:
        photo_paths = photo.capture_image_set(
            str(data_folder.joinpath(config.process.paths.photos)), timestamp=now
        )
        logger.info("Photos: %s", photo_paths)
    except Exception as e:
        photo_paths = []
        logger.error(e)

    # Encode and return pictures
    encoded_images: t.List[str] = [photo.encode_image(path) for path in photo_paths]
    # Return data
    return {
        "message": "success",
        "size": size,
        "weight": weight,
        "height": height,
        "photos": encoded_images,
    }
