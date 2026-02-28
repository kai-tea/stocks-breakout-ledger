from pathlib import Path

def find_file(filename: str, start_path: Path = Path(".")) -> Path | None:
    """
    :param filename: name of the file
    :param start_path: starting path that is being recursively searched
    :return: Path object or None
    """

    try:
        return next(Path(start_path).rglob(filename))
    except StopIteration:
        # raised if no file is found
        return None
