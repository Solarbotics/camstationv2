"""Utilities for transferring data."""

import os
import pathlib
import shutil
import typing as t

from . import config
from . import files


def export_data(data_folder: str, destination: str) -> None:
    """Export camera station data to a specified destination.

    Deletes local copy.
    """
    data_path = pathlib.Path(data_folder)
    destination_path = pathlib.Path(destination)

    if data_path.exists():
        # Get name of data folder, and join it to destination
        # to get the proper name to name it as
        new_name = files.next_name(destination_path.joinpath(data_path.name)).name

        new_data_path = data_path.with_name(new_name)

        os.rename(data_path, new_data_path)

        shutil.move(str(new_data_path), dst=destination, copy_function=shutil.copy)
