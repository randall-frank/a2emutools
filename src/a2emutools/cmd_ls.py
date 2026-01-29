import logging
from typing import Union

from . import container_formats, filesystem  # noqa: F401

log = logging.getLogger("a2emutools")


def _gen_text_entity(
    entity: Union[filesystem.DirObj, filesystem.FileObj], recurse: bool = False
) -> str:
    s = ""
    if isinstance(entity, filesystem.DirObj):
        s += f"{entity.info()}\n"
        if recurse:
            for child in entity.children():
                s += _gen_text_entity(child, recurse=recurse)
    else:
        s += f"{entity.info()}\n"
    return s


def cmd_ls(cont_name: str, prefix: str, recurse: bool = False):
    container = container_formats.create_image(cont_name)
    fs = container.filesystem
    root = fs.find_entity(prefix)
    if not root:
        log.error(f"Unable to find '{prefix}' in the container '{container.container_name}'")
    s = f"Prefix: {prefix}\n"
    for entity in root.children():
        s += _gen_text_entity(entity, recurse=recurse)
    print(s)
