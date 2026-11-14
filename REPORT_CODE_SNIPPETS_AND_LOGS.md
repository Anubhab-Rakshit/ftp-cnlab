# Report Code Snippets & Curated Terminal Logs
**Companion Reference Material for the 10–14 Page Lab Report**

---

## 1. Curated Code Snippets (Concise, Limited Comments)

### Listing 1: Session State Machine & Pre-Authentication Dispatching (`server/session.py`)
```python
def dispatch_command(self, raw_line: str):
    cmd, arg = parse_command_line(raw_line)
    if not cmd:
        return

    # Handle commands permitted prior to authentication (RFC 4217 & RFC 959)
    if self.state != self.STATE_AUTHENTICATED:
        if cmd == "AUTH":
            self.handle_AUTH(arg)
        elif cmd in ("PBSZ", "PROT"):
            self.handle_PBSZ(arg) if cmd == "PBSZ" else self.handle_PROT(arg)
        elif cmd == CMD_USER:
            self.handle_USER(arg)
        elif cmd == CMD_PASS:
            self.handle_PASS(arg)
        elif cmd == CMD_QUIT:
            self.handle_QUIT(arg)
        elif cmd == CMD_NOOP:
            self.reply(R_200_COMMAND_OK, "NOOP okay.")
        else:
            self.reply(R_530_NOT_LOGGED_IN, "Please log in with USER and PASS.")
        return

    # Authenticated command dispatch table
    handlers = {
        CMD_PWD: self.handle_PWD,
        CMD_CWD: self.handle_CWD,
        CMD_CDUP: self.handle_CDUP,
        CMD_PORT: self.handle_PORT,
        CMD_PASV: self.handle_PASV,
        CMD_EPSV: self.handle_EPSV,
        CMD_LIST: self.handle_LIST,
        CMD_RETR: self.handle_RETR,
        CMD_STOR: self.handle_STOR,
        CMD_SIZE: self.handle_SIZE,
        CMD_REST: self.handle_REST,
        CMD_QUIT: self.handle_QUIT,
    }
    handler = handlers.get(cmd)
    if handler:
        handler(arg)
    else:
        self.reply(R_502_COMMAND_NOT_IMPLEMENTED, f"Command '{cmd}' not implemented.")
```

### Listing 2: Active & Passive Data Channel Establishment (`server/data_channel.py`)
```python
def open_connection(self, prot: str = "C", ssl_context = None) -> socket.socket:
    if self.mode == "ACTIVE":
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.settimeout(30.0)
        conn.connect((self.active_host, self.active_port))
    elif self.mode == "PASSIVE":
        conn, addr = self.pasv_listener.accept()
        conn.settimeout(30.0)
        self.pasv_listener.close()
        self.pasv_listener = None
    else:
        raise RuntimeError("Data channel mode not configured.")

    # Wrap data channel socket if RFC 4217 PROT P (Private/TLS) is negotiated
    if prot == "P" and ssl_context:
        conn = ssl_context.wrap_socket(conn, server_side=True)
    return conn
```

### Listing 3: Rate-Limited Chunk Streaming & Resumption (`server/session.py`)
```python
def handle_RETR(self, arg: str):
    real_path, clean_vpath = self.vfs.resolve(arg)
    file_size = os.path.getsize(real_path)
    data_sock = self.data_mgr.open_connection(prot=self.data_prot, ssl_context=self.ssl_context)
    self.reply(R_150_FILE_STATUS_OK_OPEN_DATA, f"Opening BINARY mode for {clean_vpath} ({file_size} B).")

    hasher = hashlib.sha256()
    total_sent = 0
    RATE_LIMIT_BYTES_PER_SEC = 1048576  # 1 MB/s Token Bucket target

    with open(real_path, "rb") as f:
        if self.rest_offset > 0:
            f.seek(self.rest_offset)
            self.rest_offset = 0

        while True:
            start_time = time.time()
            chunk = f.read(BUFFER_SIZE)
            if not chunk:
                break
            data_sock.sendall(chunk)
            hasher.update(chunk)
            total_sent += len(chunk)

            # Bandwidth throttling calculation
            elapsed_time = time.time() - start_time
            expected_time = len(chunk) / RATE_LIMIT_BYTES_PER_SEC
            if expected_time > elapsed_time:
                time.sleep(expected_time - elapsed_time)

    data_sock.close()
    self.reply(R_226_CLOSING_DATA_CONN_SUCCESS, f"Transfer complete. SHA-256: {hasher.hexdigest()}")
```

