from datetime import datetime
from enum import IntEnum
import os.path
import stat
from typing import Any, List, Optional, Union

from a2emutools.container_formats import DiskImage


class Access(IntEnum):
    # Notion of entities having access restrictions
    DELETE: int = 1 << 7
    RENAME: int = 1 << 6
    CHANGED: int = 1 << 5
    WRITE: int = 1 << 1
    READ: int = 1 << 0
    ALL: int = DELETE | RENAME | WRITE | READ
    CORE: int = DELETE | RENAME


class DirObj:
    def __init__(
        self, file_system: "FileSystem", name: str = "", parent: Optional["DirObj"] = None
    ) -> None:
        self._fs = file_system
        self._name: str = name
        self._parent: Optional["DirObj"] = parent
        self._create_time: "datetime" = datetime.now()
        self._mod_time: "datetime" = datetime.now()
        self._access: Access = Access.ALL

    def setup(self, **kwargs) -> None:
        pass

    @property
    def file_system(self) -> "FileSystem":
        return self._fs

    @property
    def parent(self) -> Optional["DirObj"]:
        return self._parent

    @property
    def access(self) -> Access:
        return self._access

    @property
    def path(self) -> str:
        s = f"/{self.name}"
        p = self.parent
        while p:
            if not p.name:
                return s
            s = f"/{p.name}{s}"
            p = p.parent
        return s

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, name: Any) -> None:
        if type(name) is not str:
            self._name = name.decode("ascii")
        self._name = self._name.rstrip("\0").rstrip(" ")

    def create_file(self, name: str, filetype: str) -> Optional["FileObj"]:
        return None

    def create_directory(self, name: str) -> Optional["DirObj"]:
        raise RuntimeError("Subdirectories are not supported on this filesystem.")

    def children(self) -> List[Union["DirObj", "FileObj"]]:
        children: List[Union["DirObj", "FileObj"]] = []
        path = self._fs._local_pathname(self.path)
        for name in os.listdir(path):
            fullname = os.path.join(path, name)
            if os.path.isfile(fullname):
                children.append(FileObj(self._fs, name, self))
            elif os.path.isdir(fullname):
                children.append(DirObj(self._fs, name, self))
        return children

    def delete(self):
        print(f"Deleting: {self._fs._local_pathname(self.path)} unimplemented.")

    def info(self) -> str:
        s = f"{self.path}/"
        s += (
            f" Create: {self._create_time.strftime('%Y-%m-%d %H:%M:%S')} "
            f"Mod: {self._mod_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        return s


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
        self._access: Access = Access.ALL
        self._data: bytearray = bytearray()
        self._synced: bool = False

    def setup(self, **kwargs) -> None:
        path = self._fs._local_pathname(self.path)
        if os.path.isfile(path):
            s = os.stat(path)
            self._file_size = s.st_size
            self._file_type = os.path.splitext(path)[1][1:].upper()
            self._mod_time = datetime.fromtimestamp(s.st_mtime)
            self._create_time = datetime.fromtimestamp(s.st_ctime)
            a = int(Access.CORE)
            if stat.S_IRUSR & s.st_mode:
                a |= Access.READ
            if stat.S_IWUSR & s.st_mode:
                a |= Access.WRITE
            self._access = Access(a)

    @property
    def file_system(self) -> "FileSystem":
        return self._fs

    @property
    def parent(self) -> Optional["DirObj"]:
        return self._parent

    @property
    def path(self) -> str:
        s = f"/{self.name}"
        p = self.parent
        while p:
            if not p.name:
                return s
            s = f"/{p.name}{s}"
            p = p.parent
        return s

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, name: Any) -> None:
        if type(name) is not str:
            self._name = name.decode("ascii")
        self._name = self._name.rstrip("\0").rstrip(" ")

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
    def access(self) -> Access:
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
        if not self._synced:
            self._read()
        return self._data

    @data.setter
    def data(self, data: bytearray) -> None:
        self._data = data
        self._synced = False

    def _read(self) -> None:
        self.data = bytearray()
        path = self._fs._local_pathname(self.path)
        if os.path.isfile(path):
            with open(path, "rb") as fp:
                tmp = fp.read()
            self._data = bytearray(tmp)
        self._synced = True

    def _write(self) -> None:
        print(f"Writing to: {self._fs._local_pathname(self.path)} unimplemented.")
        self._synced = True

    def delete(self) -> None:
        print(f"Deleting: {self._fs._local_pathname(self.path)} unimplemented.")

    def info(self) -> str:
        s = f"{self.path} {self.file_type} Size: {self.file_size} Aux: {self.aux_bits}"
        s += (
            f" Access: {self.access.name}"
            f" Create: {self.create_time.strftime('%Y-%m-%d %H:%M:%S')}"
            f" Mod: {self.mod_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        return s


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
        return os.path.isdir(container.container_name)

    def __init__(self, container: "DiskImage") -> None:
        self._type: str = "Local Filesystem"
        self._container: "DiskImage" = container
        self._volume_name: str = ""
        self._bitmap: bytearray = bytearray()

    @property
    def container(self) -> "DiskImage":
        return self._container

    @property
    def type(self) -> str:
        return self._type

    @property
    def root(self) -> "DirObj":
        return DirObj(self)

    @property
    def volume_name(self) -> str:
        return self._volume_name

    @property
    def bitmap(self) -> bytearray:
        return self._bitmap

    def find_entity(
        self, name: str, parent: Optional["DirObj"] = None
    ) -> Union["DirObj", "FileObj", None]:
        """
        Walk the files and directories of the filesystem and return the DirObj, FileObj
        instances corresponding to the specified name.   If the name cannot be found,
        the method returns None.

        Parameters
        ----------
        name: str
            The pathname of the object to find.  The '/' character serves as the name deliminator.

        parent: DirObj, optional
            The directory object to start the search from.  If None, the search starts
            from the root of the filesystem.
        Returns
        -------
        The object found or None

        """
        cur_obj = parent
        if not cur_obj:
            cur_obj = self.root
        if cur_obj.path == name:
            return cur_obj
        for child in cur_obj.children():
            if isinstance(child, FileObj):
                continue
            found = self.find_entity(name, parent=child)
            if found:
                return found
        return None

    def flush(self) -> None:
        pass

    def initialize(self) -> None:
        pass

    def info(self, vtoc: bool = False) -> str:
        """
        This method returns the string that is displayed by the 'info' cli command.
        It should report on the nature of the container: size, type, VTOC, etc

        Parameters
        ----------
        vtoc: bool
            If True, include block/sector allocation info where applicable

        Returns
        -------
        str
            The output to be displayed.
        """
        s = f"Container: {self.container.container_name}\n"
        s += f"Filesystem: {self.type}"
        return s

    def ls_info_header(self, prefix: str) -> str:
        s = f"Listing for '{prefix}' in container '{self.container.container_name}':\n"
        s += "-" * 60 + "\n"
        return s

    def ls_info_footer(self, prefix: str) -> str:
        s = "-" * 60 + "\n"
        return s

    def _local_pathname(self, pathname: str) -> str:
        return os.path.join(self._container.container_name, pathname)
