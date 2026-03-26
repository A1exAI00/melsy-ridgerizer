from os import makedirs, path


def is_float(string):
    try:
        float(string)
        return True
    except ValueError:
        return False


def get_next_filename(dir: str, name: str = "image", ext: str = "png") -> str:
    makedirs(dir, exist_ok=True)

    counter = 1
    while True:
        filename = path.join(dir, f"{name}{counter:03d}.{ext}")
        if not path.exists(filename):
            return filename
        counter += 1
    return