### Listing 4: Client Transfer Resumption with SHA-256 Pre-Seeding (`client/ftp_client.py`)
```python
def retrieve_file(self, remote_path: str, local_dest: str, resume: bool = False):
    rest_offset = 0
    hasher = hashlib.sha256()

    # Pre-hash existing local bytes to produce correct end-to-end checksum
    if resume and os.path.exists(local_dest):
        rest_offset = os.path.getsize(local_dest)
        if rest_offset > 0:
            self.send_cmd(CMD_REST, str(rest_offset))
            with open(local_dest, "rb") as existing_f:
                while chunk := existing_f.read(BUFFER_SIZE):
                    hasher.update(chunk)

    data_sock = self._setup_and_connect_data()
    self.send_cmd(CMD_RETR, remote_path)
    open_mode = "ab" if (resume and rest_offset > 0) else "wb"

    with open(local_dest, open_mode) as f:
        while chunk := data_sock.recv(BUFFER_SIZE):
            f.write(chunk)
            hasher.update(chunk)

    data_sock.close()
    self._read_reply()
    return os.path.getsize(local_dest), hasher.hexdigest()
```

---

## 2. Curated Terminal Logs (Formatted for Report Boxes)

### Log Box 1: Server Daemon Initialization & FTPS Certificate Loading
```text
$ python3 -m server.ftp_server --port 2121
15:38:53.538 [INFO] SSL Certificate loaded successfully. Ready for FTPS.
15:38:53.539 [SUCCESS] =========================================================
15:38:53.539 [SUCCESS]    RFC 959 Multi-Threaded Pure Socket FTP Server
15:38:53.539 [SUCCESS]    Listening on: 0.0.0.0:2121
15:38:53.539 [SUCCESS]    Root Sandbox: .../storage/server_root
15:38:53.539 [SUCCESS]    Active Mode (PORT) & Passive Mode (PASV) Supported
15:38:53.539 [SUCCESS]    NVT/ASCII Control Inspector Enabled
15:38:53.539 [SUCCESS] =========================================================
```

### Log Box 2: Client Shell, Authentication & Resumed Download (`reget`)
```text
$ python3 -m client.cli --host 127.0.0.1 --port 2121
15:39:53.688 [INFO] Connecting to FTP control server at 127.0.0.1:2121...
15:39:53.689 [CTRL:RECV] <-- '220 RFC 959 Python FTP Server Ready.\r\n'
15:39:53.689 [SUCCESS] Connected: RFC 959 Python FTP Server Ready.

ftp> user anubhab password123
15:40:06.987 [CTRL:SEND] --> 'USER anubhab\r\n'
15:40:06.988 [CTRL:RECV] <-- '331 Password required for anubhab.\r\n'
15:40:06.988 [CTRL:SEND] --> 'PASS password123\r\n'
15:40:06.988 [CTRL:RECV] <-- '230 User anubhab logged in successfully.\r\n'
15:40:06.988 [SUCCESS] Successfully authenticated as 'anubhab'.

ftp> reget archive_5mb.bin
Resuming download: 'archive_5mb.bin' -> '.../storage/client_workspace/archive_5mb.bin' (Mode: PASSIVE)...
15:40:15.018 [CTRL:SEND] --> 'SIZE archive_5mb.bin\r\n'
15:40:15.019 [CTRL:RECV] <-- '213 5242880\r\n'
15:40:15.019 [CTRL:SEND] --> 'PASV\r\n'
15:40:15.020 [CTRL:RECV] <-- '227 Entering Passive Mode (127,0,0,1,251,85)\r\n'
15:40:15.020 [DATA:PASV] Connecting to server data endpoint 127.0.0.1:64341
15:40:15.020 [CTRL:SEND] --> 'RETR archive_5mb.bin\r\n'
15:40:15.021 [CTRL:RECV] <-- '150 Opening BINARY mode data connection for /archive_5mb.bin (5242880 bytes).\r\n'
  [========================================] 100.0% (5242880/5242880 B)
15:40:20.352 [CTRL:RECV] <-- '226 Transfer complete. 5242880 bytes sent. SHA-256: 82fb1b7e193fb89722d13de35f2dab9b48e34b4e5ce703e08bca103b415d4800\r\n'
15:40:20.352 [SUCCESS] Downloaded 5242880 bytes -> '.../archive_5mb.bin' [SHA-256: 82fb1b7e193f...]

Resumed 5242880 bytes in 5.334s (959.9 KB/s)
Final Local SHA-256: 82fb1b7e193fb89722d13de35f2dab9b48e34b4e5ce703e08bca103b415d4800

ftp> quit
15:41:05.901 [CTRL:SEND] --> 'QUIT\r\n'
15:41:05.902 [CTRL:RECV] <-- '221 Goodbye.\r\n'
```

