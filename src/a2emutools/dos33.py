import struct
from typing import List, Optional, Tuple, Union

from a2emutools.container_formats import DiskImage
from a2emutools.filesystem import Access, DirObj, FileObj, FileSystem

DOS33FiletypesMap = dict(
    TXT=b"\x00",
    INT=b"\x01",
    BAS=b"\x02",
    BIN=b"\x04",
    S=b"\x08",
    R=b"\x10",
    A=b"\x20",
    B=b"\x40",
)


class DOS33FileObj(FileObj):
    def __init__(self, file_system: "DOS33FileSystem", name: str, parent: "DirObj") -> None:
        super().__init__(file_system, name, parent)
        self._dfs = file_system
        # where is the file in the catalog
        self._parent_track: int = 0
        self._parent_sector: int = 0
        self._parent_index: int = 0
        # where is the track/sector list start for this file
        self._ts_list_track: int = 0
        self._ts_list_sector: int = 0

    def setup(
        self,
        filetype: int = 0,
        parent_tsi: Tuple[int, int, int] = (0, 0, 0),
        ts_list: Tuple[int, int] = (0, 0),
        size: int = 0,
        **kwargs,
    ) -> None:
        """build a file object"""
        # where is it in the catalog (for deletion purposes)
        self._parent_track = parent_tsi[0]
        self._parent_sector = parent_tsi[1]
        self._parent_index = parent_tsi[2]
        # where is the track/sector list for this file
        self._ts_list_track = ts_list[0]
        self._ts_list_sector = ts_list[1]
        # file size in sectors
        self._file_size = size
        # handle the file type and access flags
        flags = Access.ALL
        if filetype & 0x80:
            flags = Access.READ
        self._access = Access(flags)
        self._file_type = self._fs.filetype_to_ext(filetype & 0x7F)

    def _read(self) -> None:
        self._data = bytearray()
        # read the track/sector list
        ts_sector = self._fs.container.read_sector(self._ts_list_track, self._ts_list_sector)
        next_ts_track = ts_sector[1]
        next_ts_sector = ts_sector[2]
        # start with the first few bytes
        sector_index = 0
        raw_data = self._fs.container.read_sector(
            ts_sector[0x0C + sector_index * 2], ts_sector[0x0C + sector_index * 2 + 1]
        )
        # Reading file formats are very different
        # T = read sectors until EOF (00)
        if self.file_type == "TXT":
            while True:
                index = raw_data.find(0)
                if index != -1:
                    # no EOF, copy entire sector
                    self._data += raw_data
                    # next sector
                    sector_index += 1
                    # wrap to next track/sector list if needed
                    if sector_index == self._dfs.max_ts_pairs:
                        if next_ts_track == 0:
                            break
                        ts_sector = self._fs.container.read_sector(next_ts_track, next_ts_sector)
                        next_ts_track = ts_sector[1]
                        next_ts_sector = ts_sector[2]
                        sector_index = 0
                    raw_data = self._fs.container.read_sector(
                        ts_sector[0x0C + sector_index * 2], ts_sector[0x0C + sector_index * 2 + 1]
                    )
                else:
                    # EOF found, copy up to EOF and stop
                    self._data += raw_data[:index]
                    self._file_size = len(self._data)
                    self._aux_bits = 0
                    break
        # B = starts with load address and file length (16-bit numbers), then raw data
        # A = starts with file length (16-bit numbers), then encoded Applesoft BASIC
        # I = same as A, but for Integer BASIC
        elif self.file_type in ("BIN", "BAS", "INT"):
            # basically the same, except that BIN has a 2-byte load address at the start
            if self.file_type == "BIN":
                self._aux_bits = raw_data[0] + (raw_data[1] << 8)
                self._file_size = raw_data[2] + (raw_data[3] << 8)
                self._data = raw_data[4:]
            else:
                self._aux_bits = 0
                self._file_size = raw_data[0] + (raw_data[1] << 8)
                self._data = raw_data[2:]
            while len(self._data) < self._file_size:
                # next sector
                sector_index += 1
                # wrap to next track/sector list if needed
                if sector_index == self._dfs.max_ts_pairs:
                    if next_ts_track == 0:
                        break
                    ts_sector = self._fs.container.read_sector(next_ts_track, next_ts_sector)
                    next_ts_track = ts_sector[1]
                    next_ts_sector = ts_sector[2]
                    sector_index = 0
                raw_data = self._fs.container.read_sector(
                    ts_sector[0x0C + sector_index * 2], ts_sector[0x0C + sector_index * 2 + 1]
                )
                self._data += raw_data
            self._data = self._data[: self._file_size]
        else:
            raise RuntimeError(f"Unsupported DOS 3.3 file type: {self.file_type}")
        self._synced = True

        # Notes: R format is not implemented (relocatable binary) but first 6 bytes are:
        #   2 bytes load address - RAM image starting address
        #   2 bytes exec address - RAM image length
        #   2 bytes file length - length of file data following these 6 bytes

    def _write(self) -> None:
        self._synced = True

    def delete(self) -> None:
        pass

    def info(self) -> str:
        s = " "
        if not (self.access & Access.WRITE):
            s = "*"
        s += f"{self.name:31}"
        s += f"{self.file_type:5}"
        s += f" {self.file_size:03d}"
        return s


