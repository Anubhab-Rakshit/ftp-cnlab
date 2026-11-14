# RFC 959 File Transfer Protocol (FTP) Implementation Specification
**Computer Networks Laboratory Project**

---

## 1. Executive Summary & Lab Scope

This project implements an **RFC 959-compliant, dual-channel File Transfer Protocol (FTP)** client and server from scratch using raw Python TCP sockets (`socket.socket(socket.AF_INET, socket.SOCK_STREAM)`).

### Core Principles
1. **Zero High-Level Abstractions**: No third-party FTP libraries (`ftplib`, `pyftpdlib`, etc.) are used. All network transport, handshaking, framing, and data streaming are engineered directly over raw Berkeley/POSIX sockets.
2. **Real-Time Data Streaming**: Transfers are performed via chunked streaming buffers (64 KB chunks) directly between disk and socket streams, supporting files of arbitrary size (from small ASCII files to multi-megabyte binary archives, images, and videos).
3. **Strict Wire-Format & Wireshark Compatibility**: All control messages follow Telnet Network Virtual Terminal (NVT) ASCII conventions (`\r\n` line delimiters, standard 3-digit reply codes). Captured traffic is recognized, dissected, and parsed natively by Wireshark's `ftp` and `ftp-data` dissectors.
4. **Interoperability**: The server can interoperate not only with its companion custom client, but also with industry-standard FTP clients (CLI `ftp`, `curl`, FileZilla).
5. **Mathematical Integrity Verification**: Every transfer includes SHA-256 checksum computation on both endpoints to verify byte-for-byte fidelity without data corruption.

---

## 2. Protocol Architecture

FTP separates control signaling from bulk data transfer across two distinct TCP channels:

```
+-----------------------------------------------------------------------+
|                             FTP Client                                |
|  - Interactive Shell (REPL)              - Real-time Progress Tracker |
|  - Active (PORT) Data Listener           - Passive (PASV) Connector   |
+-------------------+-------------------------------+-------------------+
                    |                               |
                    | Control Connection            | Data Connection
                    | Port: 2121 (Configurable)     | Port: Dynamic / Ephemeral
                    | Lifespan: Entire Session      | Lifespan: Single Data Transfer
                    v                               v
+-------------------+-------------------------------+-------------------+
|                             FTP Server                                |
|  - Multi-threaded Control Listener       - Active Connector           |
|  - State Machine & Command Dispatcher    - Passive Listener           |
|  - Virtual File System Sandbox           - Chunked Streaming Engine   |
+-----------------------------------------------------------------------+
```

### 2.1 The Control Connection
* **Transport**: TCP, persistent for the duration of the user session.
* **Port**: Default lab port `2121` (unprivileged high-port, avoiding `sudo`, configurable to `21`).
* **Framing**: Telnet NVT/ASCII:
  * Client commands: `<COMMAND> [<ARGUMENT>]\r\n` (e.g. `USER anonymous\r\n`, `RETR notes.pdf\r\n`).
  * Server responses: `<CODE> <MESSAGE>\r\n` or multiline `<CODE>-<MESSAGE>\r\n ... <CODE> <FINAL MESSAGE>\r\n`.
* **State Machine**:
  * `NOT_AUTHENTICATED` $\to$ Waiting for `USER`
  * `NEED_PASSWORD` $\to$ Waiting for `PASS`
  * `AUTHENTICATED` $\to$ Ready for command execution (`LIST`, `RETR`, `STOR`, `CWD`, etc.)
  * `TRANSFERRED` / `READY` $\to$ Ready for subsequent operations
  * `TERMINATED` $\to$ Upon `QUIT` or socket disconnect

### 2.2 The Data Connection
The data connection is **ephemeral**: it is established dynamically before a data command (`LIST`, `NLST`, `RETR`, `STOR`, `APPE`), transfers the payload, and is closed immediately at EOF to signal completion.

#### Active Mode (`PORT`)
In Active Mode, the **client acts as a listener** and the **server initiates the connection**:
1. Client binds a local ephemeral TCP port and begins listening.
2. Client sends `PORT h1,h2,h3,h4,p1,p2\r\n` over the control connection, where:
   $$\text{Client Port} = (p1 \times 256) + p2$$
