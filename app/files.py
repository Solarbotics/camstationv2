"""Data file management."""

import datetime
import pathlib
import string
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


def next_name(path: pathlib.Path) -> pathlib.Path:
    """Determine the next non-conflicting path name.

    Creates a non-conflicting name by incrementing a trailing number,
    directly before the first '.'.

    <name>.<ext> -> <name>1.<ext> -> <name>2.<ext> ...

    If the path does not already exist, it is returned unchanged.
    """

    # If the path doesn't exist, doing .parent.iterdir
    # will appropriately raise an error, but in that
    # case we can properly say existing is an empty set
    try:
        existing = set(path.parent.iterdir())
    except FileNotFoundError:
        existing = set()

    # We edit path until it no longer exists
    # If it doesn't exist in the first place we instantly return
    while path in existing:
        # Extract suffixes
        name, *suffixes = path.name.split(".")
        # Strip any existing numeral off
        bare_name = name.rstrip(string.digits)
        # Recover digits
        # Empty string will raise a value error
        try:
            old_value = int(name[len(bare_name) :])
        except ValueError:
            old_value = 0
        # Increment
        next_mark = str(old_value + 1)
        # need to do the '.' + '.'.join to get leading '.' when there is a extension
        new_name = (
            bare_name + next_mark + ("." if suffixes else "") + ".".join(suffixes)
        )
        path = path.with_name(new_name)

    return path


def query_folder(query: t.Optional[str], generic: str, parent: str) -> pathlib.Path:
    """Construct a query-based folder for files based on given parameters.

    Makes a path with the query if given,
    otherwise increments a generic folder name.
    """

    # Query can be false if None, or empty ("")
    if query:
        data_folder = pathlib.Path(parent).joinpath(query)
    else:
        data_folder = next_name(pathlib.Path(parent).joinpath(pathlib.Path(generic)))

    return data_folder
