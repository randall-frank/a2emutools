import logging
from typing import Union

from . import container_formats, filesystem  # noqa: F401

log = logging.getLogger("a2emutools")


def _gen_text_entity(
    entity: Union[filesystem.DirObj, filesystem.FileObj], full: bool = False, recurse: bool = False
) -> str:
    s = ""
    if isinstance(entity, filesystem.DirObj):
        s += f"Directory: {entity.path}\n"
        if recurse:
            for child in entity.children():
                s += _gen_text_entity(child, full=full, recurse=recurse)
    else:
        s += f"File: {entity.path} {entity.file_type}\n"
    return s


def cmd_ls(cont_name: str, prefix: str, full: bool = False, recurse: bool = False):
    container = container_formats.create_image(cont_name)
    fs = container.filesystem
    root = fs.find_entity(prefix)
    if not root:
        log.error(f"Unable to find '{prefix}' in the container '{container.container_name}'")
    s = ""
    for entity in root.children():
        s += _gen_text_entity(entity, full=full, recurse=recurse)
    print(s)
