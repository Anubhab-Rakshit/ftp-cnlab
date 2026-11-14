"""
Interactive FTP Command Line Interface Shell.
Provides a full-featured terminal client with progress bar, command history, and packet view toggle.
"""

import cmd
import os
import sys
import time
from typing import Optional

from client.ftp_client import FTPClient
from client.integrity import compute_file_sha256
from common.rfc959 import DEFAULT_FTP_CONTROL_PORT, TYPE_ASCII, TYPE_IMAGE


def draw_progress_bar(transferred: int, total: int, width: int = 40):
    """Draws a clean terminal progress bar."""
    if total > 0:
        percent = min(100.0, (transferred / total) * 100.0)
        filled = int(width * (transferred / total))
        bar = "=" * filled + "-" * (width - filled)
        sys.stdout.write(f"\r  [{bar}] {percent:5.1f}% ({transferred}/{total} B)")
    else:
        # Indeterminate or unknown size
        sys.stdout.write(f"\r  Streaming: {transferred} bytes transferred...")
    sys.stdout.flush()


class FTPShell(cmd.Cmd):
    intro = (
        "\033[1;36m=========================================================\n"
        "       RFC 959 Pure Socket Interactive FTP Shell\n"
        " Type 'help' or '?' to list commands. Type 'quit' to exit.\n"
        "=========================================================\033[0m"
    )
    prompt = "\033[1;32mftp>\033[0m "

    def __init__(self, show_wire: bool = True):
        super().__init__()
        self.show_wire = show_wire
        self.client = FTPClient(show_wire=show_wire)
        self.local_workspace = os.path.realpath("storage/client_workspace")
        os.makedirs(self.local_workspace, exist_ok=True)

    def default(self, line):
        print(f"Unknown command: '{line.split()[0]}'. Type 'help' for available commands.")

    def emptyline(self):
        pass

    # ---------------- Connection Commands ----------------

    def do_open(self, arg):
        """Connect to an FTP server: open <host> [port]"""
        parts = arg.split()
        if not parts:
            print("Usage: open <host> [port]")
            return
        host = parts[0]
        port = int(parts[1]) if len(parts) > 1 else DEFAULT_FTP_CONTROL_PORT
        try:
            self.client.connect(host, port)
        except Exception as e:
            print(f"Connection failed: {e}")

    def do_user(self, arg):
        """Log in to FTP server: user <username> [password]"""
        if not self.client.is_connected:
            print("Not connected. Use 'open <host> [port]' first.")
            return
        parts = arg.split()
        if not parts:
            username = input("Username: ").strip()
            password = input("Password: ").strip()
        else:
            username = parts[0]
            password = parts[1] if len(parts) > 1 else input("Password: ").strip()
        try:
            self.client.login(username, password)
        except Exception as e:
            print(f"Login error: {e}")

    def do_wire(self, arg):
        """Toggle or set NVT/ASCII wire logging: wire [on|off]"""
        val = arg.strip().lower()
        if val in ("on", "true", "1"):
            self.show_wire = True
        elif val in ("off", "false", "0"):
            self.show_wire = False
        else:
            self.show_wire = not self.show_wire
        self.client.logger.show_wire = self.show_wire
        status = "ENABLED" if self.show_wire else "DISABLED"
        print(f"NVT/ASCII wire inspector is now {status}.")

    def do_mode(self, arg):
        """Set or show data connection mode: mode [active|passive]"""
        arg = arg.strip().lower()
        if not arg:
            print(f"Current data channel mode: {self.client.mode.upper()}")
            return
        try:
            self.client.set_mode(arg)
        except ValueError as e:
            print(e)

    def do_type(self, arg):
        """Set representation type: type [binary|ascii]"""
        arg = arg.strip().lower()
        if arg in ("binary", "bin", "i"):
            self.client.set_type(TYPE_IMAGE)
            print("Type set to Binary / Image (I).")
        elif arg in ("ascii", "asc", "a"):
            self.client.set_type(TYPE_ASCII)
            print("Type set to ASCII (A).")
        else:
            print("Usage: type [binary|ascii]")

    # ---------------- File Navigation ----------------

    def do_pwd(self, arg):
        """Print current working directory on server: pwd"""
        if not self.client.is_connected:
            print("Not connected.")
            return
        try:
            print(self.client.pwd())
        except Exception as e:
            print(f"Error: {e}")

    def do_cd(self, arg):
        """Change current directory on server: cd <directory>"""
        if not self.client.is_connected:
            print("Not connected.")
            return
        if not arg:
            print("Usage: cd <path>")
            return
        try:
            code, msg = self.client.cwd(arg.strip())
            print(msg)
        except Exception as e:
            print(f"Error: {e}")

    def do_cdup(self, arg):
        """Move to parent directory on server: cdup"""
        if not self.client.is_connected:
            print("Not connected.")
            return
        try:
            code, msg = self.client.cdup()
            print(msg)
        except Exception as e:
            print(f"Error: {e}")

    def do_ls(self, arg):
        """List files in directory on server: ls [path]"""
        if not self.client.is_connected:
            print("Not connected.")
            return
        try:
            listing = self.client.list(arg.strip())
            print(listing)
        except Exception as e:
            print(f"Error listing directory: {e}")

    do_dir = do_ls

    def do_mkdir(self, arg):
        """Create a directory on server: mkdir <dirname>"""
        if not self.client.is_connected:
            print("Not connected.")
            return
        if not arg:
            print("Usage: mkdir <dirname>")
            return
        try:
            code, msg = self.client.make_dir(arg.strip())
            print(msg)
        except Exception as e:
            print(f"Error: {e}")

    def do_rmdir(self, arg):
        """Remove a directory on server: rmdir <dirname>"""
        if not self.client.is_connected:
            print("Not connected.")
            return
        if not arg:
            print("Usage: rmdir <dirname>")
            return
        try:
            code, msg = self.client.remove_dir(arg.strip())
            print(msg)
        except Exception as e:
            print(f"Error: {e}")

    def do_delete(self, arg):
        """Delete a file on server: delete <filename>"""
        if not self.client.is_connected:
            print("Not connected.")
            return
        if not arg:
            print("Usage: delete <filename>")
            return
        try:
            code, msg = self.client.delete_file(arg.strip())
            print(msg)
        except Exception as e:
            print(f"Error: {e}")

    do_rm = do_delete

    def do_rename(self, arg):
        """Rename a file or folder on server: rename <source> <destination>"""
        if not self.client.is_connected:
            print("Not connected.")
            return
        parts = arg.split()
        if len(parts) != 2:
            print("Usage: rename <source> <destination>")
            return
        try:
            code, msg = self.client.rename(parts[0], parts[1])
            print(msg)
        except Exception as e:
            print(f"Error: {e}")

    def do_size(self, arg):
        """Get file size on server: size <filename>"""
        if not self.client.is_connected:
            print("Not connected.")
            return
        if not arg:
            print("Usage: size <filename>")
            return
        try:
            sz = self.client.get_size(arg.strip())
            print(f"{arg.strip()}: {sz} bytes")
        except Exception as e:
            print(f"Error: {e}")

    # ---------------- File Transfer ----------------

    def do_get(self, arg):
        """Download file from server: get <remote_file> [local_path]"""
        if not self.client.is_connected:
            print("Not connected.")
            return
        parts = arg.split()
        if not parts:
            print("Usage: get <remote_file> [local_path]")
            return
        remote_file = parts[0]
        if len(parts) > 1:
            local_dest = parts[1]
        else:
            local_dest = os.path.join(self.local_workspace, os.path.basename(remote_file))

        print(f"Starting download: '{remote_file}' -> '{local_dest}' (Mode: {self.client.mode.upper()})...")
        start_time = time.time()
        try:
            total_bytes, sha256_hex = self.client.retrieve_file(
                remote_path=remote_file,
                local_dest=local_dest,
                progress_cb=draw_progress_bar,
            )
            print()  # Newline after progress bar
            duration = max(0.001, time.time() - start_time)
            rate_kb = (total_bytes / 1024.0) / duration
            print(f"Downloaded {total_bytes} bytes in {duration:.3f}s ({rate_kb:.1f} KB/s)")
            print(f"Local SHA-256: {sha256_hex}")
        except Exception as e:
            print()
            print(f"Download failed: {e}")
            
    def do_reget(self, arg):
        """Resume download file from server: reget <remote_file> [local_path]"""
        if not self.client.is_connected:
            print("Not connected.")
            return
        parts = arg.split()
        if not parts:
            print("Usage: reget <remote_file> [local_path]")
            return
        remote_file = parts[0]
        if len(parts) > 1:
            local_dest = parts[1]
        else:
            local_dest = os.path.join(self.local_workspace, os.path.basename(remote_file))

        print(f"Resuming download: '{remote_file}' -> '{local_dest}' (Mode: {self.client.mode.upper()})...")
        start_time = time.time()
        try:
            # Note the resume=True parameter here!
            total_bytes, sha256_hex = self.client.retrieve_file(
                remote_path=remote_file,
                local_dest=local_dest,
                progress_cb=draw_progress_bar,
                resume=True 
            )
            print()  
            duration = max(0.001, time.time() - start_time)
            rate_kb = (total_bytes / 1024.0) / duration
            print(f"Resumed {total_bytes} bytes in {duration:.3f}s ({rate_kb:.1f} KB/s)")
            print(f"Final Local SHA-256: {sha256_hex}")
        except Exception as e:
            print()
            print(f"Resume failed: {e}")

    def do_put(self, arg):
        """Upload file to server: put <local_path> [remote_dest]"""
        if not self.client.is_connected:
            print("Not connected.")
            return
        parts = arg.split()
        if not parts:
            print("Usage: put <local_path> [remote_dest]")
            return
        local_path = parts[0]
        remote_dest = parts[1] if len(parts) > 1 else os.path.basename(local_path)

        if not os.path.isabs(local_path) and not os.path.exists(local_path):
            # Check inside local workspace
            ws_path = os.path.join(self.local_workspace, local_path)
            if os.path.exists(ws_path):
                local_path = ws_path

        if not os.path.exists(local_path):
            print(f"Local file not found: {local_path}")
            return

        print(f"Starting upload: '{local_path}' -> '{remote_dest}' (Mode: {self.client.mode.upper()})...")
        start_time = time.time()
        try:
            total_bytes, sha256_hex = self.client.store_file(
                local_path=local_path,
                remote_dest=remote_dest,
                progress_cb=draw_progress_bar,
            )
            print()  # Newline after progress bar
            duration = max(0.001, time.time() - start_time)
            rate_kb = (total_bytes / 1024.0) / duration
            print(f"Uploaded {total_bytes} bytes in {duration:.3f}s ({rate_kb:.1f} KB/s)")
            print(f"Local SHA-256: {sha256_hex}")
        except Exception as e:
            print()
            print(f"Upload failed: {e}")

    def do_sha256(self, arg):
        """Calculate SHA-256 of a local file: sha256 <local_path>"""
        if not arg:
            print("Usage: sha256 <local_path>")
            return
        path = arg.strip()
        if not os.path.exists(path):
            ws_path = os.path.join(self.local_workspace, path)
            if os.path.exists(ws_path):
                path = ws_path
        if not os.path.exists(path):
            print(f"File not found: {path}")
            return
        h = compute_file_sha256(path)
        print(f"SHA-256 ({path}): {h}")

    # ---------------- Session Commands ----------------

    def do_quit(self, arg):
        """Disconnect and exit FTP shell: quit"""
        if self.client.is_connected:
            try:
                self.client.quit()
            except Exception:
                pass
        print("Goodbye.")
        return True

    do_bye = do_quit
    do_exit = do_quit


def main():
    import argparse
    parser = argparse.ArgumentParser(description="RFC 959 Pure Socket FTP Interactive Shell")
    parser.add_argument("--host", default=None, help="Auto-connect to host on start")
    parser.add_argument("--port", type=int, default=DEFAULT_FTP_CONTROL_PORT, help="Port to connect")
    parser.add_argument("--no-wire", action="store_true", help="Disable wire-level NVT/ASCII logging")
    args = parser.parse_args()

    shell = FTPShell(show_wire=not args.no_wire)
    if args.host:
        try:
            shell.client.connect(args.host, args.port)
        except Exception as e:
            print(f"Could not connect to {args.host}:{args.port}: {e}")

    try:
        shell.cmdloop()
    except KeyboardInterrupt:
        print("\nExiting.")
        if shell.client.is_connected:
            shell.client.quit()


if __name__ == "__main__":
    main()