### Log Box 3: Explicit FTPS (TLS) Wire Trace & Interoperability Verification
```text
# Command executed from external terminal:
$ curl --ssl-reqd -k -s ftp://anubhab:password123@127.0.0.1:2121/welcome.txt

# Server Control & Data Channel Wire Trace:
15:40:47.690 [INFO] Accepted control connection from 127.0.0.1:64351
15:40:47.690 [CTRL:SEND] [127.0.0.1:64351] --> '220 RFC 959 Python FTP Server Ready.\r\n'
15:40:47.690 [CTRL:RECV] [127.0.0.1:64351] <-- 'AUTH SSL\r\n'
15:40:47.690 [CTRL:SEND] [127.0.0.1:64351] --> '234 AUTH TLS OK. Initiating TLS negotiation.\r\n'
15:40:47.726 [SUCCESS] Control channel upgraded to TLS for 127.0.0.1:64351
15:40:47.726 [CTRL:RECV] [127.0.0.1:64351] <-- 'USER anubhab\r\n'   (ENCRYPTED)
15:40:47.726 [CTRL:SEND] [127.0.0.1:64351] --> '331 Password required for anubhab.\r\n'
15:40:47.726 [CTRL:RECV] [127.0.0.1:64351] <-- 'PASS password123\r\n'   (ENCRYPTED)
15:40:47.726 [CTRL:SEND] [127.0.0.1:64351] --> '230 User anubhab logged in successfully.\r\n'
15:40:47.726 [CTRL:RECV] [127.0.0.1:64351] <-- 'PBSZ 0\r\n'
15:40:47.726 [CTRL:SEND] [127.0.0.1:64351] --> '200 PBSZ set to 0.\r\n'
15:40:47.726 [CTRL:RECV] [127.0.0.1:64351] <-- 'PROT P\r\n'
15:40:47.726 [CTRL:SEND] [127.0.0.1:64351] --> '200 Data channel protection set to Private (TLS).\r\n'
15:40:47.727 [CTRL:RECV] [127.0.0.1:64351] <-- 'EPSV\r\n'
15:40:47.727 [DATA:EPSV] [127.0.0.1:64351] Extended passive mode listener active on port 64352
15:40:47.727 [CTRL:SEND] [127.0.0.1:64351] --> '229 Entering Extended Passive Mode (|||64352|)\r\n'
15:40:47.730 [DATA:ESTB] [127.0.0.1:64351] Data channel connected for RETR /welcome.txt
15:40:47.730 [CTRL:SEND] [127.0.0.1:64351] --> '150 Opening BINARY mode data connection for /welcome.txt (241 bytes).\r\n'
15:40:47.731 [DATA:STRM] [127.0.0.1:64351] Streamed 241 bytes in 1 chunks (65536 B/chunk).
15:40:47.731 [DATA:CLSE] [127.0.0.1:64351] Data channel closed at EOF.
15:40:47.731 [CTRL:SEND] [127.0.0.1:64351] --> '226 Transfer complete. 241 bytes sent. SHA-256: 234b0c6b3a8fbbfdf912f63a754da521e30b565a2c615c6912170466ba5c8337\r\n'
15:40:47.731 [CTRL:RECV] [127.0.0.1:64351] <-- 'QUIT\r\n'
15:40:47.731 [CTRL:SEND] [127.0.0.1:64351] --> '221 Goodbye.\r\n'

# Client Curl Output:
Welcome to the RFC 959 FTP Server!
Computer Networks Lab Project
Features:
- Dual channel architecture (Control & Data)
- Active (PORT) & Passive (PASV) modes
- Real-time chunked byte streaming
- SHA-256 cryptographically verified integrity
```
