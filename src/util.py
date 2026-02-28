from pathlib import Path

def get_path_from_filename(filename: str, search_path: Path = Path(".")) -> Path | None:
    """Returns path to given filename in the given search_path or None if not found."""

    try:
        return next(Path(search_path).rglob(filename))
    except StopIteration:
        # raised if no file is found
        return None
