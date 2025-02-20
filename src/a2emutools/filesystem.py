from datetime import datetime
from typing import List, Optional, Union

from a2emutools.container_formats import DiskImage


class DirObj:
    def __init__(
        self, file_system: "FileSystem", name: str = "", parent: Optional["DirObj"] = None
    ) -> None:
        self._fs = file_system
        self._name: str = name
        self._parent: Optional["DirObj"] = parent
        self._create_time: "datetime" = datetime.now()
        self._mod_time: "datetime" = datetime.now()

    @property
    def file_system(self) -> "FileSystem":
        return self._fs

    @property
    def parent(self) -> Optional["DirObj"]:
        return self._parent

    @property
    def path(self) -> str:
        p = self.parent
        s = ""
        while p:
            s = f"/{p.name}{s}"
        return s

    @property
    def name(self) -> str:
        return self._name

    @property
    def fullpath(self) -> str:
        s = self.path
        if s:
            s = f"{self.path}/{self.name}"
        else:
            s = self.name
        s = s.replace("//", "/")
        return s

    def create_file(self, name: str, filetype: str) -> Optional["FileObj"]:
        return None

    def create_directory(self, name: str) -> Optional["DirObj"]:
        raise RuntimeError("Subdirectories are not supported on this filesystem.")

    def children(self) -> List[Union["DirObj", "FileObj"]]:
        return []

    def delete(self):
        pass


class FileObj:
    def __init__(self, file_system: "FileSystem", name: str, parent: "DirObj") -> None:
        self._fs = file_system
        self._name: str = name
        self._parent: "DirObj" = parent
        self._create_time: "datetime" = datetime.now()
        self._mod_time: "datetime" = datetime.now()
        self._file_type: str = ""
        self._file_size: int = 0
        self._aux_bits: int = 0
        self._access: int = 0
        self._data: bytearray = bytearray()

    @property
    def file_system(self) -> "FileSystem":
        return self._fs

    @property
    def parent(self) -> Optional["DirObj"]:
        return self._parent

    @property
    def path(self) -> str:
        p = self.parent
        s = ""
        while p:
            s = f"/{p.name}{s}"
        return s

    @property
    def name(self) -> str:
        return self._name

    @property
    def file_type(self) -> str:
        return self._file_type

    @property
    def file_size(self) -> int:
        return self._file_size

    @property
    def aux_bits(self) -> int:
        return self._aux_bits

    @property
    def access(self) -> int:
        return self._access

    @property
    def create_time(self) -> datetime:
        return self._create_time

    @create_time.setter
    def create_time(self, t: datetime) -> None:
        self._create_time = t

    @property
    def mod_time(self) -> datetime:
        return self._mod_time

    @mod_time.setter
    def mod_time(self, t: datetime) -> None:
        self._mod_time = t

    @property
    def data(self) -> bytearray:
        return self._data

    @data.setter
    def data(self, data: bytearray) -> None:
        self._data = data

    def _read(self) -> None:
        self.data = bytearray()

    def _write(self) -> None:
        pass

    def delete(self) -> None:
        pass


class FileSystem:
    @staticmethod
    def is_format(container: "DiskImage") -> bool:
        """
        Check to see if a specific container instance supports
        this filesystem interface.

        Parameters
        ----------
        container: DiskImage
            The DiskImage object to test.

        Returns
        -------
        bool
            True if the DiskImage object supports this FileSystem

        """
        return False

    def __init__(self, container: "DiskImage") -> None:
        self._type: str = "Local Filesystem"
        self._container: "DiskImage" = container

    @property
    def container(self) -> "DiskImage":
        return self._container

    @property
    def type(self) -> str:
        return self._type

    @property
    def root(self) -> "DirObj":
        return DirObj(self, name=self.container.pathname)

    def flush(self) -> None:
        pass

    def initialize(self) -> None:
        pass

    def info(self) -> str:
        s = f"{self.type}\n"
        s += f"Container={self.container.container_name}\n"
        s += f"Path={self.root.fullpath}"
        return s
