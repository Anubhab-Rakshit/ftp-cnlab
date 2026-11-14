"""
Virtual File System (VFS) with Chroot-like Sandboxing and Directory Listing.
Guarantees path traversal protection and RFC 959 path conventions.
"""

import os
import stat
import time
from pathlib import Path
from typing import Tuple, List, Optional
from common.rfc959 import TELNET_EOL


class VirtualFileSystem:
    """Provides a safe, isolated virtual filesystem mapped to a real directory."""

    def __init__(self, root_dir: str):
        self.root_dir = os.path.realpath(os.path.abspath(root_dir))
        os.makedirs(self.root_dir, exist_ok=True)
        self.current_virtual_dir = "/"

    def _sanitize_virtual(self, vpath: str) -> str:
        """Normalizes a virtual path to start with / and removes relative dots."""
        if not vpath or vpath == ".":
            return self.current_virtual_dir
        if not vpath.startswith("/"):
            vpath = os.path.join(self.current_virtual_dir, vpath)
        # Normalize ../ and ./ safely in POSIX virtual space
        parts = []
        for segment in vpath.split("/"):
            if not segment or segment == ".":
                continue
            if segment == "..":
                if parts:
                    parts.pop()
            else:
                parts.append(segment)
        return "/" + "/".join(parts)

    def resolve(self, virtual_or_relative_path: str) -> Tuple[str, str]:
        """
        Resolves a virtual or relative path into (real_absolute_path, clean_virtual_path).
        Raises PermissionError if the resulting path escapes the server root.
        """
        clean_virtual = self._sanitize_virtual(virtual_or_relative_path)
        # Convert virtual path (e.g. /folder/file) to real path
        rel_to_root = clean_virtual.lstrip("/")
        real_target = os.path.realpath(os.path.join(self.root_dir, rel_to_root))

        # Security check: must start with root_dir
        if not real_target.startswith(self.root_dir):
            raise PermissionError(f"Access denied: '{virtual_or_relative_path}' attempts path traversal.")

        return real_target, clean_virtual

    def pwd(self) -> str:
        """Returns the current virtual working directory."""
        return self.current_virtual_dir

    def cwd(self, target_path: str) -> str:
        """Changes current working directory. Returns the new virtual path."""
        real_path, clean_virtual = self.resolve(target_path)
        if not os.path.exists(real_path):
            raise FileNotFoundError(f"Directory not found: {clean_virtual}")
        if not os.path.isdir(real_path):
            raise NotADirectoryError(f"Not a directory: {clean_virtual}")
        self.current_virtual_dir = clean_virtual
        return self.current_virtual_dir

    def cdup(self) -> str:
        """Moves to parent directory."""
        return self.cwd("..")

    def make_dir(self, dir_path: str) -> str:
        """Creates a directory. Returns created virtual path."""
        real_path, clean_virtual = self.resolve(dir_path)
        if os.path.exists(real_path):
            raise FileExistsError(f"Already exists: {clean_virtual}")
        os.makedirs(real_path, exist_ok=False)
        return clean_virtual

    def remove_dir(self, dir_path: str):
        """Removes an empty directory."""
        real_path, clean_virtual = self.resolve(dir_path)
        if not os.path.exists(real_path):
            raise FileNotFoundError(f"Directory not found: {clean_virtual}")
        if not os.path.isdir(real_path):
            raise NotADirectoryError(f"Not a directory: {clean_virtual}")
        os.rmdir(real_path)

    def delete_file(self, file_path: str):
        """Deletes a file."""
        real_path, clean_virtual = self.resolve(file_path)
        if not os.path.exists(real_path):
            raise FileNotFoundError(f"File not found: {clean_virtual}")
        if os.path.isdir(real_path):
            raise IsADirectoryError(f"Is a directory: {clean_virtual}")
        os.remove(real_path)

    def rename(self, src_path: str, dst_path: str):
        """Renames a file or directory."""
        real_src, _ = self.resolve(src_path)
        real_dst, _ = self.resolve(dst_path)
        if not os.path.exists(real_src):
            raise FileNotFoundError(f"Source not found: {src_path}")
        os.rename(real_src, real_dst)

    def get_size(self, file_path: str) -> int:
        """Returns size in bytes of a file."""
        real_path, clean_virtual = self.resolve(file_path)
        if not os.path.exists(real_path):
            raise FileNotFoundError(f"File not found: {clean_virtual}")
        if os.path.isdir(real_path):
            raise IsADirectoryError(f"Is a directory: {clean_virtual}")
        return os.path.getsize(real_path)

    def list_dir(self, target_path: Optional[str] = None, detailed: bool = True) -> bytes:
        """
        Generates RFC 959 directory listing (Unix 'ls -l' style) terminated by \\r\\n.
        Returns bytes ready for streaming over the data socket.
        """
        query_path = target_path if target_path else self.current_virtual_dir
        real_path, _ = self.resolve(query_path)

        if not os.path.exists(real_path):
            raise FileNotFoundError(f"Path not found: {query_path}")

        lines: List[str] = []

        if os.path.isfile(real_path):
            # Single file listing
            lines.append(self._format_entry(os.path.basename(real_path), real_path, detailed))
        else:
            # Directory listing
            entries = sorted(os.listdir(real_path))
            for item in entries:
                full_item_path = os.path.join(real_path, item)
                lines.append(self._format_entry(item, full_item_path, detailed))

        listing_str = TELNET_EOL.join(lines)
        if listing_str:
            listing_str += TELNET_EOL
        return listing_str.encode("utf-8")

    def _format_entry(self, name: str, full_path: str, detailed: bool) -> str:
        """Formats a single file entry into standard Unix ls -l style."""
        if not detailed:
            return name
        try:
            st = os.stat(full_path)
            is_dir = stat.S_ISDIR(st.st_mode)
            type_char = "d" if is_dir else "-"
            # File permissions string
            mode = st.st_mode
            perms = [
                "r" if mode & stat.S_IRUSR else "-",
                "w" if mode & stat.S_IWUSR else "-",
                "x" if mode & stat.S_IXUSR else "-",
                "r" if mode & stat.S_IRGRP else "-",
                "w" if mode & stat.S_IWGRP else "-",
                "x" if mode & stat.S_IXGRP else "-",
                "r" if mode & stat.S_IROTH else "-",
                "w" if mode & stat.S_IWOTH else "-",
                "x" if mode & stat.S_IXOTH else "-",
            ]
            perm_str = type_char + "".join(perms)
            nlink = st.st_nlink
            size = st.st_size
            mtime = time.localtime(st.st_mtime)
            # Format time: e.g. "Nov 13 20:30"
            time_str = time.strftime("%b %d %H:%M", mtime)
            return f"{perm_str:10} {nlink:3} ftp ftp {size:10} {time_str} {name}"
        except Exception:
            return f"-rw-r--r--   1 ftp ftp          0 Jan 01 00:00 {name}"

