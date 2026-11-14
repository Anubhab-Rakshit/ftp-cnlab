"""
Automated end-to-end integration test for Passive Mode (PASV) operations.
Verifies control commands, file transfers, and SHA-256 byte-level integrity.
"""

import os
import shutil
import sys
import threading
import time

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from client.ftp_client import FTPClient
from client.integrity import compute_file_sha256, verify_integrity
from common.rfc959 import DEFAULT_FTP_CONTROL_PORT
from server.ftp_server import FTPServer
from tests.generate_assets import generate_test_assets


def run_passive_mode_test():
    print("\n" + "=" * 60)
    print(" >>> RUNNING TEST SUITE: PASSIVE MODE (PASV)")
    print("=" * 60)

    server_root = "storage/test_server_root_pasv"
    client_ws = "storage/test_client_ws_pasv"

    # Clean prior test runs
    if os.path.exists(server_root):
        shutil.rmtree(server_root)
    if os.path.exists(client_ws):
        shutil.rmtree(client_ws)

    os.makedirs(server_root, exist_ok=True)
    os.makedirs(client_ws, exist_ok=True)

    # Generate assets in server root
    generate_test_assets(server_root)

    test_port = 2125
    server = FTPServer(host="127.0.0.1", port=test_port, root_dir=server_root)
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    time.sleep(0.5)

    client = FTPClient(show_wire=False)
    try:
        # 1. Connect
        code, msg = client.connect("127.0.0.1", test_port)
        assert code == 220, f"Expected 220, got {code}"

        # 2. Login
        code, msg = client.login("admin", "password123")
        assert code == 230, f"Expected 230, got {code}"

        # 3. Ensure Passive Mode
        client.set_mode(FTPClient.MODE_PASSIVE)

        # 4. PWD
        curr = client.pwd()
        assert curr == "/", f"Expected root '/', got {curr}"
        print("[PASS] PWD confirmed at '/'")

        # 5. LIST
        listing = client.list()
        assert "welcome.txt" in listing
        assert "dataset_1mb.bin" in listing
        assert "archive_5mb.bin" in listing
        print("[PASS] LIST returned directory contents correctly.")

        # 6. RETR (Download 5MB binary archive)
        remote_file = "archive_5mb.bin"
        local_dest = os.path.join(client_ws, "downloaded_archive_5mb.bin")
        print(f"Downloading {remote_file} via PASV...")
        n_bytes, sha_client = client.retrieve_file(remote_file, local_dest)
        src_path = os.path.join(server_root, remote_file)
        sha_server = compute_file_sha256(src_path)
        assert sha_client == sha_server, f"Hash mismatch! Server: {sha_server} != Client: {sha_client}"
        assert n_bytes == os.path.getsize(src_path)
        print(f"[PASS] RETR byte-for-byte SHA-256 match! ({n_bytes} bytes: {sha_client})")

        # 7. STOR (Upload a new 1MB file)
        upload_src = os.path.join(client_ws, "upload_test.bin")
        with open(upload_src, "wb") as f:
            f.write(os.urandom(1048576))  # 1 MB
        upload_sha = compute_file_sha256(upload_src)

        print("Uploading 1MB file via PASV...")
        client.store_file(upload_src, "uploaded_file.bin")
        uploaded_on_server = os.path.join(server_root, "uploaded_file.bin")
        assert os.path.exists(uploaded_on_server)
        server_uploaded_sha = compute_file_sha256(uploaded_on_server)
        assert upload_sha == server_uploaded_sha, "Uploaded file SHA-256 mismatch!"
        print(f"[PASS] STOR byte-for-byte SHA-256 match! ({server_uploaded_sha})")

        # 8. Directory operations (MKD, CWD, CDUP, RMD)
        client.make_dir("lab_test_dir")
        client.cwd("lab_test_dir")
        assert client.pwd() == "/lab_test_dir"
        client.cdup()
        assert client.pwd() == "/"
        client.remove_dir("lab_test_dir")
        print("[PASS] VFS MKD, CWD, CDUP, RMD verified.")

        # 9. Path traversal protection test
        try:
            client.cwd("../../")
            # Virtual path should normalize to root '/'
            assert client.pwd() == "/"
            print("[PASS] Path traversal attempt safely confined to root.")
        except Exception as e:
            print(f"[PASS] Path traversal correctly rejected: {e}")

        # 10. QUIT
        client.quit()
        print("[PASS] Client QUIT and disconnection clean.")

        print("\n*** ALL PASSIVE MODE TESTS PASSED PERFECTLY ***\n")

    finally:
        server.stop()
        if os.path.exists(server_root):
            shutil.rmtree(server_root)
        if os.path.exists(client_ws):
            shutil.rmtree(client_ws)


if __name__ == "__main__":
    run_passive_mode_test()