class DOS33DirObj(DirObj):
    def __init__(
        self, file_system: "DOS33FileSystem", name: str = "", parent: Optional["DirObj"] = None
    ) -> None:
        super().__init__(file_system, name, parent)
        self._dfs = file_system
        self._type: str = "DOS 3.3"
        self._children: List[Union["DirObj", "FileObj"]] = []

    def setup(self, track: int = 0, sector: int = 0, **kwargs) -> None:
        catalog_hdr = "<BB"
        catalog_entry = "<BBB30sH"
        # there are no subdirectories in DOS 3.3, so this is the root directory only
        while track != 0:
            raw_sector = self._fs.container.read_sector(track, sector)
            for i in range(7):
                offset = 0x0B + i * 0x23
                tmp = struct.unpack_from(catalog_entry, raw_sector, offset)
                file_track = int(tmp[0])
                if (file_track == 0) or (file_track == 0xFF):  # unused or deleted entry
                    continue  # skip it
                file_sector = int(tmp[1])
                file_flags = int(tmp[2])
                file_name = (
                    bytearray([b & 0x7F for b in tmp[3]]).decode("ascii").rstrip("\0").strip(" ")
                )
                file_length = int(tmp[4])
                file_obj = DOS33FileObj(self._dfs, file_name, self)
                parent_tsi = (track, sector, i)
                file_obj.setup(
                    filetype=file_flags,
                    parent_tsi=parent_tsi,
                    ts_list=(file_track, file_sector),
                    size=file_length,
                )
                self._children.append(file_obj)
            # Next sector to parse...
            tmp = struct.unpack_from(catalog_hdr, raw_sector, 1)
            track = int(tmp[0])
            sector = int(tmp[1])

    def create_file(self, name: str, filetype: str) -> Optional["FileObj"]:
        return None

    def create_directory(self, name: str) -> Optional["DirObj"]:
        raise RuntimeError("Subdirectories are not supported on this filesystem.")

    def children(self) -> List[Union["DirObj", "FileObj"]]:
        return self._children

    def delete(self):
        pass


