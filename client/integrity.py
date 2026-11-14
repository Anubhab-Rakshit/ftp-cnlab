"""
Cryptographic integrity checker (SHA-256) for verifying file transfers.
"""

import hashlib
import os
from common.rfc959 import BUFFER_SIZE


def compute_file_sha256(file_path: str) -> str:
    """Computes the SHA-256 hex digest of a local file."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(BUFFER_SIZE)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_integrity(file_path_a: str, file_path_b: str) -> bool:
    """Returns True if both files are byte-for-byte identical via SHA-256."""
    if not os.path.exists(file_path_a) or not os.path.exists(file_path_b):
        return False
    return compute_file_sha256(file_path_a) == compute_file_sha256(file_path_b)

