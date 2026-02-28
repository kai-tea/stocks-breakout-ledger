from pathlib import Path

def find_file(filename: str, path: str = ".") -> Path | None:
    """
    :param filename: name of the file
    :param path: path to that needs to be searched
    :return: Path object or None
    """

    return next(Path(path).glob(filename))
