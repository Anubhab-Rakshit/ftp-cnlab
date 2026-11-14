# Master Prompt for Claude: Computer Networks Lab Report (10–14 Pages)

---

## Instructions for You (Anubhab)
1. In Claude, start a new chat.
2. **Attach the following 5 files** to Claude:
   - `Assignment4_CDMA_Walsh_Codes_Report.pdf` (Reference style document)
   - `report_assets/fig1_ftp_architecture.png` (Generated Figure 1)
   - `report_assets/fig2_active_passive_handshake.png` (Generated Figure 2)
   - `report_assets/fig3_chunked_streaming_resume.png` (Generated Figure 3)
   - `report_assets/fig4_ftps_encryption_flow.png` (Generated Figure 4)
3. Copy and paste the **Master Prompt** below into Claude.

---

```markdown
You are an expert Academic Systems & Computer Networks Researcher. I have provided:
1. A reference sample lab report from our university ("Assignment4_CDMA_Walsh_Codes_Report.pdf").
2. Four high-resolution architectural diagram images ("fig1_ftp_architecture.png", "fig2_active_passive_handshake.png", "fig3_chunked_streaming_resume.png", "fig4_ftps_encryption_flow.png").
3. Curated terminal logs and clean code snippets from our pure Python socket implementation of RFC 959 / RFC 4217 FTP.

Generate a complete, publication-grade LaTeX lab report (target: 10 to 14 pages) matching the visual styling, typographic elegance (Crimson / Palatino font, clean section titles, colored headers, tight listings, professional math formulas, and structured tables) of the provided reference PDF.

============================================================
METADATA & HEADER PARTICULARS
============================================================
Institution: Jadavpur University
Department: Department of Computer Science & Engineering
Location: Kolkata — 700032, West Bengal, India
Course: Computer Networks Laboratory
Project Title: RFC 959 File Transfer Protocol (FTP) Implementation with Dual-Channel Socket Architecture, Bandwidth Throttling, Transfer Resumption, and Explicit FTPS (RFC 4217) Security
Subtitle: A Multi-Threaded Application/Transport Layer Client-Server System with Active/Passive Data Channels, Chroot Sandboxing, and Cryptographic SHA-256 Verification
Class: BCSE-III (Semester 5)
Group Members / Roll Numbers:
- 002410501017
- 002410501029
- 302510501001
- 302510501002

============================================================
REPORT OUTLINE (10 TO 14 PAGES)
============================================================

1. Introduction & Learning Objectives
   1.1 Context: The architectural role of FTP as an out-of-band application-layer signaling protocol (RFC 959); contrast with monolithic HTTP/1.1; transport-layer interactions.
   1.2 Learning Objectives: Pure BSD socket programming (`socket.socket`), persistent vs ephemeral socket lifecycle, active vs passive connection handshakes, real-time chunked byte streaming, cryptographic verification, and explicit TLS security (RFC 4217).

2. System Architecture
   2.1 Dual-Channel Topology: Decoupling of control signaling (TCP Port 2121) and bulk data transfer (ephemeral TCP ports). Reference and embed `fig1_ftp_architecture.png`.
   2.2 Server Daemon Architecture: Multi-threaded connection handler (`FTPServer`), per-client state machine (`FTPSession`), dynamic ephemeral listener management (`DataChannelManager`).
   2.3 Client Subsystems: Dual-engine interactive shell (`cli.py`), terminal cursor dashboard (`client/tui.py`), and raw protocol driver (`ftp_client.py`).
   2.4 Virtual File System (VFS) & Chroot Sandboxing: Path canonicalization via `os.path.realpath`, preventing path traversal attacks (`../../`). Table of project module responsibilities.

3. Mathematical & Protocol Foundations
   3.1 NVT/ASCII Command-Reply Wire Framing: Telnet conventions, line termination (`\r\n`), 3-digit reply code classes (1xx, 2xx, 3xx, 4xx, 5xx).
   3.2 Active Mode (PORT) Port Encoding:
       Address translation formula: P = (p1 * 256) + p2.
       Client acts as listener; server executes active `connect()`.
   3.3 Passive Mode (PASV / EPSV) Handshake:
       Server ephemeral port allocation; client executes active `connect()`. Reference and embed `fig2_active_passive_handshake.png`.
   3.4 Chunked Streaming Dynamics & Token Bucket Rate Limiting:
       Mathematical model of chunk streaming (64 KB buffers).
       Bandwidth throttling: Delta t = (ChunkSize / RateLimit) - ElapsedTime.
   3.5 Cryptographic Verification:
       SHA-256 hash computation over streaming byte arrays to prove 0% bit corruption across TCP segments.
   3.6 Transfer Resumption Mechanics:
       Byte offset seeking (`f.seek(offset)`) via RFC 959 `REST` command. Reference and embed `fig3_chunked_streaming_resume.png`.
   3.7 Explicit FTPS Security (RFC 4217):
       Pre-authentication TLS upgrade (`AUTH TLS`/`AUTH SSL`), `PBSZ 0`, and `PROT P` private data channel wrapping. Reference and embed `fig4_ftps_encryption_flow.png`.

4. Implementation Details (Code Listings with Minimal Comments)
   Include 4 focused, elegant LaTeX code listings (`lstlisting` environment). Keep code comments to an absolute minimum (at most 1-line per function):
   - Listing 1: Session State Machine & Command Dispatching (`server/session.py`)
   - Listing 2: Active & Passive Data Channel Coordinator (`server/data_channel.py`)
   - Listing 3: Rate-Limited Chunk Streaming & REST Offset Resume (`client/ftp_client.py` & `server/session.py`)
   - Listing 4: Explicit FTPS TLS Socket Upgrade & PROT P Protection (`server/session.py`)

5. Experimental Methodology & Results
   5.1 Verification Test Matrix: Table showing test cases (Passive Mode RETR/STOR, Active Mode RETR/STOR, 6-client Concurrency Stress Test, 5MB Archive Download with Resumption, FTPS TLS encryption).
   5.2 Concurrency Stress Test: 6 simultaneous threads performing uploads and downloads without socket collisions; timing and throughput metrics.
   5.3 Bit-Level Integrity Validation: SHA-256 hash comparison table between server originals and downloaded client replicas.
   5.4 Transfer Resumption Benchmark: Downloading 1 MB of 5 MB archive, resuming with `reget`, verifying byte completion and final SHA-256 match.

6. Wire Traces & Terminal Verifications
   Format these real terminal logs into elegant shaded verbatim boxes:
   - Box 1: Server Daemon Startup with FTPS TLS Certificate Loading.
   - Box 2: Client Interactive Shell, Authentication for user `anubhab`, and `reget archive_5mb.bin` at 959.9 KB/s with Progress Bar and SHA-256 validation.
   - Box 3: Explicit FTPS Curl Verification (`curl --ssl-reqd -k -s ftp://anubhab:password123@127.0.0.1:2121/welcome.txt`) showing `AUTH SSL`, `234`, `PBSZ 0`, `PROT P`, and encrypted payload transfer.

