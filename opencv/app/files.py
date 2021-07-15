"""Data file management."""

import datetime
import pathlib
import typing as t

from . import config


def data_name(
    name: str,
    folder: str = ".",
    extension: t.Optional[str] = None,
    timestamp: bool = False,
) -> str:
    """Construct a data filepath based on given parameters.

    Ensures the folder exists (may be a multi-folder path).

    If timestamp is true, appends a timestamp to the end of the file name.
    If extension is provided, a '.' and it are appended to the end of the file (after timestamp).
    """
    root = pathlib.Path(folder)
    root.mkdir(parents=True, exist_ok=True)

    now = datetime.datetime.now().strftime(config.files.timeformat)

    if extension is not None:
        file_name = f"{name}_{now}.{extension}"
    else:
        file_name = f"{name}_{now}"

    save_path = str(root.joinpath(pathlib.Path(file_name)))

    return save_path
