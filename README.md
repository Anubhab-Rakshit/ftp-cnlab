# Pure Socket RFC 959 FTP Client-Server System  
**Computer Networks Laboratory Project**  
   
## 1. System Overview  
A complete, standards-compliant **File Transfer Protocol (FTP)** client-server implementation built from scratch using raw Python TCP sockets (socket.socket(AF_INET, SOCK_STREAM)).  
### Core Highlights  
- **Zero 3rd-Party Abstractions**: Engineered purely with Python's standard library (socket, threading, hashlib, os). Does **NOT** use ftplib or pyftpdlib.  
- **RFC 959 Dual-Channel Architecture**:  
  - **Control Channel**: Persistent TCP socket (default port 2121) implementing Telnet NVT/ASCII framing (\r\n).  
  - **Data Channel**: Ephemeral TCP sockets dynamically created for data streaming and closed immediately at EOF.  
- **Dual Operating Modes**:  
  - **Active Mode (PORT)**: Client acts as listener, server initiates active connection.  
  - **Passive Mode (PASV / EPSV)**: Server binds ephemeral listener, client initiates connection (firewall/NAT friendly).  
- **Dual-Pane Terminal TUI**: A built-in, interactive curses-based graphical terminal interface for split-pane local and remote filesystem navigation.  
- **Transfer Resumption & Recovery**: Supports appending and resuming interrupted transfers using the REST and APPE commands.  
- **Explicit TLS/SSL Encryption (FTPS)**: Secures both control and data channels against packet sniffing using ssl.wrap_socket (AUTH TLS, PROT P).  
- **Storage Quotas & Rate Limiting**: Enforces multi-tenant storage limits and chunk-based bandwidth throttling to simulate real-world network conditions.  
- **Real-Time Chunked Streaming**: Files are transferred in 64 KB buffers directly between socket and disk streams, handling files of any size (tested up to multi-megabyte binary archives and images).  
- **Live NVT/ASCII Packet Inspector**: Real-time console logging showing exact wire-level commands (\[CTRL:RECV\], \[CTRL:SEND\], \[DATA:ESTB\], \[DATA:STRM\], \[DATA:CLSE\]).  
- **Cryptographic Integrity (SHA-256)**: Automated pre- and post-transfer cryptographic checksums ensure byte-for-byte fidelity without data corruption.  
- **Virtual File System (VFS)**: Chroot-jailed root directory (storage/server_root) with path-traversal attack defenses.  
- **100% Interoperability**: Fully compatible with custom client, CLI curl, standard system ftp, and FileZilla.  
## Recent Feature Updates  
The FTP Client-Server System has been enhanced with key capabilities for improved security, interface usability, and data control:  
- **Dual-Pane Terminal User Interface (TUI)**: Provides an interactive split-pane interface for browsing local and remote directories simultaneously.  
- **Explicit TLS/SSL Encryption (FTPS)**: Secures control and data connections using AUTH TLS and PROT P commands.  
- **Storage Quotas & Bandwidth Throttling**: Configurable per-user storage caps and chunk-level transfer rate limits for effective resource management.  
- **Transfer Resumption**: Resume interrupted file downloads or append data seamlessly using the REST and APPE commands.  
   
## 2. Architecture & Communication Flow  
                      +---------------------------------------+  
                      |         FTP Client (Python)           |  
                      |  - Interactive Shell & Curses TUI     |  
                      |  - TLS/SSL Encryption Wrapper         |  
                      |  - Terminal Progress Bar (Transfer)   |  
                      |  - Active (PORT) & Passive (PASV)     |  
                      +-------+-----------------------+-------+  
                              |                       |  
            NVT/ASCII Control | Port 2121             | Data Connection (PORT/PASV)  
            Commands & Status | (Persistent TCP)      | (Ephemeral TCP, Per-Transfer)  
                              v                       v  
                      +-------+-----------------------+-------+  
                      |         FTP Server (Python)           |  
                      |  - Multi-threaded Session Handler     |  
                      |  - Dual Channel Coordinator           |  
                      |  - Virtual FS & Path Traversal Guard  |  
                      |  - Real Chunked Stream Engine         |  
                      +---------------------------------------+  
   
## 3. Directory Layout  
   
ftp-work/  
├── server.crt                         # TLS/SSL certificate  
├── server.key                         # TLS/SSL private key  
├── README.md                          # Complete lab report & usage guide  
├── FTP_IMPLEMENTATION_SPEC.md         # Detailed technical specification  
├── grp-project-blueprint.md           # Original lab blueprint  
├── common/  
│   ├── \_\_init\_\_.py  
│   ├── rfc959.py                      # RFC 959/2428 status codes, command constants  
│   ├── protocol_parser.py             # NVT/ASCII parser & PORT/PASV address encoders  
│   └── logger.py                      # Real-time console packet visualizer  
├── server/  
│   ├── \_\_init\_\_.py  
│   ├── ftp_server.py                  # Multi-threaded server daemon entrypoint  
│   ├── session.py                     # RFC 959 state machine & command dispatcher  
│   ├── data_channel.py                # Active (PORT) and Passive (PASV) data manager  
│   ├── vfs.py                         # Virtual File System with path-traversal guards  
│   └── auth.py                        # User auth, permissions, and Storage Quotas  
├── client/  
│   ├── \_\_init\_\_.py  
│   ├── ftp_client.py                  # Core client protocol engine (raw sockets)  
│   ├── cli.py                         # Interactive FTP shell with progress bar  
│   ├── tui.py                         # Dual-pane Curses Terminal User Interface  
│   └── integrity.py                   # SHA-256 calculation & validation utility  
├── storage/  
│   ├── server_root/                   # Server sandboxed storage  
│   └── client_workspace/              # Client download/upload workspace  
└── tests/  
    ├── generate_assets.py             # Generates test assets (text, images, binary)  
    ├── test_passive_mode.py           # Automated test for Passive Mode (PASV)  
    ├── test_active_mode.py            # Automated test for Active Mode (PORT)  
    ├── test_concurrency.py            # Stress test with 6 simultaneous parallel clients  
    └── test_all.py                    # Master test runner  
   
