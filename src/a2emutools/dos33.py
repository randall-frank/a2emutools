import struct
from typing import List, Optional, Union

from a2emutools.container_formats import DiskImage
from a2emutools.filesystem import DirObj, FileObj, FileSystem

DOS33FiletypesMap = dict(
    TXT=b"x00",
    INT=b"x01",
    BAS=b"x02",
    BIN=b"x04",
    S=b"x08",
    R=b"x10",
    A=b"x20",
    B=b"x40",
)


class DOS33FileObj(FileObj):
    def __init__(self, file_system: "FileSystem", name: str, parent: "DirObj") -> None:
        super().__init__(file_system, name, parent)

    def _read_info(self):
        pass

    def _read(self) -> None:
        self.data = bytearray()
        self._synced = True

    def _write(self) -> None:
        self._synced = True

    def delete(self) -> None:
        pass


class DOS33DirObj(DirObj):
    def __init__(
        self, file_system: "FileSystem", name: str = "", parent: Optional["DirObj"] = None
    ) -> None:
        super().__init__(file_system, name, parent)
        self._type: str = "DOS 3.3"

    def create_file(self, name: str, filetype: str) -> Optional["FileObj"]:
        return None

    def create_directory(self, name: str) -> Optional["DirObj"]:
        raise RuntimeError("Subdirectories are not supported on this filesystem.")

    def children(self) -> List[Union["DirObj", "FileObj"]]:
        return []

    def delete(self):
        pass


class DOS33FileSystem(FileSystem):
    vtoc_format = "<cBBBHB32sB8sBBHBBH50H"

    @staticmethod
    def is_format(container: "DiskImage") -> bool:
        # Try to read the DOS 3.3 VTOC from track 17, sector 0.
        raw_sector = container.read_sector(17, 0)
        tmp = struct.unpack_from(DOS33FileSystem.vtoc_format, raw_sector, 0)
        # tmp[0] = unused (1byte)
        # tmp[1] = CATALOG_TRACK (1byte)
        # first_track = int(tmp[1])
        # tmp[2] = CATALOG_SECTOR (1byte)
        # first_sector = int(tmp[2])
        # tmp[3] = DOS_VERSION (1byte)
        dos_version = int(tmp[3])
        if dos_version != 3:
            return False
        # tmp[4] = unused (2bytes)
        # tmp[5] = VOLUME_NUMBER (1byte)
        # volume_number = int(tmp[5])
        # tmp[6] = unused (32bytes)
        # tmp[7] = MAX_T/S_PAIRS (1byte)
        max_ts_pairs = int(tmp[7])
        if max_ts_pairs != 122:
            return False
        # tmp[8] = unused (8bytes)
        # tmp[9] = LAST_TRACK (1byte)
        # last_track = int(tmp[9])
        # tmp[10] = DIRECTION (1byte)
        # direction = int(tmp[10])
        # tmp[11] = unused (2bytes)
        # tmp[12] = NUM_TRACKS (1byte)
        # num_tracks = int(tmp[12])
        # tmp[13] = NUM_SECTORS (1byte)
        num_sectors = int(tmp[13])
        if num_sectors != 16:
            return False
        # tmp[14] = NUM_BYTES_PER_SECTOR (2bytes)
        num_bytes_per_sector = int(tmp[14])
        if num_bytes_per_sector != 256:
            return False
        # 50 potential tracks, one bit per sector
        # (normally 35 tracks x 16 sectors = 560 bits)
        # tmp[15...] = SECTOR_BITMAPS 50 shorts
        # bitmaps = tmp[15]
        return True

    def __init__(self, container: "DiskImage") -> None:
        super().__init__(container)
        self._type = "DOS3.3"
        self._volume_name: str = "DOS33"

    @property
    def root(self) -> "DirObj":
        return DirObj(self)

    def flush(self) -> None:
        pass

    def initialize(self) -> None:
        pass

    def info(self, vtoc: bool = False) -> str:
        s = f"{self.type}\n"
        s += f"Container={self.container.container_name}"
        return s

    def ext_to_filetype(self, ext: str) -> bytes:
        return DOS33FiletypesMap.get(ext, DOS33FiletypesMap["BIN"])

    def filetype_to_ext(self, ftype: bytes) -> str:
        # upper bit is the "locked" flag
        b = ftype[0] & 127
        for key, value in DOS33FiletypesMap.items():
            if value == b:
                return key
        return "BIN"
