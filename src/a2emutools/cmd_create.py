import logging

from . import container_formats, filesystem  # noqa: F401

_ = logging.getLogger("a2emutools")


def cmd_create(cont_name: str, bootable: bool = True, size: int = 143360):
    return
