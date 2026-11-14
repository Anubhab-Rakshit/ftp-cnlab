# Pure Socket RFC 959 FTP Client-Server System
**Computer Networks Laboratory Project**

---

## 1. System Overview

A complete, standards-compliant **File Transfer Protocol (FTP)** client-server implementation built from scratch using raw Python TCP sockets (`socket.socket(AF_INET, SOCK_STREAM)`).

### Core Highlights
* **Zero 3rd-Party Abstractions**: Engineered purely with Python's standard library (`socket`, `threading`, `hashlib`, `os`). Does **NOT** use `ftplib` or `pyftpdlib`.
* **RFC 959 Dual-Channel Architecture**:
  * **Control Channel**: Persistent TCP socket (default port `2121`) implementing Telnet NVT/ASCII framing (`\r\n`).
  * **Data Channel**: Ephemeral TCP sockets dynamically created for data streaming and closed immediately at EOF.
* **Dual Operating Modes**:
  * **Active Mode (`PORT`)**: Client acts as listener, server initiates active connection.
  * **Passive Mode (`PASV` / `EPSV`)**: Server binds ephemeral listener, client initiates connection (firewall/NAT friendly).
* **Real-Time Chunked Streaming**: Files are transferred in 64 KB buffers directly between socket and disk streams, handling files of any size (tested up to multi-megabyte binary archives and images).
* **Live NVT/ASCII Packet Inspector**: Real-time console logging showing exact wire-level commands (`[CTRL:RECV]`, `[CTRL:SEND]`, `[DATA:ESTB]`, `[DATA:STRM]`, `[DATA:CLSE]`).
* **Cryptographic Integrity (SHA-256)**: Automated pre- and post-transfer cryptographic checksums ensure byte-for-byte fidelity without data corruption.
* **Virtual File System (VFS)**: Chroot-jailed root directory (`storage/server_root`) with path-traversal attack defenses.
* **100% Interoperability**: Fully compatible with custom client, CLI `curl`, standard system `ftp`, and FileZilla.

---

## 2. Architecture & Communication Flow

```
                      +---------------------------------------+
                      |         FTP Client (Python)           |
                      |  - Interactive Shell (prompt/history) |
                      |  - Terminal Progress Bar (Transfer)   |
                      |  - Active (PORT) & Passive (PASV)     |
                      +-------+-----------------------+-------+
                              |                       |
            NVT/ASCII Control | Port 2121             | Data Connection (PORT/PASV)
            Commands & Status | (Persistent TCP)      | (Ephemeral TCP, Per-Transfer)
                              v                       v
                      +-------+-----------------------+-------+
                      |         FTP Server (Python)           |
                      |  - Multi-threaded Session Handler     |
                      |  - Dual Channel Coordinator           |
                      |  - Virtual FS & Path Traversal Guard  |
                      |  - Real Chunked Stream Engine         |
                      +---------------------------------------+
```

---

## 3. Directory Layout

```
ftp-work/
├── README.md                          # Complete lab report & usage guide
├── FTP_IMPLEMENTATION_SPEC.md        # Detailed technical specification
├── grp-project-blueprint.md           # Original lab blueprint
├── common/
│   ├── __init__.py
│   ├── rfc959.py                      # RFC 959/2428 status codes, command constants
│   ├── protocol_parser.py             # NVT/ASCII parser & PORT/PASV address encoders
│   └── logger.py                      # Real-time console packet visualizer
├── server/
│   ├── __init__.py
│   ├── ftp_server.py                  # Multi-threaded server daemon entrypoint
│   ├── session.py                     # RFC 959 state machine & command dispatcher
│   ├── data_channel.py                # Active (PORT) and Passive (PASV) data manager
│   ├── vfs.py                         # Virtual File System with path-traversal guards
│   └── auth.py                        # User authentication store & permissions
├── client/
│   ├── __init__.py
│   ├── ftp_client.py                  # Core client protocol engine (raw sockets)
│   ├── cli.py                         # Interactive FTP shell with progress bar
│   └── integrity.py                   # SHA-256 calculation & validation utility
├── storage/
│   ├── server_root/                   # Server sandboxed storage
│   │   ├── welcome.txt
│   │   ├── dataset_1mb.bin
│   │   ├── archive_5mb.bin
│   │   └── network_diagram.png
│   └── client_workspace/              # Client download/upload workspace
└── tests/
    ├── __init__.py
    ├── generate_assets.py             # Generates test assets (text, images, binary)
    ├── test_passive_mode.py           # Automated test for Passive Mode (PASV)
    ├── test_active_mode.py            # Automated test for Active Mode (PORT)
    ├── test_concurrency.py            # Stress test with 6 simultaneous parallel clients
    └── test_all.py                    # Master test runner
```

