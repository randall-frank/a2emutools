__version__ = "0.1.0"

from typing import Callable, Dict

from . import container_formats, dos33, filesystem, prodos

known_filesystems: Dict["container_formats.FileSystemType", Callable] = dict()
known_filesystems[container_formats.FileSystemType.NATIVE] = filesystem.FileSystem
known_filesystems[container_formats.FileSystemType.DOS33] = dos33.DOS33FileSystem
known_filesystems[container_formats.FileSystemType.PRODOS] = prodos.ProDOSFileSystem
