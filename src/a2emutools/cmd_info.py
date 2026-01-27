import logging

from . import container_formats, filesystem  # noqa: F401

_ = logging.getLogger("a2emutools")


def cmd_info(cont_name: str, vtoc: bool = False):
    image = container_formats.create_image(cont_name)
    fs = image.filesystem
    print(fs.info(vtoc=vtoc))
