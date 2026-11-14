"""
Generates realistic test assets for testing FTP streaming, binary integrity, and concurrency.
"""

import os
import secrets


def generate_test_assets(target_dir: str = "storage/server_root"):
    os.makedirs(target_dir, exist_ok=True)

    # 1. Plain text file (ASCII)
    text_path = os.path.join(target_dir, "welcome.txt")
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(
            "Welcome to the RFC 959 FTP Server!\n"
            "Computer Networks Lab Project\n"
            "Features:\n"
            "- Dual channel architecture (Control & Data)\n"
            "- Active (PORT) & Passive (PASV) modes\n"
            "- Real-time chunked byte streaming\n"
            "- SHA-256 cryptographically verified integrity\n"
        )
    print(f"Created text asset: {text_path} ({os.path.getsize(text_path)} bytes)")

    # 2. Medium binary file (1 Megabyte)
    med_path = os.path.join(target_dir, "dataset_1mb.bin")
    with open(med_path, "wb") as f:
        # 16 chunks of 64KB random bytes
        for _ in range(16):
            f.write(secrets.token_bytes(65536))
    print(f"Created 1MB binary asset: {med_path} ({os.path.getsize(med_path)} bytes)")

    # 3. Large binary file (5 Megabytes)
    large_path = os.path.join(target_dir, "archive_5mb.bin")
    with open(large_path, "wb") as f:
        for _ in range(80):
            f.write(secrets.token_bytes(65536))
    print(f"Created 5MB binary asset: {large_path} ({os.path.getsize(large_path)} bytes)")

    # 4. Mock PNG Image asset (header + dummy image bytes)
    img_path = os.path.join(target_dir, "network_diagram.png")
    png_header = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    with open(img_path, "wb") as f:
        f.write(png_header + secrets.token_bytes(32768))
    print(f"Created image asset: {img_path} ({os.path.getsize(img_path)} bytes)")


if __name__ == "__main__":
    generate_test_assets()

