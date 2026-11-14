"""
Generates publication-quality figures for the Computer Networks Lab FTP Report.
Outputs high-resolution 300 DPI diagrams in report_assets/.
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches

os.environ["MPLCONFIGDIR"] = "/tmp/matplotlib_cache"
os.makedirs("report_assets", exist_ok=True)

# -------------------------------------------------------------
# FIGURE 1: Dual-Channel System Architecture
# -------------------------------------------------------------
def generate_fig1_architecture():
    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=300)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")

    # Client Box
    client_box = patches.FancyBboxPatch(
        (0.6, 1.2), 2.5, 3.8, boxstyle="round,pad=0.2",
        fc="#EBF3FB", ec="#2B6CB0", lw=2
    )
    ax.add_patch(client_box)
    ax.text(1.85, 4.6, "FTP CLIENT (Python)", ha="center", va="center", fontsize=11, fontweight="bold", color="#1A365D")
    ax.text(1.85, 3.8, "• Interactive CLI & TUI\n• Active Port Listener\n• Passive Mode Connector\n• Chunk Receiver/Sender\n• SHA-256 Validator",
            ha="center", va="center", fontsize=8.5, color="#2D3748")

    # Server Box
    server_box = patches.FancyBboxPatch(
        (6.9, 1.2), 2.5, 3.8, boxstyle="round,pad=0.2",
        fc="#F0FFF4", ec="#276749", lw=2
    )
    ax.add_patch(server_box)
    ax.text(8.15, 4.6, "FTP SERVER (Python)", ha="center", va="center", fontsize=11, fontweight="bold", color="#1C4532")
    ax.text(8.15, 3.8, "• Multi-Threaded Daemon\n• RFC 959 State Engine\n• VFS Sandbox Guard\n• Active/Passive Manager\n• Rate Limiter & FTPS",
            ha="center", va="center", fontsize=8.5, color="#2D3748")

    # Control Channel Arrow (Top)
    ax.annotate("", xy=(6.8, 3.6), xytext=(3.2, 3.6),
                arrowprops=dict(arrowstyle="<->", color="#DD6B20", lw=2.5))
    ax.text(5.0, 4.05, "Control Channel (Port 2121)", ha="center", va="bottom", fontsize=10, fontweight="bold", color="#C05621")
    ax.text(5.0, 3.75, "Persistent TCP | Telnet NVT/ASCII Framing (\\r\\n)\n[USER, PASS, PWD, LIST, RETR, REST, AUTH TLS]",
            ha="center", va="top", fontsize=8, color="#744210")

    # Data Channel Arrow (Bottom)
    ax.annotate("", xy=(6.8, 2.0), xytext=(3.2, 2.0),
                arrowprops=dict(arrowstyle="<->", color="#3182CE", lw=2.5, ls="--"))
    ax.text(5.0, 2.45, "Data Channel (Dynamic Ephemeral Port)", ha="center", va="bottom", fontsize=10, fontweight="bold", color="#2B6CB0")
    ax.text(5.0, 2.15, "Ephemeral TCP | Active (PORT) or Passive (PASV)\nRaw Chunked Byte Stream | Closed at EOF",
            ha="center", va="top", fontsize=8, color="#2C5282")

    # VFS Storage Box
    vfs_box = patches.FancyBboxPatch(
        (7.2, 0.3), 1.9, 0.7, boxstyle="round,pad=0.1",
        fc="#EDF2F7", ec="#718096", lw=1.2, ls=":"
    )
    ax.add_patch(vfs_box)
    ax.text(8.15, 0.65, "VFS Sandbox\n(storage/server_root)", ha="center", va="center", fontsize=7.5, color="#4A5568")

    # Client Workspace Box
    ws_box = patches.FancyBboxPatch(
        (0.9, 0.3), 1.9, 0.7, boxstyle="round,pad=0.1",
        fc="#EDF2F7", ec="#718096", lw=1.2, ls=":"
    )
    ax.add_patch(ws_box)
    ax.text(1.85, 0.65, "Client Workspace\n(storage/client_workspace)", ha="center", va="center", fontsize=7.5, color="#4A5568")

    plt.tight_layout()
    plt.savefig("report_assets/fig1_ftp_architecture.png", dpi=300)
    plt.close()
    print("Created: report_assets/fig1_ftp_architecture.png")


# -------------------------------------------------------------
# FIGURE 2: Active vs. Passive Mode Sequence Diagram
# -------------------------------------------------------------
def generate_fig2_active_passive():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5.5), dpi=300)

    # 1. Active Mode (Left)
    ax1.set_xlim(0, 5)
    ax1.set_ylim(0, 8)
    ax1.axis("off")
    ax1.set_title("Active Mode (PORT)", fontsize=11, fontweight="bold", pad=12, color="#2C5282")

    ax1.plot([1.2, 1.2], [0.5, 7.2], color="#A0AEC0", lw=1.5, ls="--")
    ax1.plot([3.8, 3.8], [0.5, 7.2], color="#A0AEC0", lw=1.5, ls="--")
    ax1.text(1.2, 7.5, "Client", ha="center", va="center", fontweight="bold", bbox=dict(boxstyle="round", fc="#EBF8FF", ec="#3182CE"))
    ax1.text(3.8, 7.5, "Server", ha="center", va="center", fontweight="bold", bbox=dict(boxstyle="round", fc="#F0FFF4", ec="#38A169"))

    steps_act = [
        (6.7, "Client binds ephemeral Port P", "note_left"),
        (6.1, "PORT h1,h2,h3,h4,p1,p2 -->", "msg_right"),
        (5.5, "<-- 200 PORT command OK", "msg_left"),
        (4.9, "RETR file.bin -->", "msg_right"),
        (4.3, "<-- 150 Opening Data Conn", "msg_left"),
        (3.6, "<== [Server connects to Client:P] ==", "data_left"),
        (2.8, "<== Binary Chunks Streamed ==", "data_left"),
        (2.1, "<== Server Closes Socket (EOF) ==", "data_left"),
        (1.4, "<-- 226 Transfer Complete", "msg_left"),
    ]
    for y, text, stype in steps_act:
        if stype == "note_left":
            ax1.text(1.2, y, text, ha="center", va="center", fontsize=7.5, fontstyle="italic", color="#718096")
        elif stype == "msg_right":
            ax1.annotate("", xy=(3.7, y), xytext=(1.3, y), arrowprops=dict(arrowstyle="->", color="#DD6B20", lw=1.5))
            ax1.text(2.5, y + 0.18, text, ha="center", va="bottom", fontsize=7.5, color="#C05621")
        elif stype == "msg_left":
            ax1.annotate("", xy=(1.3, y), xytext=(3.7, y), arrowprops=dict(arrowstyle="->", color="#38A169", lw=1.5))
            ax1.text(2.5, y + 0.18, text, ha="center", va="bottom", fontsize=7.5, color="#276749")
        elif stype == "data_left":
            ax1.annotate("", xy=(1.3, y), xytext=(3.7, y), arrowprops=dict(arrowstyle="->", color="#3182CE", lw=2, ls="--"))
            ax1.text(2.5, y + 0.18, text, ha="center", va="bottom", fontsize=7.5, fontweight="bold", color="#2B6CB0")

    # 2. Passive Mode (Right)
    ax2.set_xlim(0, 5)
    ax2.set_ylim(0, 8)
    ax2.axis("off")
    ax2.set_title("Passive Mode (PASV)", fontsize=11, fontweight="bold", pad=12, color="#276749")

    ax2.plot([1.2, 1.2], [0.5, 7.2], color="#A0AEC0", lw=1.5, ls="--")
    ax2.plot([3.8, 3.8], [0.5, 7.2], color="#A0AEC0", lw=1.5, ls="--")
    ax2.text(1.2, 7.5, "Client", ha="center", va="center", fontweight="bold", bbox=dict(boxstyle="round", fc="#EBF8FF", ec="#3182CE"))
    ax2.text(3.8, 7.5, "Server", ha="center", va="center", fontweight="bold", bbox=dict(boxstyle="round", fc="#F0FFF4", ec="#38A169"))

    steps_pasv = [
        (6.7, "PASV -->", "msg_right"),
        (6.1, "Server binds ephemeral Port P", "note_right"),
        (5.5, "<-- 227 Entering Passive Mode (...,p1,p2)", "msg_left"),
        (4.7, "== [Client connects to Server:P] ==>", "data_right"),
        (4.0, "RETR file.bin -->", "msg_right"),
        (3.4, "<-- 150 Opening Data Conn", "msg_left"),
        (2.7, "<== Binary Chunks Streamed ==", "data_left"),
        (2.0, "<== Server Closes Socket (EOF) ==", "data_left"),
        (1.3, "<-- 226 Transfer Complete", "msg_left"),
    ]
    for y, text, stype in steps_pasv:
        if stype == "note_right":
            ax2.text(3.8, y, text, ha="center", va="center", fontsize=7.5, fontstyle="italic", color="#718096")
        elif stype == "msg_right":
            ax2.annotate("", xy=(3.7, y), xytext=(1.3, y), arrowprops=dict(arrowstyle="->", color="#DD6B20", lw=1.5))
            ax2.text(2.5, y + 0.18, text, ha="center", va="bottom", fontsize=7.5, color="#C05621")
        elif stype == "msg_left":
            ax2.annotate("", xy=(1.3, y), xytext=(3.7, y), arrowprops=dict(arrowstyle="->", color="#38A169", lw=1.5))
            ax2.text(2.5, y + 0.18, text, ha="center", va="bottom", fontsize=7.5, color="#276749")
        elif stype == "data_right":
            ax2.annotate("", xy=(3.7, y), xytext=(1.3, y), arrowprops=dict(arrowstyle="->", color="#3182CE", lw=2, ls="--"))
            ax2.text(2.5, y + 0.18, text, ha="center", va="bottom", fontsize=7.5, fontweight="bold", color="#2B6CB0")
        elif stype == "data_left":
            ax2.annotate("", xy=(1.3, y), xytext=(3.7, y), arrowprops=dict(arrowstyle="->", color="#3182CE", lw=2, ls="--"))
            ax2.text(2.5, y + 0.18, text, ha="center", va="bottom", fontsize=7.5, fontweight="bold", color="#2B6CB0")

    plt.tight_layout()
    plt.savefig("report_assets/fig2_active_passive_handshake.png", dpi=300)
    plt.close()
    print("Created: report_assets/fig2_active_passive_handshake.png")


# -------------------------------------------------------------
# FIGURE 3: Chunked Streaming, Throttling & Resume
# -------------------------------------------------------------
def generate_fig3_streaming_resume():
    fig, ax = plt.subplots(figsize=(10, 4.8), dpi=300)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")

    # Title
    ax.text(5.0, 4.6, "Chunked Byte Streaming, Rate Limiting & REST Resumption", ha="center", va="center", fontsize=11, fontweight="bold", color="#1A202C")

    # Normal File Bar (Top)
    ax.text(0.5, 3.7, "Full 5 MB File:", fontsize=9, fontweight="bold", color="#2D3748")
    bar_full = patches.Rectangle((2.3, 3.4), 6.8, 0.6, fc="#CBD5E0", ec="#4A5568", lw=1.2)
    ax.add_patch(bar_full)
    for i in range(8):
        ax.plot([2.3 + i*0.85, 2.3 + i*0.85], [3.4, 4.0], color="#718096", lw=1, ls=":")
    ax.text(5.7, 3.7, "80 Chunks × 64 KB (Fixed Socket Buffers)", ha="center", va="center", fontsize=8.5, color="#1A202C")

    # Resumed File Bar (Middle)
    ax.text(0.5, 2.3, "Interrupted Download:", fontsize=9, fontweight="bold", color="#C53030")
    bar_existing = patches.Rectangle((2.3, 2.0), 2.0, 0.6, fc="#FEB2B2", ec="#E53E3E", lw=1.2)
    ax.add_patch(bar_existing)
    ax.text(3.3, 2.3, "1 MB on Disk", ha="center", va="center", fontsize=8, fontweight="bold", color="#9B2C2C")

    bar_missing = patches.Rectangle((4.3, 2.0), 4.8, 0.6, fc="#FEFCBF", ec="#D69E2E", lw=1.2, ls="--")
    ax.add_patch(bar_missing)
    ax.text(6.7, 2.3, "Remaining 4 MB Requested via REST 1048576", ha="center", va="center", fontsize=8, fontweight="bold", color="#744210")

    # Resume flow explanation
    ax.annotate("REST offset seek in f.seek(1048576)", xy=(4.3, 2.6), xytext=(4.3, 3.1),
                arrowprops=dict(arrowstyle="->", color="#D69E2E", lw=1.5), fontsize=8, color="#B7791F")

    # Rate Limiting & Token Bucket (Bottom)
    rate_box = patches.FancyBboxPatch(
        (1.0, 0.4), 8.0, 1.1, boxstyle="round,pad=0.15",
        fc="#EDF2F7", ec="#4A5568", lw=1.2
    )
    ax.add_patch(rate_box)
    ax.text(5.0, 1.15, "Bandwidth Throttling / Rate Limiting (Token Bucket Emulation)", ha="center", va="center", fontsize=9, fontweight="bold", color="#2B6CB0")
    ax.text(5.0, 0.75, "Chunk Sent (64 KB)  -->  Calculate Δt = (ChunkSize / RateLimit) - ElapsedTime  -->  Sleep(Δt)\n"
                       "Guarantees flat 1.0 MB/s throughput line on Wireshark I/O Graphs without bursty CPU spikes.",
            ha="center", va="center", fontsize=7.8, color="#4A5568")

    plt.tight_layout()
    plt.savefig("report_assets/fig3_chunked_streaming_resume.png", dpi=300)
    plt.close()
    print("Created: report_assets/fig3_chunked_streaming_resume.png")


# -------------------------------------------------------------
# FIGURE 4: FTPS (Explicit TLS) Security Handshake
# -------------------------------------------------------------
def generate_fig4_ftps_flow():
    fig, ax = plt.subplots(figsize=(9, 5.2), dpi=300)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis("off")

    ax.text(5.0, 6.6, "RFC 4217 Explicit FTPS (Control & Data TLS Upgrade)", ha="center", va="center", fontsize=11, fontweight="bold", color="#1A202C")

    # Client and Server Lifelines
    ax.plot([2.5, 2.5], [0.5, 6.2], color="#CBD5E0", lw=2, ls="--")
    ax.plot([7.5, 7.5], [0.5, 6.2], color="#CBD5E0", lw=2, ls="--")
    ax.text(2.5, 6.3, "FTP Client", ha="center", va="center", fontweight="bold", bbox=dict(boxstyle="round", fc="#EBF8FF", ec="#3182CE"))
    ax.text(7.5, 6.3, "FTPS Server", ha="center", va="center", fontweight="bold", bbox=dict(boxstyle="round", fc="#F0FFF4", ec="#38A169"))

    steps = [
        (5.5, "TCP 3-Way Handshake (Port 2121) [Plaintext]", "#718096", False),
        (4.9, "AUTH TLS / AUTH SSL -->", "#DD6B20", True),
        (4.3, "<-- 234 AUTH TLS OK. Ready for negotiation", "#38A169", False),
        (3.6, "<== TLS 1.3 Cryptographic Handshake (server.crt) ==>", "#9F7AEA", False),
        (2.9, "[TLS Encrypted] USER anubhab  /  PASS password123", "#3182CE", True),
        (2.2, "[TLS Encrypted] PBSZ 0  /  PROT P (Private Data Channel)", "#3182CE", True),
        (1.5, "<== [Data Channel Wrapped with TLS SSLSocket] ==>", "#805AD5", False),
        (0.8, "[TLS Encrypted] File Bytes Streamed Securely", "#2B6CB0", False),
    ]

    for y, text, col, is_req in steps:
        if "<==" in text or "==>" in text:
            ax.annotate("", xy=(7.4, y), xytext=(2.6, y), arrowprops=dict(arrowstyle="<->", color=col, lw=2.5))
            ax.text(5.0, y + 0.16, text, ha="center", va="bottom", fontsize=8, fontweight="bold", color=col)
        elif is_req:
            ax.annotate("", xy=(7.4, y), xytext=(2.6, y), arrowprops=dict(arrowstyle="->", color=col, lw=1.8))
            ax.text(5.0, y + 0.16, text, ha="center", va="bottom", fontsize=8, color=col)
        else:
            ax.annotate("", xy=(2.6, y), xytext=(7.4, y), arrowprops=dict(arrowstyle="->", color=col, lw=1.8))
            ax.text(5.0, y + 0.16, text, ha="center", va="bottom", fontsize=8, color=col)

    plt.tight_layout()
    plt.savefig("report_assets/fig4_ftps_encryption_flow.png", dpi=300)
    plt.close()
    print("Created: report_assets/fig4_ftps_encryption_flow.png")


if __name__ == "__main__":
    generate_fig1_architecture()
    generate_fig2_active_passive()
    generate_fig3_streaming_resume()
    generate_fig4_ftps_flow()