3. Server receives `PORT`, decodes the IP and port, and replies with `200 Command okay`.
4. Client requests transfer (e.g. `RETR sample.bin`).
5. Server sends `150 Opening data connection` and executes `data_sock.connect((client_ip, client_port))`.
6. Data is streamed in chunks over the socket until EOF.
7. Server closes the data socket and sends `226 Transfer complete` over the control channel.

```
Client                                                  Server
  |                                                       |
  |-- (Opens listening socket on Port P)                 |
  |-- PORT h1,h2,h3,h4,p1,p2 --------------------------->| (Control)
  |<-- 200 PORT command successful -----------------------| (Control)
  |                                                       |
  |-- RETR file.txt ------------------------------------->| (Control)
  |<-- 150 Opening BINARY mode data connection -----------| (Control)
  |                                                       |
  |<==== [Server actively connects to Client:P] ==========| (Data Channel)
  |<================ Data Stream (Chunks) ===============| (Data Channel)
  |<==== [Server closes Data Channel at EOF] =============| (Data Channel)
  |                                                       |
  |<-- 226 Transfer complete -----------------------------| (Control)
```

#### Passive Mode (`PASV`)
In Passive Mode, the **server acts as a listener** and the **client initiates the connection** (firewall-friendly):
1. Client sends `PASV\r\n` over the control channel.
2. Server binds an ephemeral TCP port, starts listening, and responds:
   `227 Entering Passive Mode (h1,h2,h3,h4,p1,p2)\r\n`
3. Client decodes the IP and port and calls `data_sock.connect((server_ip, server_port))`.
4. Client sends the transfer command (`RETR`, `STOR`, `LIST`).
5. Server sends `150 Opening BINARY mode data connection` and accepts the incoming data socket.
6. Payload is streamed in chunks until EOF, the data socket is closed, and `226 Transfer complete` is returned.

---

## 3. Supported RFC 959 Command Set

| Command | Arguments | Category | RFC Description |
| :--- | :--- | :--- | :--- |
| `USER` | `<username>` | Authentication | Specify user identity |
| `PASS` | `<password>` | Authentication | Specify user password |
| `QUIT` | *None* | Session | Terminate control connection |
| `NOOP` | *None* | Session | Keepalive / No operation |
| `SYST` | *None* | Information | Return server operating system type (`UNIX Type: L8`) |
| `FEAT` | *None* | Information | List server supported features / extensions |
| `HELP` | `[<topic>]` | Information | Return command syntax and descriptions |
| `PWD` | *None* | File System | Print current working directory |
| `CWD` | `<pathname>` | File System | Change current working directory |
| `CDUP` | *None* | File System | Change to parent directory |
| `MKD` | `<pathname>` | File System | Make directory |
| `RMD` | `<pathname>` | File System | Remove directory |
| `DELE` | `<pathname>` | File System | Delete file |
| `RNFR` | `<pathname>` | File System | Rename from (source path) |
| `RNTO` | `<pathname>` | File System | Rename to (destination path) |
| `TYPE` | `<type-code>` | Transfer Parameters | Representation type (`I` = Binary/Image, `A` = ASCII) |
| `MODE` | `<mode-code>` | Transfer Parameters | Transfer mode (`S` = Stream) |
| `STRU` | `<structure-code>`| Transfer Parameters | File structure (`F` = File) |
| `PORT` | `h1,h2,h3,h4,p1,p2` | Channel Setup | Active mode client data listener address |
| `PASV` | *None* | Channel Setup | Request passive mode server data listener |
| `LIST` | `[<pathname>]` | Transfer | Stream detailed Unix `ls -l` directory listing |
| `NLST` | `[<pathname>]` | Transfer | Stream bare list of filenames |
| `RETR` | `<filename>` | Transfer | Retrieve (download) file from server |
| `STOR` | `<filename>` | Transfer | Store (upload) file onto server |
| `APPE` | `<filename>` | Transfer | Append uploaded bytes to existing file |
| `SIZE` | `<filename>` | Transfer Parameters | Return file size in bytes |
| `REST` | `<marker>` | Transfer | Restart transfer from byte offset |

---

## 4. Modular Directory & Code Architecture

