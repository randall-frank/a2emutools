from datetime import datetime
import struct
from typing import List, Optional, Tuple, Union

from a2emutools.container_formats import DiskImage
from a2emutools.filesystem import DirObj, FileObj, FileSystem


class ProDOSFileObj(FileObj):
    def __init__(self, file_system: "FileSystem", name: str, parent: "DirObj") -> None:
        super().__init__(file_system, name, parent)

    def _read(self) -> None:
        self.data = bytearray()

    def _write(self) -> None:
        pass

    def delete(self) -> None:
        pass


class ProDOSDirObj(DirObj):
    def __init__(
        self, file_system: "FileSystem", name: str = "", parent: Optional["DirObj"] = None
    ) -> None:
        super().__init__(file_system, name, parent)
        self._type: str = "ProDOS"

    def create_file(self, name: str, filetype: str) -> Optional["FileObj"]:
        return None

    def create_directory(self, name: str) -> Optional["DirObj"]:
        raise RuntimeError("Subdirectories are not supported on this filesystem.")

    def children(self) -> List[Union["DirObj", "FileObj"]]:
        return []

    def delete(self):
        pass


class ProDOSFileSystem(FileSystem):
    volume_directory_header_format = "<ic15c8cHHcccccHHH"

    @staticmethod
    def is_format(container: "DiskImage") -> bool:
        # Try to read the ProDOS Volume Directory from block 2.
        raw_block = container.read_block(2)
        tmp = struct.unpack(ProDOSFileSystem.volume_directory_header_format, raw_block)
        # tmp[0] = unknown 4 bytes
        storage_type = int(tmp[1])
        # The first block must be type 'f'
        if (storage_type & 0xF0) != 0xF0:
            return False
        name_length = storage_type & 0x0F
        volume_name = tmp[2]
        volume_name = volume_name[:name_length]
        # tmp[3] = reserved 8 bytes
        # date_date = tmp[5]  # 2 bytes
        # date_time = tmp[6]  # 2 bytes
        # VERSION ProDOS 1.0 version is 0.
        prodos_version = int(tmp[7])
        if prodos_version != 0:
            return False
        # tmp[8] = MIN_VERSION
        # tmp[9] = ACCESS
        # tmp[10] = ENTRY_LENGTH = $27
        if int(tmp[10]) != 0x27:
            return False
        # tmp[11] = ENTRIES_PER_BLOCK = $0D?
        # tmp[12] = FILE_COUNT
        # tmp[13] = BIT_MAP_POINTER
        # tmp[14] = TOTAL_BLOCKS
        return True

    @staticmethod
    def timestamp_to_datetime(date_date: int, date_time: int) -> "datetime":
        # Date/time ProDOS bit layout
        # YYYY YYYM MMMD DDDD - year
        # 000H HHHH 00MM MMMM - time
        # Year conversion:
        # 40-99 = 1940-1999
        # 0-39 = 2000-2039
        day = date_date & 0x001F
        month = (date_date >> 5) & 0x000F
        year = (date_date >> 9) & 0x003F
        if year < 40:
            year = 2000 + year
        else:
            year = 1900 + year
        hour = (date_time >> 8) & 0x001F
        minute = date_time & 0x003F
        return datetime(year=year, month=month, day=day, hour=hour, minute=minute)

    @staticmethod
    def datetime_to_timestamp(date: "datetime") -> Tuple[int, int]:
        year = date.year
        if year >= 2000:
            year = year - 2000
        else:
            year = year - 1900
        date_date = date.day | (date.month << 5) | (year << 9)
        date_time = date.minute | (date.hour << 8)
        return date_date, date_time

    def __init__(self, container: "DiskImage") -> None:
        super().__init__(container)
        self._type = "ProDOS"

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
