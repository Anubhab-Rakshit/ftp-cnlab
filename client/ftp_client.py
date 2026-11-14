"""
Pure Socket RFC 959 FTP Client Engine.
Implements dual-channel architecture (Active and Passive) using raw TCP sockets.
"""

import hashlib
import os
import socket
from typing import Callable, Optional, Tuple

from common.logger import WireLogger
from common.protocol_parser import (
    format_port_command,
    parse_pasv_reply,
    parse_reply_line,
)
from common.rfc959 import (
    BUFFER_SIZE,
    CMD_APPE,
    CMD_CDUP,
    CMD_CWD,
    CMD_DELE,
    CMD_FEAT,
    CMD_HELP,
    CMD_LIST,
    CMD_MKD,
    CMD_MODE,
    CMD_NLST,
    CMD_NOOP,
    CMD_PASS,
    CMD_PASV,
    CMD_PORT,
    CMD_PWD,
    CMD_QUIT,
    CMD_REST,
    CMD_RETR,
    CMD_RMD,
    CMD_RNFR,
    CMD_RNTO,
    CMD_SIZE,
    CMD_STOR,
    CMD_STRU,
    CMD_SYST,
    CMD_TYPE,
    CMD_USER,
    DEFAULT_FTP_CONTROL_PORT,
    MODE_STREAM,
    R_150_FILE_STATUS_OK_OPEN_DATA,
    R_200_COMMAND_OK,
    R_220_SERVICE_READY_NEW_USER,
    R_226_CLOSING_DATA_CONN_SUCCESS,
    R_227_ENTERING_PASSIVE_MODE,
    R_230_USER_LOGGED_IN,
    R_250_REQUESTED_FILE_ACTION_OK,
    R_257_PATHNAME_CREATED,
    R_331_USER_NAME_OK_NEED_PASS,
    STRU_FILE,
    TELNET_EOL,
    TYPE_ASCII,
    TYPE_IMAGE,
)