---

## 4. Quick Start Guide

### Step 1: Start the FTP Server
In Terminal 1:
```bash
python3 -m server.ftp_server --port 2121
```
*The server will bind to `0.0.0.0:2121` and display live NVT/ASCII wire packets.*

### Step 2: Launch the Interactive FTP Client
In Terminal 2:
```bash
python3 -m client.cli --host 127.0.0.1 --port 2121
```

Once inside the `ftp> ` shell:
```text
ftp> user admin password123      # Authenticate
ftp> pwd                         # Print working directory
ftp> ls                          # List files (streamed over data channel)
ftp> mode passive                # Switch to Passive mode (or 'mode active')
ftp> get archive_5mb.bin         # Download file with live progress bar
ftp> sha256 downloaded_file.bin  # Verify SHA-256 checksum
ftp> put my_photo.png            # Upload a file
ftp> mkdir lab_folder            # Create directory
ftp> cd lab_folder               # Navigate
ftp> wire off                    # Toggle NVT/ASCII wire trace (on/off)
ftp> quit                        # Disconnect and exit
```

---

## 5. Verification & Test Suite

Run the comprehensive master test runner:
```bash
python3 tests/test_all.py
```
This runs:
1. **Passive Mode Suite**: Verifies authentication, directory navigation, 5MB binary download, 1MB upload, directory manipulation, path-traversal containment, and SHA-256 match.
2. **Active Mode Suite**: Verifies client listening socket setup, `PORT h1,h2,h3,h4,p1,p2` negotiation, server connect-back, 1MB streaming download, 1MB upload, and SHA-256 match.
3. **Concurrency Stress Test**: Spawns **6 simultaneous client threads** concurrently transferring binary files in both Active and Passive modes to stress-test the multi-threaded server.

---

## 6. Testing with Standard Tools (Interoperability)

### Testing with `curl`
```bash
# Download a file via curl
curl ftp://anonymous:guest@127.0.0.1:2121/welcome.txt

# Upload a file via curl
curl -T my_local_file.txt ftp://admin:password123@127.0.0.1:2121/
```

### Testing with OS Native CLI `ftp`
```bash
ftp -p 127.0.0.1 2121
```

---

## 7. Wireshark Capture & Lab Demonstration Guide

### How to Capture Packets
1. Open Wireshark and select the **Loopback interface (`lo0` on macOS / `any` on Linux)**.
2. Set Display Filter:
   ```text
   ftp || ftp-data
   ```
3. Start the FTP server and run a file transfer via the client or tests.

### What to Observe & Explain in Lab
1. **Control Connection Handshake (TCP 3-Way Handshake)**:
   * Client `SYN` $\to$ Server Port `2121`
   * Server `SYN, ACK` $\to$ Client
   * Client `ACK` $\to$ Server
2. **Telnet NVT/ASCII Framing**:
   * Inspect the `FTP` protocol packets: clear text commands terminated by `\r\n` (`USER`, `PASS`, `PORT`, `PASV`, `RETR`, `STOR`).
   * 3-digit reply codes (`220`, `331`, `230`, `150`, `226`).
3. **Data Channel Negotiation**:
   * **Active (`PORT`)**: Observe client transmitting `PORT 127,0,0,1,p1,p2`, followed by server initiating a new TCP handshake to `(p1*256 + p2)`.
   * **Passive (`PASV`)**: Observe server returning `227 Entering Passive Mode (127,0,0,1,p1,p2)`, followed by client initiating a new TCP handshake to that ephemeral port.
4. **Data Stream & EOF Teardown**:
   * Inspect the `FTP-DATA` packets streaming the payload.
   * Observe the sender sending a TCP `FIN` packet upon EOF, cleanly terminating the ephemeral data channel while the control channel remains persistent!

