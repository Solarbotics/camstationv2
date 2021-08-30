"""Utilities for transferring data."""

import shutil
import typing as t

from . import config


def export_data(
    data_folder: t.Optional[str] = None, destination: t.Optional[str] = None
) -> None:
    """Export camera station data to a specified destination.

    Deletes local copy.
    """
    if data_folder is None:
        data_folder = config.process.paths.data

    if destination is None:
        destination = config.process.paths.external

    shutil.move(data_folder, dst=destination, copy_function=shutil.copy)
