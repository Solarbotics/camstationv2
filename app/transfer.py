"""Utilities for transferring data."""

import logging
import pathlib
import shutil
import subprocess
import typing as t

from . import config
from . import files

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def export_data(data_folder: str, destination: str) -> None:
    """Export camera station data to a specified destination.

    Deletes local copy.
    """
    data_path = pathlib.Path(data_folder)
    destination_path = pathlib.Path(destination)

    if data_path.exists():
        # Ensure destination exists
        destination_path.mkdir(parents=True, exist_ok=True)
        # Use rsync to copy over
        try:
            subprocess.run(
                ["rsync", "-a", str(data_path), str(destination_path)], check=True
            )
        except subprocess.CalledProcessError as e:
            logger.error(e)
        else:
            shutil.rmtree(data_path)