class DOS33FileSystem(FileSystem):
    @staticmethod
    def is_format(container: "DiskImage") -> bool:
        info = DOS33FileSystem._read_volume_directory(container)
        return info["valid"]

    @staticmethod
    def _read_volume_directory(container: "DiskImage") -> dict:
        """Read the ProDOS Volume Directory from block 2 of the container.
        Parameters
        ----------
        container : DiskImage
            The image container to read from.

        Returns
        -------
        dict
            A dictionary with volume information.
        """
        vtoc_format = "<cBBBHB32sB8sBBHBBH40L"

        info = {"valid": False}
        # Try to read the DOS 3.3 VTOC from track 17, sector 0.
        raw_sector = container.read_sector(17, 0)
        tmp = struct.unpack_from(vtoc_format, raw_sector, 0)
        # tmp[0] = unused (1byte)
        # tmp[1] = CATALOG_TRACK (1byte)
        info["cat_track"] = tmp[1]
        # tmp[2] = CATALOG_SECTOR (1byte)
        info["cat_sector"] = tmp[2]
        # tmp[3] = DOS_VERSION (1byte)
        dos_version = tmp[3]
        if dos_version != 3:
            return info
        # tmp[4] = unused (2bytes)
        # tmp[5] = VOLUME_NUMBER (1byte)
        info["volume_num"] = tmp[5]
        # tmp[6] = unused (32bytes)
        # tmp[7] = MAX_T/S_PAIRS (1byte)
        info["max_ts_pairs"] = tmp[7]
        if info["max_ts_pairs"] != 122:
            return info
        # tmp[8] = unused (8bytes)
        # tmp[9] = LAST_TRACK (1byte)
        # last_track = int(tmp[9])
        # tmp[10] = DIRECTION (1byte)
        # direction = int(tmp[10])
        # tmp[11] = unused (2bytes)
        # tmp[12] = NUM_TRACKS (1byte)
        info["num_tracks"] = tmp[12]
        # tmp[13] = NUM_SECTORS (1byte)
        num_sectors = tmp[13]
        if num_sectors != 16:
            return info
        info["num_sectors"] = num_sectors
        # tmp[14] = NUM_BYTES_PER_SECTOR (2bytes)
        num_bytes_per_sector = int(tmp[14])
        if num_bytes_per_sector != 256:
            return info
        # 40 potential tracks, one bit per sector, 4 bytes/track
        # tmp[15...] = SECTOR_BITMAPS 40 longs
        # bitmaps = tmp[15]
        info["valid"] = True
        return info

    def __init__(self, container: "DiskImage") -> None:
        super().__init__(container)
        self._type = "DOS3.3"
        self._volume_name: str = "DOS33"
        info = DOS33FileSystem._read_volume_directory(container)
        self._volume_number: int = info["volume_num"]
        self._num_tracks: int = info["num_tracks"]
        self._num_sectors: int = info["num_sectors"]
        self._cat_track: int = info["cat_track"]
        self._cat_sector: int = info["cat_sector"]
        self._max_ts_pairs = info["max_ts_pairs"]
        self._bitmap = bytearray(self.num_tracks * self.num_sectors)  # one byte per sector
        self._read_sector_bitmap()
        self._root: Optional[DOS33DirObj] = None

    @property
    def max_ts_pairs(self) -> int:
        return self._max_ts_pairs

    def _read_sector_bitmap(self) -> None:
        """Fill the block allocation bitmap from the container."""
        # Read the DOS 3.3 VTOC from track 17, sector 0.
        # for a given sector, (offset, mask) of the bitmap byte
        sec_map = [
            (1, 0x01),
            (1, 0x02),
            (1, 0x04),
            (1, 0x08),
            (1, 0x10),
            (1, 0x20),
            (1, 0x40),
            (1, 0x80),
            (0, 0x01),
            (0, 0x02),
            (0, 0x04),
            (0, 0x08),
            (0, 0x10),
            (0, 0x20),
            (0, 0x40),
            (0, 0x80),
        ]
        raw_sector = self.container.read_sector(0x11, 0x00)
        for i in range(self.num_tracks):
            for j in range(self._num_sectors):
                # Bitmap for one track is 4 bytes: 89abcdef 01234567 00000000 00000000 lsb-hsb
                (sector_offset, mask) = sec_map[j]
                offset = 0x38 + i * 4 + sector_offset
                if raw_sector[offset] & mask:
                    self._bitmap[i * self._num_sectors + j] = 1
                else:
                    self._bitmap[i * self._num_sectors + j] = 0

    def _write_sector_bitmap(self) -> None:
        """Write the block allocation bitmap back to the container."""
        sec_map = [
            (1, 0x01),
            (1, 0x02),
            (1, 0x04),
            (1, 0x08),
            (1, 0x10),
            (1, 0x20),
            (1, 0x40),
            (1, 0x80),
            (0, 0x01),
            (0, 0x02),
            (0, 0x04),
            (0, 0x08),
            (0, 0x10),
            (0, 0x20),
            (0, 0x40),
            (0, 0x80),
        ]
        raw_sector = self.container.read_sector(0x11, 0x00)
        for i in range(self.num_tracks):
            for j in range(self._num_sectors):
                (sector_offset, mask) = sec_map[j]
                offset = 0x38 + i * 4 + sector_offset
                index = i * self._num_sectors + j
                if self._bitmap[index]:
                    raw_sector[offset] |= mask
                else:
                    raw_sector[offset] &= ~mask
        self.container.write_sector(0x11, 0x00, raw_sector)

    def _allocate_sectors(self, num: int) -> List[Tuple[int, int]]:
        """Allocate sectors on the disk.

        Parameters
        ----------
        num : int
            The number of sectors to allocate.

        Returns
        -------
        List[Tuple[int, int]]
            A list of (track, sector) tuples for the allocated sectors.
        """
        if num > self._bitmap.count(0):
            raise RuntimeError("Not enough free sectors available.")
        allocated: List[Tuple[int, int]] = []
        for i in range(self.num_tracks * self.num_sectors):
            if self._bitmap[i] == 0:
                track = i // self.num_sectors
                sector = i % self.num_sectors
                self._bitmap[i] = 1
                allocated.append((track, sector))
            if len(allocated) == num:
                break
        return allocated

    def _free_sectors(self, sectors: List[Tuple[int, int]]) -> None:
        """Free previously allocated sectors.

        Parameters
        ----------
        sectors : List[Tuple[int, int]]
            A list of (track, sector) tuples to free.
        """
        for track, sector in sectors:
            index = track * self.num_sectors + sector
            self._bitmap[index] = 0

    @property
    def num_tracks(self) -> int:
        return self._num_tracks

    @property
    def num_sectors(self) -> int:
        return self._num_sectors

    @property
    def volume_number(self) -> int:
        return self._volume_number

    @property
    def root(self) -> "DirObj":
        if self._root is None:
            self._root = DOS33DirObj(self)
            self._root.setup(track=self._cat_track, sector=self._cat_sector)
        return self._root

    def flush(self) -> None:
        pass

    def initialize(self) -> None:
        pass

    def info(self, vtoc: bool = False) -> str:
        s = super().info(vtoc=vtoc)
        s += f"\nVolume number: {self.volume_number}"
        s += f"\nTotal tracks: {self.num_tracks}"
        s += f"\nSectors per track: {self.num_sectors}"
        s += f"\nTotal sectors: {self.num_tracks * self.num_sectors}"
        s += f"\nUsed sectors: {self._bitmap.count(1)}"
        s += f"\nFree sectors: {self._bitmap.count(0)}"
        if vtoc:
            s += "\nSector allocation (*=used,.=free):\n"
            s += "      0000000000111111\n"
            s += "Trk#: 0123456789012345"
            for i in range(self.num_tracks * self.num_sectors):
                if i % self.num_sectors == 0:
                    s += f"\n{(i//self.num_sectors):04d}: "
                s += "." if self._bitmap[i] else "*"
        return s

    def ls_info_header(self, prefix: str) -> str:
        used = self._bitmap.count(1)
        total = len(self._bitmap)
        s = f"DOS 3.3 DISK Volume: {self.volume_number:03d} Used: {used:03d} of {total:03d}\n"
        s += "-----------------------------------------\n"
        return s

    def ls_info_footer(self, prefix: str) -> str:
        s = "-----------------------------------------"
        return s

    def ext_to_filetype(self, ext: str) -> bytes:
        if ext.startswith("d3_"):
            t = int(ext[2:])
            return bytes(t)
        return DOS33FiletypesMap.get(ext, DOS33FiletypesMap["BIN"])

    def filetype_to_ext(self, ftype: int) -> str:
        for key, value in DOS33FiletypesMap.items():
            if int(value[0]) == ftype:
                return key
        return f"d3_{ftype:03d}"
