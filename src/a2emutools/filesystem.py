from typing import List
from datetime import datetime


class FileObj:
    def __init__(self, file_system: "FileSystem", name: str = "", path: str = ""):
        self._fs = file_system
        self._name: str = name
        self._path: str = path
        self._create_time: "datetime" = datetime.now()
        self._mod_time: "datetime" = datetime.now()
        self._file_type: str = ""
        self._file_size: int = 0
        self._aux_bits: int = 0
        self._access: int = 0
        self._data: bytes = b''

    @property
    def file_system(self) -> "FileSystem":
        return self._fs

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
    def path(self) -> str:
        return self._path

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
    def data(self) -> bytes:
        return self._data

    @data.setter
    def data(self, data: bytes) -> None:
        self._data = data

    def read(self) -> None:
        pass

    def write(self) -> None:
        pass


class FileSystem:
    def __int__(self, container: str = "", cwd: str = ""):
        self._type: str = "unknown"
        self._container: str = container
        self._working_dir: str = cwd

    def cwd(self) -> str:
        return self._working_dir

    def set_cwd(self, path: str) -> None:
        self._working_dir = path

    def list_files(self, path: str = "") -> List["FileObj"]:
        return []

    def unlink_file(self, path: str) -> None:
        pass

    def create_path(self, path: str, recurse: bool = False) -> None:
        pass

    def unlink_path(self, path: str, recurse: bool = False) -> None:
        pass

    def flush(self) -> None:
        pass

    def initialize(self) -> None:
        pass
