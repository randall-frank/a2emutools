import logging

from . import container_formats, filesystem  # noqa: F401

log = logging.getLogger("a2emutools")


def cmd_ls(
    cont_name: str, prefix: str, full: bool = False, json: bool = False, recurse: bool = False
):
    container = container_formats.create_image(cont_name)
    fs = container.filesystem
    root = fs.find_entity(prefix)
    if not root:
        log.error(f"Unable to find '{prefix}' in the container '{container.container_name}'")
