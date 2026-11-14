"""
Automated end-to-end integration test for Active Mode (PORT) operations.
Verifies server connecting back to client listener and SHA-256 byte-level integrity.
"""

import os
import shutil
import sys
import threading
import time

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from client.ftp_client import FTPClient
from client.integrity import compute_file_sha256
from server.ftp_server import FTPServer
from tests.generate_assets import generate_test_assets


def run_active_mode_test():
    print("\n" + "=" * 60)
    print(" >>> RUNNING TEST SUITE: ACTIVE MODE (PORT)")
    print("=" * 60)

    server_root = "storage/test_server_root_act"
    client_ws = "storage/test_client_ws_act"

    # Clean prior test runs
    if os.path.exists(server_root):
        shutil.rmtree(server_root)
    if os.path.exists(client_ws):
        shutil.rmtree(client_ws)

    os.makedirs(server_root, exist_ok=True)
    os.makedirs(client_ws, exist_ok=True)

    # Generate assets in server root
    generate_test_assets(server_root)

    test_port = 2126
    server = FTPServer(host="127.0.0.1", port=test_port, root_dir=server_root)
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    time.sleep(0.5)

    client = FTPClient(show_wire=True)
    try:
        # 1. Connect & Login
        client.connect("127.0.0.1", test_port)
        client.login("admin", "password123")

        # 2. Switch to Active Mode (PORT)
        client.set_mode(FTPClient.MODE_ACTIVE)

        # 3. LIST via Active Mode
        print("\n--- Testing LIST in Active Mode ---")
        listing = client.list()
        assert "welcome.txt" in listing
        assert "dataset_1mb.bin" in listing
        print("[PASS] Active Mode LIST successfully received directory listing.")

        # 4. RETR via Active Mode (Download 1MB binary dataset)
        print("\n--- Testing RETR in Active Mode ---")
        remote_file = "dataset_1mb.bin"
        local_dest = os.path.join(client_ws, "active_download_1mb.bin")
        n_bytes, sha_client = client.retrieve_file(remote_file, local_dest)
        src_path = os.path.join(server_root, remote_file)
        sha_server = compute_file_sha256(src_path)
        assert sha_client == sha_server, f"Active RETR Hash mismatch! Server: {sha_server} != Client: {sha_client}"
        assert n_bytes == os.path.getsize(src_path)
        print(f"[PASS] Active Mode RETR SHA-256 match! ({n_bytes} bytes: {sha_client})")

        # 5. STOR via Active Mode (Upload 1MB binary file)
        print("\n--- Testing STOR in Active Mode ---")
        upload_src = os.path.join(client_ws, "active_upload_src.bin")
        with open(upload_src, "wb") as f:
            f.write(os.urandom(1048576))  # 1 MB
        upload_sha = compute_file_sha256(upload_src)

        client.store_file(upload_src, "active_uploaded_file.bin")
        uploaded_on_server = os.path.join(server_root, "active_uploaded_file.bin")
        assert os.path.exists(uploaded_on_server)
        server_uploaded_sha = compute_file_sha256(uploaded_on_server)
        assert upload_sha == server_uploaded_sha, "Active STOR SHA-256 mismatch!"
        print(f"[PASS] Active Mode STOR SHA-256 match! ({server_uploaded_sha})")

        # 6. QUIT
        client.quit()
        print("\n*** ALL ACTIVE MODE TESTS PASSED PERFECTLY ***\n")

    finally:
        server.stop()
        if os.path.exists(server_root):
            shutil.rmtree(server_root)
        if os.path.exists(client_ws):
            shutil.rmtree(client_ws)


if __name__ == "__main__":
    run_active_mode_test()