## 4. Quick Start Guide  
### Step 1: Start the FTP Server  
In Terminal 1:  
   
python3 -m server.ftp_server --port 2121  
   
*The server will bind to 0.0.0.0:2121 and display live NVT/ASCII wire packets.*  
### Step 2: Launch the Dual-Pane TUI (Recommended)  
For a rich graphical terminal experience with split-pane navigation, launch the TUI: In Terminal 2:  
   
python3 -m client.tui  
   
*Press c to connect, TAB to switch panes, UP/DOWN to navigate, and q to quit.*  
### Step 3: Launch the Interactive CLI  
If you prefer a standard command-line interface instead of the TUI:  
   
python3 -m client.cli --host 127.0.0.1 --port 2121  
   
Once inside the ftp>  shell:  
   
ftp> user admin password123      # Authenticate  
ftp> pwd                         # Print working directory  
ftp> ls                          # List files (streamed over data channel)  
ftp> mode passive                # Switch to Passive mode (or 'mode active')  
ftp> get archive_5mb.bin         # Download file with live progress bar  
ftp> reget archive_5mb.bin       # Resume an interrupted download  
ftp> rate 1024                   # Throttle bandwidth to 1 MB/s  
ftp> sha256 downloaded_file.bin  # Verify SHA-256 checksum  
ftp> put my_photo.png            # Upload a file  
ftp> mkdir lab_folder            # Create directory  
ftp> cd lab_folder               # Navigate  
ftp> wire off                    # Toggle NVT/ASCII wire trace (on/off)  
ftp> quit                        # Disconnect and exit  
### How to Run the Project  
Follow these steps to launch the server and start working with the system:  
1. **Start Server Daemon**: Launch python3 -m server.ftp_server --port 2121 in your terminal.  
2. **Run Interactive TUI**: Execute python3 -m client.tui to launch the interactive split-pane interface.  
3. **Use Command Line Interface**: Execute python3 -m client.cli --host 127.0.0.1 --port 2121 for direct shell access.  
   
## 5. Verification & Test Suite  
Run the comprehensive master test runner:  
   
python3 tests/test_all.py  
   
This runs:  
   
4. **Passive Mode Suite**: Verifies authentication, directory navigation, 5MB binary download, 1MB upload, directory manipulation, path-traversal containment, and SHA-256 match.  
5. **Active Mode Suite**: Verifies client listening socket setup, PORT h1,h2,h3,h4,p1,p2 negotiation, server connect-back, 1MB streaming download, 1MB upload, and SHA-256 match.  
6. **Concurrency Stress Test**: Spawns **6 simultaneous client threads** concurrently transferring binary files in both Active and Passive modes to stress-test the multi-threaded server.  
   
## 6. Testing with Standard Tools (Interoperability)  
### Testing with curl  
\# Download a file via curl  
curl ftp://anonymous:guest@127.0.0.1:2121/welcome.txt  
   
\# Upload a file via curl  
curl -T my_local_file.txt ftp://admin:password123@127.0.0.1:2121/  
### Testing with OS Native CLI ftp  
ftp -p 127.0.0.1 2121  
   
## 7. Wireshark Capture & Lab Demonstration Guide  
### How to Capture Packets  
7. Open Wireshark and select the **Loopback interface (lo0 on macOS / any on Linux)**.  
8. Set Display Filter:  
   
ftp || ftp-data  
   
9. Start the FTP server and run a file transfer via the client or tests.  
### What to Observe & Explain in Lab  
10. **Control Connection Handshake (TCP 3-Way Handshake)**:  
  - Client SYN \$\to\$ Server Port 2121  
  - Server SYN, ACK \$\to\$ Client  
  - Client ACK \$\to\$ Server  
11. **Telnet NVT/ASCII Framing**:  
  - Inspect the FTP protocol packets: clear text commands terminated by \r\n (USER, PASS, PORT, PASV, RETR, STOR).  
  - 3-digit reply codes (220, 331, 230, 150, 226).  
12. **Data Channel Negotiation**:  
  - **Active (PORT)**: Observe client transmitting PORT 127,0,0,1,p1,p2, followed by server initiating a new TCP handshake to (p1\*256 + p2).  
  - **Passive (PASV)**: Observe server returning 227 Entering Passive Mode (127,0,0,1,p1,p2), followed by client initiating a new TCP handshake to that ephemeral port.  
13. **Data Stream & EOF Teardown**:  
  - Inspect the FTP-DATA packets streaming the payload.  
  - Observe the sender sending a TCP FIN packet upon EOF, cleanly terminating the ephemeral data channel while the control channel remains persistent!  
-    
