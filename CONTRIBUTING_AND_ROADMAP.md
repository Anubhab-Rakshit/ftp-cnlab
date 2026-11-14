# Contributor Roadmap & Extension Guide
**For Collaborators and Friends working on the RFC 959 FTP Project**

---

## 1. Project Overview & Architecture
This project is an **RFC 959-compliant, pure-socket File Transfer Protocol (FTP)** client-server implementation in Python.
It does **NOT** use any high-level libraries (`ftplib`, `pyftpdlib`). All interactions are raw TCP sockets (`socket.socket(AF_INET, SOCK_STREAM)`).

### Quick Architecture Refresher
* **Control Channel (Port 2121)**: Persistent TCP socket for text commands terminated by `\r\n` and 3-digit reply codes.
* **Data Channel**: Ephemeral TCP sockets dynamically opened per transfer (`LIST`, `RETR`, `STOR`, `APPE`).
  * **Active Mode (`PORT`)**: Client listens, server connects to client.
  * **Passive Mode (`PASV` / `EPSV`)**: Server listens, client connects to server.
* **VFS (Virtual File System)**: Chroot-jailed root directory (`storage/server_root`) with path-traversal protection.
* **Integrity**: SHA-256 computed on both ends to ensure 100% byte fidelity without data corruption.

---

## 2. Recommended High-Value Improvements

Here are actionable features you can implement for extra credit or systems engineering depth:

### Feature 1: Transfer Resumption (`REST` + `reget` / `reput`)
* **Background**: The server already has `REST <offset>` implemented in `server/session.py`.
* **Action**:
  1. In `client/cli.py`, add a command `reget <remote_file> [<local_dest>]`.
  2. If the local file already exists partially (e.g., 2 MB out of 5 MB), get its size `os.path.getsize(local_dest)`.
  3. Send `REST <size>` before `RETR <remote_file>`.
  4. Open the local file in `"ab"` (append binary) mode and stream remaining chunks.
* **Testing**: Download halfway, simulate network failure, resume, and verify SHA-256 match.

### Feature 2: Bandwidth Throttling / Rate Limiting (Token Bucket)
* **Background**: Demonstrating Quality of Service (QoS) and rate control in Wireshark throughput graphs.
* **Action**:
  1. Add a `--rate-limit <bytes_per_sec>` argument in server and client.
  2. In chunk streaming loops, calculate:
     $$\Delta t = \frac{\text{Chunk Size}}{\text{Target Rate}} - \text{Time Taken}$$
  3. If $\Delta t > 0$, call `time.sleep(\Delta t)`.
* **Wireshark Demonstration**: Use **Statistics $\to$ I/O Graphs** to show an uncapped bursty line vs. a flat, rate-limited line.

### Feature 3: Explicit TLS/SSL Encryption (FTPS - RFC 4217)
* **Background**: Securing control and data channels against eavesdropping.
* **Action**:
  1. Use Python’s built-in `ssl` module (`ssl.SSLContext`).
  2. Implement `AUTH TLS` command on server.
  3. Upon `AUTH TLS`, upgrade existing control socket with `context.wrap_socket()`.
  4. Implement `PROT P` (Private data channel encryption).
* **Wireshark Demonstration**: Show cleartext `USER` / `PASS` on plain FTP vs. encrypted `Application Data (TLS)` frames on FTPS.

### Feature 4: Dual-Pane Terminal TUI (Terminal User Interface)
* **Action**: Use Python's built-in `curses` or `rich` library to build a dual-pane terminal client:
  * Left pane: Local workspace files (`storage/client_workspace/`).
  * Right pane: Remote server files (`storage/server_root/`).
  * Status footer: Transfer speed, progress bar, and raw packet log.

### Feature 5: Multi-Tenant Storage Quotas
* **Action**:
  1. In `server/auth.py`, add `quota_bytes` per user (e.g. 50 MB max).
  2. In `server/session.py` before accepting a `STOR` upload, check the total size of files owned by the user.
  3. If exceeded, return RFC code `552 Exceeded storage allocation`.

---

## 3. Project File Guide
```
ftp-work/
├── common/
│   ├── rfc959.py            # Status codes, constants, reply templates
│   ├── protocol_parser.py   # NVT/ASCII parser & PORT/PASV address encoders
│   └── logger.py            # Colorized console packet visualizer
├── server/
│   ├── ftp_server.py        # Main TCP listening daemon
│   ├── session.py           # Command dispatcher & state machine
│   ├── data_channel.py      # Active & Passive socket coordinator
│   ├── vfs.py               # Virtual File System & path traversal guard
│   └── auth.py              # User credentials store
├── client/
│   ├── ftp_client.py        # Pure socket client engine
│   ├── cli.py               # Interactive terminal shell
│   └── integrity.py         # SHA-256 integrity validator
├── storage/
│   ├── server_root/         # Server sandbox directory
│   └── client_workspace/    # Client local downloads & uploads
└── tests/
    ├── test_passive_mode.py # PASV end-to-end tests
    ├── test_active_mode.py  # PORT end-to-end tests
    ├── test_concurrency.py  # 6-client stress tests
    └── test_all.py          # Master test suite runner
```

---

## 4. How to Test Changes
Always ensure all test suites pass after any modification:
```bash
python3 tests/test_all.py
```
