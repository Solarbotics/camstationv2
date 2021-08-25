"""Data file management."""

import datetime
import pathlib
import typing as t

from . import config


def format_timestamp(
    timestamp: t.Optional[datetime.datetime] = None, timeformat: t.Optional[str] = None
) -> str:
    """Create a timestamp from the provided datetime and format string.

    If a datetime is not provided, defaults to now() (naive).

    Has a default format string that can be used if one is not provided.
    """
    if timestamp is None:
        timestamp = datetime.datetime.now()
    if timeformat is None:
        timeformat = config.files.timeformat
    return timestamp.strftime(timeformat)


def data_name(
    name: str,
    *,
    folder: t.Union[str, pathlib.Path] = ".",
    extension: t.Optional[str] = None,
    format: t.Optional[str] = None,
    use_timestamp: bool = True,
    timestamp: t.Optional[datetime.datetime] = None,
    timeformat: t.Optional[str] = None,
    ensure_folder: bool = True,
) -> str:
    """Construct a data filepath based on given parameters.

    Ensures the folder exists (may be a multi-folder path).

    Creates a filepath with the given folder as a directory,
    and then constructs a filename based on `name`,
    timestamp parameters, `extension`, and format parameters.

    The file name is constructed by calling .format on `format`, passing `name` as key `name`.
    A timestamp can also be formatted in, as described below.

    If `use_timestamp` is true, a timestamp is formatted into the file name using key `time`.
    A timestamp can be provided to `timestamp`, or .now() (naive) will be used by default.
    The datetime is first formatted into a string using `timeformat` as a format string,
    before being formatted into the final file name.

    If an extension is provided, it is appended to the end of the file, after a '.' literal.
    """

    # Pull format from config if not provided
    if format is None:
        format = config.files.format

    # We call the local file name (i.e. in the local directory)
    # `label`, to differentiate from parameter `name`
    # format_timestamp will pull a default timeformat if its None
    if use_timestamp:
        formatted_time = format_timestamp(timestamp, timeformat=timeformat)
        label = format.format(name=name, time=formatted_time)
    else:
        label = format.format(name=name)

    # Add extension if it exists
    if extension is not None:
        label += f".{extension}"

    root = pathlib.Path(folder)
    # Ensure that the folder exists
    if ensure_folder:
        root.mkdir(parents=True, exist_ok=True)

    save_path = str(root.joinpath(pathlib.Path(label)))

    return save_path


def query_folder(
    query: t.Optional[str],
    generic: str,
    timestamp: t.Optional[datetime.datetime] = None,
) -> pathlib.Path:
    """Construct a query-based folder for files based on given parameters."""

    # Query can be false if None, or empty ("")
    if query:
        data_folder = pathlib.Path(query)
    else:
        data_folder = pathlib.Path(generic).joinpath(format_timestamp(timestamp))

    return data_folder
