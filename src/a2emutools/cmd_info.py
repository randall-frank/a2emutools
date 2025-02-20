from . import container_formats, filesystem  # noqa: F401


def cmd_info(pathname: str, vtoc: bool = False, verbose: bool = False):
    image = container_formats.create_image(pathname)
    fs = image.filesystem
    print(fs.info())
    return
