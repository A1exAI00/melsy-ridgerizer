from os import makedirs, path


def is_float(string):
    try:
        float(string)
        return True
    except ValueError:
        return False


def get_next_filename(
    dir: str,
    name: str = "image",
    ext: str = "png",
    separator: str = "_",
    max_count: int = 999,
) -> str:
    """Get next unoccupied filename in a directory.

    If filename `{name}{separator}001.{ext}` is unoccupied, then {name}{separator}002.{ext}` is checked and so on until the `max_count`.

    :param dir: Directory where next unoccupied filename should be searched for.
    :type dir: str
    :param name: Name of the file.
    :type name: str
    :param ext: Extention of the file.
    :type ext: str
    :param separator: String to separate name and counter in the filename.
    :type separator: str
    :param max_count: Maximum counter value.
    :type max_count: int

    :returns: Next unoccupied filename.
    :rtype: str
    """
    makedirs(dir, exist_ok=True)

    counter = 1
    while True:
        if counter > max_count:
            raise Exception(f"Could not find next unoccupied filename '{name}.{ext}' in directory {dir}.")
        
        filename = f"{name}{separator}{counter:03d}.{ext}"
        filepath = path.join(dir, filename)
        if path.exists(filepath):
            counter += 1
            continue
        else:
            break

    return filename
