"""
Stress and concurrency test: Multiple simultaneous FTP clients transferring files.
Proves multi-threaded connection handling without socket collisions or race conditions.
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


def worker_task(client_idx: int, port: int, server_root: str, base_ws: str, results: list):
    try:
        ws = os.path.join(base_ws, f"client_{client_idx}")
        os.makedirs(ws, exist_ok=True)

        client = FTPClient(show_wire=False)
        client.connect("127.0.0.1", port)
        client.login("admin", "password123")

        # Half use passive, half use active mode
        if client_idx % 2 == 0:
            client.set_mode(FTPClient.MODE_PASSIVE)
        else:
            client.set_mode(FTPClient.MODE_ACTIVE)

        # Download 1MB file
        remote_file = "dataset_1mb.bin"
        local_dest = os.path.join(ws, f"download_{client_idx}.bin")
        _, client_hash = client.retrieve_file(remote_file, local_dest)

        src_hash = compute_file_sha256(os.path.join(server_root, remote_file))
        if client_hash != src_hash:
            results.append((client_idx, False, "Hash mismatch on download"))
            return

        # Upload a client-specific file
        upload_path = os.path.join(ws, f"my_upload_{client_idx}.bin")
        with open(upload_path, "wb") as f:
            f.write(os.urandom(524288))  # 512 KB
        up_hash = compute_file_sha256(upload_path)

        remote_name = f"uploaded_from_c{client_idx}.bin"
        client.store_file(upload_path, remote_name)

        server_up_hash = compute_file_sha256(os.path.join(server_root, remote_name))
        if up_hash != server_up_hash:
            results.append((client_idx, False, "Hash mismatch on upload"))
            return

        client.quit()
        results.append((client_idx, True, "Success"))
    except Exception as e:
        results.append((client_idx, False, str(e)))


def run_concurrency_test(num_clients: int = 6):
    print("\n" + "=" * 60)
    print(f" >>> RUNNING CONCURRENCY TEST WITH {num_clients} PARALLEL CLIENTS")
    print("=" * 60)

    server_root = "storage/test_server_root_conc"
    client_ws = "storage/test_client_ws_conc"

    if os.path.exists(server_root):
        shutil.rmtree(server_root)
    if os.path.exists(client_ws):
        shutil.rmtree(client_ws)

    os.makedirs(server_root, exist_ok=True)
    os.makedirs(client_ws, exist_ok=True)

    generate_test_assets(server_root)

    test_port = 2127
    server = FTPServer(host="127.0.0.1", port=test_port, root_dir=server_root)
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    time.sleep(0.5)

    results = []
    threads = []
    start_t = time.time()

    for i in range(num_clients):
        t = threading.Thread(
            target=worker_task,
            args=(i, test_port, server_root, client_ws, results),
            name=f"ConcurrentWorker-{i}"
        )
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    duration = time.time() - start_t
    print(f"\nCompleted {num_clients} concurrent transfers in {duration:.2f} seconds.")

    all_passed = True
    for idx, status, msg in results:
        res_str = "PASS" if status else "FAIL"
        print(f"  Client {idx}: [{res_str}] {msg}")
        if not status:
            all_passed = False

    server.stop()
    if os.path.exists(server_root):
        shutil.rmtree(server_root)
    if os.path.exists(client_ws):
        shutil.rmtree(client_ws)

    assert all_passed, "One or more concurrent client transfers failed!"
    print("\n*** CONCURRENCY STRESS TEST PASSED COMPLETELY ***\n")


if __name__ == "__main__":
    run_concurrency_test()