```
ftp-work/
├── FTP_IMPLEMENTATION_SPEC.md        # This specification document
├── grp-project-blueprint.md           # Original lab blueprint
├── common/
│   ├── __init__.py
│   ├── rfc959.py                     # RFC 959 status codes, constants, templates
│   ├── protocol_parser.py            # NVT/ASCII parser, PORT/PASV address encoders
│   └── logger.py                     # Live NVT/ASCII packet visualizer for console
├── server/
│   ├── __init__.py
│   ├── ftp_server.py                 # Multi-client TCP listening daemon
│   ├── session.py                    # Session state machine & command handler
│   ├── data_channel.py               # Active/Passive data connection manager
│   ├── vfs.py                        # Virtual File System with path traversal guards
│   └── auth.py                       # User credentials store & permission manager
├── client/
│   ├── __init__.py
│   ├── ftp_client.py                 # Core client protocol engine (raw sockets)
│   ├── cli.py                        # Interactive shell with progress bar & prompt
│   └── integrity.py                  # SHA-256 hash calculator & verifier
├── storage/
│   ├── server_root/                  # Isolated server filesystem root
│   └── client_workspace/             # Client download/upload workspace
└── tests/
    ├── __init__.py
    ├── generate_assets.py            # Generates test files (text, images, binary)
    ├── test_active_mode.py           # Automated test for Active Mode
    ├── test_passive_mode.py          # Automated test for Passive Mode
    └── test_concurrency.py           # Multi-threaded concurrent client test
```

---

## 5. Security & Virtual File System (VFS)

To ensure system safety, the server operates inside a **Virtual File System (VFS)**:
* **Chroot Jail Simulation**: The server designates `storage/server_root` as virtual `/`.
* **Path Traversal Protection**: Any path parameter containing malicious vectors (such as `../../../../etc/passwd` or `//hidden_file`) is canonicalized via `os.path.realpath()`. If the resolved real path does not start with the absolute path of `server_root`, the request is immediately rejected with `550 Access denied: Path outside server root`.
* **Safe Permissions**: Distinct read-only vs read-write permissions can be configured per user in `auth.py`.

---

## 6. Live NVT/ASCII Packet Inspector (Lab Requirement)

The lab blueprint specifically requests:
> *"show NVT/ASCII control connection contents if possible"*

Our system includes a dedicated visual packet logger that prints every raw wire-level exchange to the console with timestamped direction indicators:

```
[2026-11-13 21:10:00.123] [CTRL:RECV] <-- 'USER anonymous\r\n'
[2026-11-13 21:10:00.124] [CTRL:SEND] --> '331 Anonymous access allowed, send identity as password.\r\n'
[2026-11-13 21:10:00.130] [CTRL:RECV] <-- 'PASS guest@\r\n'
[2026-11-13 21:10:00.131] [CTRL:SEND] --> '230 User logged in, proceed.\r\n'
[2026-11-13 21:10:00.140] [CTRL:RECV] <-- 'PASV\r\n'
[2026-11-13 21:10:00.141] [CTRL:SEND] --> '227 Entering Passive Mode (127,0,0,1,195,84)\r\n'
[2026-11-13 21:10:00.145] [DATA:ESTB] <== Data Channel Connected [127.0.0.1:50004]
[2026-11-13 21:10:00.146] [CTRL:RECV] <-- 'RETR sample.bin\r\n'
[2026-11-13 21:10:00.147] [CTRL:SEND] --> '150 Opening BINARY mode data connection for sample.bin (10485760 bytes).\r\n'
[2026-11-13 21:10:00.180] [DATA:STRM] ==> Streamed 10485760 bytes in 160 chunks (65536 B/chunk)
[2026-11-13 21:10:00.181] [DATA:CLSE] <== Data Channel Closed at EOF
[2026-11-13 21:10:00.182] [CTRL:SEND] --> '226 Transfer complete. SHA-256: 3a7f...d891\r\n'
```

---

## 7. Verification & Wireshark Capture Instructions

1. **Wireshark Setup**:
   * Capture interface: `Loopback: lo0` (or `any` on Linux).
   * Display Filter: `ftp || ftp-data`
2. **Observe**:
   * Control channel handshakes on TCP Port `2121`.
   * Cleartext command sequences (`USER`, `PASS`, `PORT`, `PASV`, `RETR`, `STOR`).
   * Dynamic TCP handshake on the negotiated data port (`ftp-data`).
   * Actual payload stream and graceful TCP `FIN` packet upon EOF.
3. **Integrity Check**:
   * Pre-transfer hash computed on source file: `sha256sum source_file`.
   * Post-transfer hash computed on destination file: `sha256sum dest_file`.
   * Match verification proves zero byte loss or corruption across TCP stream.

