"""Utilities for transferring data."""

import os
import pathlib
import shutil
import typing as t

from . import config
from . import files


def export_data(
    data_folder: t.Optional[str] = None, destination: t.Optional[str] = None
) -> None:
    """Export camera station data to a specified destination.

    Deletes local copy.
    """
    if data_folder is None:
        data_folder = config.process.paths.data
    data_path = pathlib.Path(data_folder)

    if destination is None:
        destination = config.process.paths.external
    destination_path = pathlib.Path(destination)

    # Get name of data folder, and join it to destination
    # to get the proper name to name it as
    new_name = files.next_name(destination_path.joinpath(data_path.name)).name

    new_data_path = data_path.with_name(new_name)

    os.rename(data_path, new_data_path)

    shutil.move(str(new_data_path), dst=destination, copy_function=shutil.copy)