class FTPClient:
    """Client implementing RFC 959 commands over raw sockets."""

    MODE_PASSIVE = "passive"
    MODE_ACTIVE = "active"

    def __init__(self, show_wire: bool = True):
        self.logger = WireLogger(prefix="CLIENT", show_wire=show_wire)
        self.ctrl_sock: Optional[socket.socket] = None
        self.host: Optional[str] = None
        self.port: int = DEFAULT_FTP_CONTROL_PORT
        self.mode: str = self.MODE_PASSIVE  # Default to Passive mode (NAT/firewall friendly)
        self.rep_type: str = TYPE_IMAGE
        self.is_connected: bool = False
        self._recv_buffer: str = ""

    def connect(self, host: str, port: int = DEFAULT_FTP_CONTROL_PORT, timeout: float = 15.0) -> Tuple[int, str]:
        """Establishes control connection to FTP server."""
        self.host = host
        self.port = port
        self.ctrl_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ctrl_sock.settimeout(timeout)

        self.logger.info(f"Connecting to FTP control server at {host}:{port}...")
        self.ctrl_sock.connect((host, port))
        self.is_connected = True
        self._recv_buffer = ""

        # Receive 220 banner
        code, msg = self._read_reply()
        if code != R_220_SERVICE_READY_NEW_USER:
            self.logger.warn(f"Unexpected greeting code: {code} {msg}")
        else:
            self.logger.success(f"Connected: {msg}")
        return code, msg

    def _send_line(self, line: str):
        """Sends a raw command string over the control socket."""
        if not self.ctrl_sock:
            raise ConnectionError("Not connected to server.")
        wire_str = line + TELNET_EOL
        self.logger.ctrl_send(wire_str)
        self.ctrl_sock.sendall(wire_str.encode("utf-8"))

    def _read_reply(self) -> Tuple[int, str]:
        """
        Reads a full RFC 959 reply (single-line or multi-line) from control socket.
        """
        if not self.ctrl_sock:
            raise ConnectionError("Not connected to server.")

        final_code = 0
        message_lines = []
        is_multiline = False

        while True:
            # Check if we have a full line in buffer
            while "\n" not in self._recv_buffer:
                chunk = self.ctrl_sock.recv(4096)
                if not chunk:
                    raise ConnectionResetError("Server closed control connection.")
                self._recv_buffer += chunk.decode("utf-8", errors="replace")

            line, self._recv_buffer = self._recv_buffer.split("\n", 1)
            line = line.rstrip("\r")
            if not line:
                continue

            self.logger.ctrl_recv(line + "\r\n")
            code, msg, multi = parse_reply_line(line)

            if code != 0:
                if not is_multiline:
                    final_code = code
                    message_lines.append(msg)
                    if multi:
                        is_multiline = True
                    else:
                        break
                else:
                    message_lines.append(msg)
                    # Multiline ends when a line starts with code followed by a space
                    if not multi and code == final_code:
                        break
            else:
                message_lines.append(line)

        return final_code, "\n".join(message_lines)

    def send_cmd(self, cmd: str, arg: str = "") -> Tuple[int, str]:
        """Sends an FTP command and waits for reply."""
        line = f"{cmd} {arg}".strip()
        self._send_line(line)
        return self._read_reply()

    # ---------------- Authentication & Session ----------------

    def login(self, username: str = "anonymous", password: str = "guest@") -> Tuple[int, str]:
        """Performs USER / PASS login sequence."""
        code, msg = self.send_cmd(CMD_USER, username)
        if code == R_331_USER_NAME_OK_NEED_PASS:
            code, msg = self.send_cmd(CMD_PASS, password)
        if code == R_230_USER_LOGGED_IN:
            self.logger.success(f"Successfully authenticated as '{username}'.")
            # Set default type to Binary (Image)
            self.set_type(TYPE_IMAGE)
        else:
            self.logger.error(f"Login failed: {code} {msg}")
        return code, msg

    def quit(self) -> Tuple[int, str]:
        """Sends QUIT and closes control socket."""
        try:
            code, msg = self.send_cmd(CMD_QUIT)
        except Exception:
            code, msg = 221, "Goodbye"
        finally:
            self.is_connected = False
            if self.ctrl_sock:
                try:
                    self.ctrl_sock.close()
                except Exception:
                    pass
                self.ctrl_sock = None
        return code, msg

    def noop(self) -> Tuple[int, str]:
        return self.send_cmd(CMD_NOOP)

    def syst(self) -> Tuple[int, str]:
        return self.send_cmd(CMD_SYST)

    def feat(self) -> Tuple[int, str]:
        return self.send_cmd(CMD_FEAT)

    def help(self, topic: str = "") -> Tuple[int, str]:
        return self.send_cmd(CMD_HELP, topic)

    def set_mode(self, mode: str):
        """Sets client data mode: 'passive' or 'active'."""
        mode_lower = mode.lower()
        if mode_lower in (self.MODE_PASSIVE, self.MODE_ACTIVE):
            self.mode = mode_lower
            self.logger.info(f"Client data mode set to: {self.mode.upper()}")
        else:
            raise ValueError(f"Unknown mode '{mode}'. Choose 'passive' or 'active'.")

    def set_type(self, rep_type: str = TYPE_IMAGE) -> Tuple[int, str]:
        """Sets representation type: TYPE I (Binary) or TYPE A (ASCII)."""
        code, msg = self.send_cmd(CMD_TYPE, rep_type)
        if code == R_200_COMMAND_OK:
            self.rep_type = rep_type
        return code, msg

    # ---------------- File Navigation & Management ----------------

    def pwd(self) -> str:
        code, msg = self.send_cmd(CMD_PWD)
        if code == R_257_PATHNAME_CREATED:
            # Extract directory between quotes
            if '"' in msg:
                return msg.split('"')[1]
            return msg
        raise RuntimeError(f"PWD failed: {code} {msg}")

    def cwd(self, path: str) -> Tuple[int, str]:
        return self.send_cmd(CMD_CWD, path)

    def cdup(self) -> Tuple[int, str]:
        return self.send_cmd(CMD_CDUP)

    def make_dir(self, path: str) -> Tuple[int, str]:
        return self.send_cmd(CMD_MKD, path)

    def remove_dir(self, path: str) -> Tuple[int, str]:
        return self.send_cmd(CMD_RMD, path)

    def delete_file(self, path: str) -> Tuple[int, str]:
        return self.send_cmd(CMD_DELE, path)

    def rename(self, old_name: str, new_name: str) -> Tuple[int, str]:
        code, msg = self.send_cmd(CMD_RNFR, old_name)
        if code != 350:
            return code, msg
        return self.send_cmd(CMD_RNTO, new_name)

    def get_size(self, path: str) -> int:
        code, msg = self.send_cmd(CMD_SIZE, path)
        if code == 213:
            return int(msg.strip())
        raise FileNotFoundError(f"Cannot get size for {path}: {code} {msg}")

    # ---------------- Data Connection Handlers ----------------

    def _setup_data_socket(self) -> Tuple[Optional[socket.socket], Optional[socket.socket]]:
        """
        Configures the data channel based on self.mode (Passive or Active).
        Returns:
            Passive: (data_socket, None)
            Active:  (None, active_listener_socket)
        """
        if self.mode == self.MODE_PASSIVE:
            code, msg = self.send_cmd(CMD_PASV)
            if code != R_227_ENTERING_PASSIVE_MODE:
                raise RuntimeError(f"PASV command failed: {code} {msg}")
            pasv_ip, pasv_port = parse_pasv_reply(msg)

            # Connect data socket to server's passive endpoint
            data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            data_sock.settimeout(30.0)
            self.logger.data_event("PASV", f"Connecting to server data endpoint {pasv_ip}:{pasv_port}")
            data_sock.connect((pasv_ip, pasv_port))
            return data_sock, None

        elif self.mode == self.MODE_ACTIVE:
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.settimeout(30.0)
            listener.bind(("0.0.0.0", 0))
            listener.listen(1)

            _, local_port = listener.getsockname()
            # Determine client IP as seen by server
            local_ip = self.ctrl_sock.getsockname()[0]
            if local_ip == "0.0.0.0":
                local_ip = "127.0.0.1"

            port_arg = format_port_command(local_ip, local_port)
            code, msg = self.send_cmd(CMD_PORT, port_arg)
            if code != R_200_COMMAND_OK:
                listener.close()
                raise RuntimeError(f"PORT command failed: {code} {msg}")

            self.logger.data_event("PORT", f"Active mode listening on {local_ip}:{local_port}")
            return None, listener

        else:
            raise ValueError(f"Unknown data mode: {self.mode}")

    def _finalize_data_connection(
        self, data_sock: Optional[socket.socket], listener: Optional[socket.socket]
    ) -> socket.socket:
        """For active mode, accepts server's incoming connection; for passive, returns connected socket."""
        if self.mode == self.MODE_PASSIVE:
            return data_sock
        else:
            conn, addr = listener.accept()
            conn.settimeout(30.0)
            listener.close()
            self.logger.data_event("ESTB", f"Accepted active data connection from server {addr}")
            return conn

    # ---------------- High-Level Transfer Operations ----------------

    def list(self, path: str = "") -> str:
        """Retrieves and returns directory listing."""
        connected_sock, listener = self._setup_data_socket()

        code, msg = self.send_cmd(CMD_LIST, path)
        if code not in (R_150_FILE_STATUS_OK_OPEN_DATA, 125):
            if connected_sock:
                connected_sock.close()
            if listener:
                listener.close()
            raise RuntimeError(f"LIST failed: {code} {msg}")

        active_sock = self._finalize_data_connection(connected_sock, listener)
        data = b""
        try:
            while True:
                chunk = active_sock.recv(BUFFER_SIZE)
                if not chunk:
                    break
                data += chunk
        finally:
            active_sock.close()

        code, msg = self._read_reply()
        if code != R_226_CLOSING_DATA_CONN_SUCCESS:
            self.logger.warn(f"Warning after LIST transfer: {code} {msg}")

        return data.decode("utf-8", errors="replace")

    def retrieve_file(
        self,
        remote_path: str,
        local_dest: str,
        progress_cb: Optional[Callable[[int, int], None]] = None,
        resume: bool = False,
    ) -> Tuple[int, str]:
        """
        Downloads a file from server in chunks and calculates SHA-256.
        Returns: (total_bytes_received, sha256_hex)
        """
        # Attempt to get remote size for progress reporting
        total_size = 0
        try:
            total_size = self.get_size(remote_path)
        except Exception:
            pass
        
        rest_offset = 0
        hasher = hashlib.sha256()
        
        if resume and os.path.exists(local_dest):
            rest_offset = os.path.getsize(local_dest)
            if rest_offset > 0:
                # Ask the server to resume from this byte offset
                code, msg = self.send_cmd(CMD_REST, str(rest_offset))
                if code != 350:
                    raise RuntimeError(f"REST command rejected: {code} {msg}")
                
                # Pre-feed the existing local file into the SHA256 hasher
                with open(local_dest, "rb") as existing_file:
                    while True:
                        existing_chunk = existing_file.read(BUFFER_SIZE)
                        if not existing_chunk:
                            break
                        hasher.update(existing_chunk)

        connected_sock, listener = self._setup_data_socket()

        code, msg = self.send_cmd(CMD_RETR, remote_path)
        if code not in (R_150_FILE_STATUS_OK_OPEN_DATA, 125):
            if connected_sock:
                connected_sock.close()
            if listener:
                listener.close()
            raise RuntimeError(f"RETR failed: {code} {msg}")

        active_sock = self._finalize_data_connection(connected_sock, listener)

        total_recv = rest_offset

        # Ensure parent directory exists for local destination
        os.makedirs(os.path.dirname(os.path.abspath(local_dest)), exist_ok=True)
        open_mode = "ab" if (resume and rest_offset > 0) else "wb"
        try:
            with open(local_dest, open_mode) as f:
                while True:
                    chunk = active_sock.recv(BUFFER_SIZE)
                    if not chunk:
                        break
                    f.write(chunk)
                    hasher.update(chunk)
                    total_recv += len(chunk)
                    if progress_cb:
                        progress_cb(total_recv, total_size)
        finally:
            active_sock.close()

        code, msg = self._read_reply()
        if code != R_226_CLOSING_DATA_CONN_SUCCESS:
            self.logger.warn(f"Warning after RETR transfer: {code} {msg}")

        sha256_hex = hasher.hexdigest()
        self.logger.success(f"Downloaded {total_recv} bytes -> '{local_dest}' [SHA-256: {sha256_hex[:12]}...]")
        return total_recv, sha256_hex

    def store_file(
        self,
        local_path: str,
        remote_dest: Optional[str] = None,
        progress_cb: Optional[Callable[[int, int], None]] = None,
    ) -> Tuple[int, str]:
        """
        Uploads a local file to server in chunks and calculates SHA-256.
        Returns: (total_bytes_sent, sha256_hex)
        """
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Local file does not exist: {local_path}")

        file_size = os.path.getsize(local_path)
        target_name = remote_dest if remote_dest else os.path.basename(local_path)

        connected_sock, listener = self._setup_data_socket()

        code, msg = self.send_cmd(CMD_STOR, target_name)
        if code not in (R_150_FILE_STATUS_OK_OPEN_DATA, 125):
            if connected_sock:
                connected_sock.close()
            if listener:
                listener.close()
            raise RuntimeError(f"STOR failed: {code} {msg}")

        active_sock = self._finalize_data_connection(connected_sock, listener)

        hasher = hashlib.sha256()
        total_sent = 0

        try:
            with open(local_path, "rb") as f:
                while True:
                    chunk = f.read(BUFFER_SIZE)
                    if not chunk:
                        break
                    active_sock.sendall(chunk)
                    hasher.update(chunk)
                    total_sent += len(chunk)
                    if progress_cb:
                        progress_cb(total_sent, file_size)
        finally:
            active_sock.close()

        code, msg = self._read_reply()
        if code != R_226_CLOSING_DATA_CONN_SUCCESS:
            self.logger.warn(f"Warning after STOR transfer: {code} {msg}")

        sha256_hex = hasher.hexdigest()
        self.logger.success(f"Uploaded {total_sent} bytes -> '{target_name}' [SHA-256: {sha256_hex[:12]}...]")
        return total_sent, sha256_hex