7. Engineering Challenges & Technical Solutions
   - Challenge 1: Ephemeral Port Collision & Socket Lifecycle Management.
   - Challenge 2: Client-side NAT/Firewall blocking in Active Mode vs Passive Mode solution.
   - Challenge 3: Path Traversal Vulnerabilities and Canonical VFS Sandboxing.
   - Challenge 4: Pre-Authentication TLS State Synchronization (handling `AUTH TLS` prior to `USER`/`PASS`).

8. Conclusion & Future Roadmap
   - Summary of achievements.
   - Limitations & Future Work: IPv6 Dual-Stack (`EPRT`/`EPSV`), Multi-tenant user disk quotas, TLS session resumption (`SSL_SESSION`).
   - Glossary of Acronyms (FTP, FTPS, RFC, NVT, VFS, PASV, PORT, TLS, TCP, SHA, MTU, MSS).
   - Declaration of Generative AI Usage.

============================================================
STYLE GUIDELINES
============================================================
- Write clean, fully compilable LaTeX code.
- Use `geometry` (margins 1in), `microtype`, `booktabs` for tables, `listings` for code, `xcolor` for syntax highlighting, `hyperref` for clickable cross-references, `fancyhdr` for headers/footers.
- Embed `\includegraphics[width=\textwidth]{fig1_ftp_architecture.png}`, etc. with detailed captions.
- Ensure thorough academic explanations across all sections so the paper naturally spans 10–14 pages.
```
