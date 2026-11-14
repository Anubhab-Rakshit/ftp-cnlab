"""
Master Test Runner for RFC 959 FTP Project.
Executes all integration and unit test suites:
1. Passive Mode (PASV) transfers & VFS operations
2. Active Mode (PORT) transfers & server-callback
3. Concurrency Stress Test (Multiple parallel clients)
"""

import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.test_passive_mode import run_passive_mode_test
from tests.test_active_mode import run_active_mode_test
from tests.test_concurrency import run_concurrency_test


def main():
    print("\n" + "=" * 70)
    print("  RFC 959 FTP CLIENT-SERVER COMPREHENSIVE VERIFICATION SUITE")
    print("=" * 70)

    try:
        run_passive_mode_test()
        run_active_mode_test()
        run_concurrency_test(num_clients=6)

        print("\n" + "=" * 70)
        print("  \033[1;32mALL TEST SUITES PASSED SUCCESSFULLY (100% VERIFIED)\033[0m")
        print("  - RFC 959 Dual-Channel Control & Data Sockets: OK")
        print("  - Active Mode (PORT) & Passive Mode (PASV): OK")
        print("  - Real-Time Chunked Streaming & Large Binaries: OK")
        print("  - Cryptographic SHA-256 Byte-for-Byte Fidelity: OK")
        print("  - Multi-threaded Client Concurrency: OK")
        print("  - Virtual File System & Path Traversal Guards: OK")
        print("=" * 70 + "\n")
    except Exception as e:
        print(f"\n\033[1;31m[FAILED] Test suite encountered an error: {e}\033[0m\n")
        sys.exit(1)


if __name__ == "__main__":
    main()

