"""
FTP Client Session Handler implementing the RFC 959 state machine.
Handles per-client control connection, command dispatching, and file streaming.
"""

import hashlib
import os
import socket
import traceback
import time
import ssl
from typing import Optional
from pathlib import Path


from common.logger import WireLogger
from common.protocol_parser import (
    parse_command_line,
    format_reply,
    format_multiline_reply,
    parse_port_command,
    format_pasv_reply,
    format_epsv_reply,
    parse_eprt_command,
)
from common.rfc959 import (
    BUFFER_SIZE,
    CMD_ABOR,
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
    CMD_EPSV,
    CMD_EPRT,
    MODE_STREAM,
    R_150_FILE_STATUS_OK_OPEN_DATA,
    R_200_COMMAND_OK,
    R_202_COMMAND_NOT_IMPLEMENTED,
    R_211_SYSTEM_STATUS_OR_HELP,
    R_213_FILE_STATUS,
    R_214_HELP_MESSAGE,
    R_215_NAME_SYSTEM_TYPE,
    R_220_SERVICE_READY_NEW_USER,
    R_221_CLOSING_CONTROL_CONN,
    R_226_CLOSING_DATA_CONN_SUCCESS,
    R_230_USER_LOGGED_IN,
    R_250_REQUESTED_FILE_ACTION_OK,
    R_257_PATHNAME_CREATED,
    R_331_USER_NAME_OK_NEED_PASS,
    R_350_FILE_ACTION_PENDING_INFO,
    R_425_CANT_OPEN_DATA_CONN,
    R_426_CONN_CLOSED_TRANSFER_ABORT,
    R_451_LOCAL_ERROR_IN_PROCESSING,
    R_500_SYNTAX_ERROR_UNRECOGNIZED,
    R_501_SYNTAX_ERROR_IN_PARAMS,
    R_502_COMMAND_NOT_IMPLEMENTED,
    R_503_BAD_SEQUENCE_OF_COMMANDS,
    R_504_COMMAND_PARAM_NOT_IMPL,
    R_530_NOT_LOGGED_IN,
    R_550_FILE_NOT_FOUND_OR_NO_ACC,
    STRU_FILE,
    TELNET_EOL,
    TYPE_ASCII,
    TYPE_IMAGE,
)
from server.auth import AuthManager, UserAccount
from server.data_channel import DataChannelManager
from server.vfs import VirtualFileSystem


class FTPSession:
    """Manages an individual FTP client connection lifecycle."""

    STATE_NOT_AUTHENTICATED = 0
    STATE_NEED_PASSWORD = 1
    STATE_AUTHENTICATED = 2

    def __init__(
        self,
        ctrl_socket: socket.socket,
        client_addr: tuple,
        root_dir: str,
        auth_mgr: AuthManager,
        logger: WireLogger,
    ):
        self.sock = ctrl_socket
        self.addr = client_addr
        self.client_id = f"{client_addr[0]}:{client_addr[1]}"
        self.auth_mgr = auth_mgr
        self.logger = logger
        self.vfs = VirtualFileSystem(root_dir)
        self.data_mgr = DataChannelManager(server_host=ctrl_socket.getsockname()[0])

        self.state = self.STATE_NOT_AUTHENTICATED
        self.pending_user: Optional[str] = None
        self.current_user: Optional[UserAccount] = None

        self.rep_type = TYPE_IMAGE  # Default to Binary (Image)
        self.trans_mode = MODE_STREAM
        self.file_stru = STRU_FILE
        self.rest_offset = 0
        self.rnfr_path: Optional[str] = None
        self.is_running = True
        self.data_prot = "C" # 'C' = Cleartext, 'P' = Private (Encrypted)
        self.ssl_context = ctrl_socket.server_context if hasattr(ctrl_socket, 'server_context') else None

    def send_raw(self, reply_text: str):
        """Sends an NVT/ASCII reply over the control socket and logs it."""
        try:
            self.logger.ctrl_send(reply_text, self.client_id)
            self.sock.sendall(reply_text.encode("utf-8"))
        except Exception as e:
            self.logger.warn(f"Failed to send control response to {self.client_id}: {e}")
            self.is_running = False

    def reply(self, code: int, message: str):
        self.send_raw(format_reply(code, message))

    def run(self):
        """Main control loop for this client session."""
        self.logger.info(f"Accepted control connection from {self.client_id}")
        self.reply(R_220_SERVICE_READY_NEW_USER, "RFC 959 Python FTP Server Ready.")

        buffer = ""
        while self.is_running:
            try:
                data = self.sock.recv(4096)
                if not data:
                    self.logger.info(f"Client {self.client_id} disconnected.")
                    break
                buffer += data.decode("utf-8", errors="replace")

                while "\r\n" in buffer or "\n" in buffer:
                    if "\r\n" in buffer:
                        line, buffer = buffer.split("\r\n", 1)
                    else:
                        line, buffer = buffer.split("\n", 1)
                    line = line.strip("\r")
                    if not line:
                        continue
                    self.logger.ctrl_recv(line + "\r\n", self.client_id)
                    self.dispatch_command(line)

            except socket.timeout:
                continue
            except ConnectionResetError:
                self.logger.info(f"Client {self.client_id} reset connection.")
                break
            except Exception as e:
                self.logger.error(f"Error handling client {self.client_id}: {e}")
                break

        self.cleanup()

    def cleanup(self):
        """Releases session resources and closes sockets."""
        self.is_running = False
        self.data_mgr.cleanup()
        try:
            self.sock.close()
        except Exception:
            pass
        self.logger.info(f"Session closed for {self.client_id}")

    def dispatch_command(self, raw_line: str):
        """Dispatches an RFC 959 command to its respective handler."""
        cmd, arg = parse_command_line(raw_line)
        if not cmd:
            return

        # Pre-authentication commands
        if self.state != self.STATE_AUTHENTICATED:
            if cmd == CMD_USER:
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

        # Authenticated command table
        handlers = {
            CMD_USER: self.handle_USER,
            CMD_PASS: self.handle_PASS,
            CMD_QUIT: self.handle_QUIT,
            CMD_NOOP: lambda a: self.reply(R_200_COMMAND_OK, "NOOP okay."),
            CMD_SYST: lambda a: self.reply(R_215_NAME_SYSTEM_TYPE, "UNIX Type: L8"),
            CMD_FEAT: self.handle_FEAT,
            CMD_HELP: self.handle_HELP,
            CMD_PWD: self.handle_PWD,
            CMD_CWD: self.handle_CWD,
            CMD_CDUP: self.handle_CDUP,
            CMD_MKD: self.handle_MKD,
            CMD_RMD: self.handle_RMD,
            CMD_DELE: self.handle_DELE,
            CMD_RNFR: self.handle_RNFR,
            CMD_RNTO: self.handle_RNTO,
            CMD_TYPE: self.handle_TYPE,
            CMD_MODE: self.handle_MODE,
            CMD_STRU: self.handle_STRU,
            CMD_PORT: self.handle_PORT,
            CMD_PASV: self.handle_PASV,
            CMD_EPRT: self.handle_EPRT,
            CMD_EPSV: self.handle_EPSV,
            CMD_LIST: self.handle_LIST,
            CMD_NLST: self.handle_NLST,
            CMD_RETR: self.handle_RETR,
            CMD_STOR: self.handle_STOR,
            CMD_APPE: self.handle_APPE,
            CMD_SIZE: self.handle_SIZE,
            CMD_REST: self.handle_REST,
            CMD_ABOR: self.handle_ABOR,

            "AUTH": self.handle_AUTH,
            "PROT": self.handle_PROT,
            "PBSZ": self.handle_PBSZ,
        }

        handler = handlers.get(cmd)
        if handler:
            try:
                handler(arg)
            except Exception as e:
                self.logger.error(f"Exception handling {cmd} {arg}: {e}")
                self.reply(R_451_LOCAL_ERROR_IN_PROCESSING, f"Internal error: {e}")
        else:
            self.reply(R_502_COMMAND_NOT_IMPLEMENTED, f"Command '{cmd}' not implemented.")

    # ---------------- Command Handlers ----------------

    def handle_USER(self, arg: str):
        if not arg:
            self.reply(R_501_SYNTAX_ERROR_IN_PARAMS, "USER requires a username.")
            return
        self.pending_user = arg.strip()
        if self.auth_mgr.user_exists(self.pending_user):
            self.state = self.STATE_NEED_PASSWORD
            self.reply(R_331_USER_NAME_OK_NEED_PASS, f"Password required for {self.pending_user}.")
        else:
            self.reply(R_530_NOT_LOGGED_IN, "User not found.")

    def handle_PASS(self, arg: str):
        if self.state != self.STATE_NEED_PASSWORD or not self.pending_user:
            self.reply(R_503_BAD_SEQUENCE_OF_COMMANDS, "Login with USER first.")
            return
        account = self.auth_mgr.verify_password(self.pending_user, arg)
        if account:
            self.current_user = account
            self.state = self.STATE_AUTHENTICATED
            self.reply(R_230_USER_LOGGED_IN, f"User {self.pending_user} logged in successfully.")
        else:
            self.state = self.STATE_NOT_AUTHENTICATED
            self.reply(R_530_NOT_LOGGED_IN, "Authentication failed.")

    def handle_QUIT(self, arg: str):
        self.reply(R_221_CLOSING_CONTROL_CONN, "Goodbye.")
        self.is_running = False

    def handle_FEAT(self, arg: str):
        lines = [
            "Features:",
            " SIZE",
            " REST STREAM",
            " PASV",
            " UTF8",
            "End",
        ]
        self.send_raw(format_multiline_reply(R_211_SYSTEM_STATUS_OR_HELP, lines))

    def handle_HELP(self, arg: str):
        self.reply(R_214_HELP_MESSAGE, "Commands: USER, PASS, QUIT, PWD, CWD, CDUP, LIST, RETR, STOR, PORT, PASV, TYPE, SIZE, DELE, MKD, RMD.")

    def handle_PWD(self, arg: str):
        current_dir = self.vfs.pwd()
        self.reply(R_257_PATHNAME_CREATED, f'"{current_dir}" is current directory.')

    def handle_CWD(self, arg: str):
        if not arg:
            self.reply(R_501_SYNTAX_ERROR_IN_PARAMS, "CWD requires path argument.")
            return
        try:
            new_dir = self.vfs.cwd(arg)
            self.reply(R_250_REQUESTED_FILE_ACTION_OK, f'Directory successfully changed to "{new_dir}".')
        except Exception as e:
            self.reply(R_550_FILE_NOT_FOUND_OR_NO_ACC, f"Failed to change directory: {e}")

    def handle_CDUP(self, arg: str):
        try:
            new_dir = self.vfs.cdup()
            self.reply(R_250_REQUESTED_FILE_ACTION_OK, f'Directory changed to parent: "{new_dir}".')
        except Exception as e:
            self.reply(R_550_FILE_NOT_FOUND_OR_NO_ACC, f"Failed to change directory: {e}")

    def handle_MKD(self, arg: str):
        if not arg:
            self.reply(R_501_SYNTAX_ERROR_IN_PARAMS, "MKD requires directory name.")
            return
        if self.current_user and self.current_user.read_only:
            self.reply(R_550_FILE_NOT_FOUND_OR_NO_ACC, "Permission denied: read-only user.")
            return
        try:
            created = self.vfs.make_dir(arg)
            self.reply(R_257_PATHNAME_CREATED, f'"{created}" directory created.')
        except Exception as e:
            self.reply(R_550_FILE_NOT_FOUND_OR_NO_ACC, f"Cannot create directory: {e}")

    def handle_RMD(self, arg: str):
        if not arg:
            self.reply(R_501_SYNTAX_ERROR_IN_PARAMS, "RMD requires directory name.")
            return
        if self.current_user and self.current_user.read_only:
            self.reply(R_550_FILE_NOT_FOUND_OR_NO_ACC, "Permission denied: read-only user.")
            return
        try:
            self.vfs.remove_dir(arg)
            self.reply(R_250_REQUESTED_FILE_ACTION_OK, "Directory removed.")
        except Exception as e:
            self.reply(R_550_FILE_NOT_FOUND_OR_NO_ACC, f"Cannot remove directory: {e}")

    def handle_DELE(self, arg: str):
        if not arg:
            self.reply(R_501_SYNTAX_ERROR_IN_PARAMS, "DELE requires file name.")
            return
        if self.current_user and self.current_user.read_only:
            self.reply(R_550_FILE_NOT_FOUND_OR_NO_ACC, "Permission denied: read-only user.")
            return
        try:
            self.vfs.delete_file(arg)
            self.reply(R_250_REQUESTED_FILE_ACTION_OK, "File deleted.")
        except Exception as e:
            self.reply(R_550_FILE_NOT_FOUND_OR_NO_ACC, f"Cannot delete file: {e}")

    def handle_RNFR(self, arg: str):
        if not arg:
            self.reply(R_501_SYNTAX_ERROR_IN_PARAMS, "RNFR requires source path.")
            return
        try:
            real_path, _ = self.vfs.resolve(arg)
            if not os.path.exists(real_path):
                self.reply(R_550_FILE_NOT_FOUND_OR_NO_ACC, "File does not exist.")
                return
            self.rnfr_path = arg
            self.reply(R_350_FILE_ACTION_PENDING_INFO, "File exists, ready for destination name (RNTO).")
        except Exception as e:
            self.reply(R_550_FILE_NOT_FOUND_OR_NO_ACC, f"Invalid path: {e}")

    def handle_RNTO(self, arg: str):
        if not self.rnfr_path:
            self.reply(R_503_BAD_SEQUENCE_OF_COMMANDS, "RNFR required prior to RNTO.")
            return
        if not arg:
            self.reply(R_501_SYNTAX_ERROR_IN_PARAMS, "RNTO requires destination path.")
            return
        try:
            self.vfs.rename(self.rnfr_path, arg)
            self.rnfr_path = None
            self.reply(R_250_REQUESTED_FILE_ACTION_OK, "Rename successful.")
        except Exception as e:
            self.rnfr_path = None
            self.reply(R_550_FILE_NOT_FOUND_OR_NO_ACC, f"Rename failed: {e}")

    def handle_TYPE(self, arg: str):
        t = arg.strip().upper()
        if t in (TYPE_IMAGE, "L 8", "L8"):
            self.rep_type = TYPE_IMAGE
            self.reply(R_200_COMMAND_OK, "Type set to I (Binary / Image).")
        elif t in (TYPE_ASCII, "A N", "AN"):
            self.rep_type = TYPE_ASCII
            self.reply(R_200_COMMAND_OK, "Type set to A (ASCII).")
        else:
            self.reply(R_504_COMMAND_PARAM_NOT_IMPL, f"Type '{arg}' not supported. Use A or I.")

    def handle_MODE(self, arg: str):
        m = arg.strip().upper()
        if m == MODE_STREAM:
            self.reply(R_200_COMMAND_OK, "Mode set to S (Stream).")
        else:
            self.reply(R_504_COMMAND_PARAM_NOT_IMPL, f"Mode '{arg}' not supported. Only Stream mode.")

    def handle_STRU(self, arg: str):
        s = arg.strip().upper()
        if s == STRU_FILE:
            self.reply(R_200_COMMAND_OK, "Structure set to F (File).")
        else:
            self.reply(R_504_COMMAND_PARAM_NOT_IMPL, f"Structure '{arg}' not supported.")

    def handle_PORT(self, arg: str):
        try:
            ip, port = parse_port_command(arg)
            self.data_mgr.set_active(ip, port)
            self.logger.data_event("PORT", f"Active mode configured -> Client Data Listener at {ip}:{port}", self.client_id)
            self.reply(R_200_COMMAND_OK, "PORT command successful.")
        except Exception as e:
            self.reply(R_501_SYNTAX_ERROR_IN_PARAMS, f"Illegal PORT command: {e}")

    def handle_PASV(self, arg: str):
        try:
            # Bind ephemeral listening port
            ctrl_ip = self.sock.getsockname()[0]
            ip, port = self.data_mgr.setup_passive(advertise_ip=ctrl_ip)
            self.logger.data_event("PASV", f"Passive mode listener active on {ip}:{port}", self.client_id)
            self.send_raw(format_pasv_reply(ip, port))
        except Exception as e:
            self.logger.error(f"Failed to enter passive mode: {e}")
            self.reply(R_425_CANT_OPEN_DATA_CONN, f"Cannot open passive listener: {e}")

    def handle_EPSV(self, arg: str):
        try:
            _, port = self.data_mgr.setup_passive()
            self.logger.data_event("EPSV", f"Extended passive mode listener active on port {port}", self.client_id)
            self.send_raw(format_epsv_reply(port))
        except Exception as e:
            self.logger.error(f"Failed to enter EPSV mode: {e}")
            self.reply(R_425_CANT_OPEN_DATA_CONN, f"Cannot open extended passive listener: {e}")

    def handle_EPRT(self, arg: str):
        try:
            ip, port = parse_eprt_command(arg)
            self.data_mgr.set_active(ip, port)
            self.logger.data_event("EPRT", f"Active mode configured -> Client Data Listener at {ip}:{port}", self.client_id)
            self.reply(R_200_COMMAND_OK, "EPRT command successful.")
        except Exception as e:
            self.reply(R_501_SYNTAX_ERROR_IN_PARAMS, f"Illegal EPRT command: {e}")

    def handle_SIZE(self, arg: str):
        if not arg:
            self.reply(R_501_SYNTAX_ERROR_IN_PARAMS, "SIZE requires filename.")
            return
        try:
            sz = self.vfs.get_size(arg)
            self.reply(R_213_FILE_STATUS, str(sz))
        except Exception as e:
            self.reply(R_550_FILE_NOT_FOUND_OR_NO_ACC, f"Could not get size: {e}")

    def handle_REST(self, arg: str):
        try:
            offset = int(arg)
            if offset < 0:
                raise ValueError()
            self.rest_offset = offset
            self.reply(R_350_FILE_ACTION_PENDING_INFO, f"Restarting at {self.rest_offset}. Send STORE or RETRIEVE.")
        except Exception:
            self.reply(R_501_SYNTAX_ERROR_IN_PARAMS, "REST requires a non-negative integer offset.")

    def handle_ABOR(self, arg: str):
        self.data_mgr.cleanup()
        self.reply(R_226_CLOSING_DATA_CONN_SUCCESS, "ABOR command processed.")

    # ---------------- Data Transfer Commands ----------------

    def handle_LIST(self, arg: str):
        self._transfer_directory_listing(arg, detailed=True)

    def handle_NLST(self, arg: str):
        self._transfer_directory_listing(arg, detailed=False)

    def _transfer_directory_listing(self, target_path: str, detailed: bool):
        """Generates and streams directory listing over the data channel."""
        try:
            listing_bytes = self.vfs.list_dir(target_path if target_path else None, detailed=detailed)
        except Exception as e:
            self.reply(R_550_FILE_NOT_FOUND_OR_NO_ACC, f"File or directory not found: {e}")
            self.data_mgr.cleanup()
            return

        try:
            data_sock = self.data_mgr.open_connection(prot=self.data_prot, ssl_context=self.ssl_context)
            self.logger.data_event("ESTB", "Data channel connected for directory listing.", self.client_id)
        except Exception as e:
            self.reply(R_425_CANT_OPEN_DATA_CONN, f"Cannot open data connection: {e}")
            self.data_mgr.cleanup()
            return

        self.reply(R_150_FILE_STATUS_OK_OPEN_DATA, "Opening ASCII mode data connection for file list.")

        try:
            data_sock.sendall(listing_bytes)
            self.logger.data_event("STRM", f"Transferred {len(listing_bytes)} bytes of directory listing.", self.client_id)
        except Exception as e:
            self.logger.error(f"Error sending directory listing: {e}")
            self.reply(R_426_CONN_CLOSED_TRANSFER_ABORT, "Transfer aborted due to network error.")
            return
        finally:
            try:
                data_sock.close()
                self.logger.data_event("CLSE", "Data channel closed at EOF.", self.client_id)
            except Exception:
                pass
            self.data_mgr.cleanup()

        self.reply(R_226_CLOSING_DATA_CONN_SUCCESS, "Directory send OK.")

    def handle_RETR(self, arg: str):
        """Streams a requested file to the client over the data channel."""
        if not arg:
            self.reply(R_501_SYNTAX_ERROR_IN_PARAMS, "RETR requires filename.")
            return

        try:
            real_path, clean_vpath = self.vfs.resolve(arg)
            if not os.path.exists(real_path) or os.path.isdir(real_path):
                self.reply(R_550_FILE_NOT_FOUND_OR_NO_ACC, f"File not found: {clean_vpath}")
                self.data_mgr.cleanup()
                return
            file_size = os.path.getsize(real_path)
        except Exception as e:
            self.reply(R_550_FILE_NOT_FOUND_OR_NO_ACC, f"File access error: {e}")
            self.data_mgr.cleanup()
            return

        # Connect data socket
        try:
            data_sock = self.data_mgr.open_connection(prot=self.data_prot, ssl_context=self.ssl_context)
            self.logger.data_event("ESTB", f"Data channel connected for RETR {clean_vpath}", self.client_id)
        except Exception as e:
            self.reply(R_425_CANT_OPEN_DATA_CONN, f"Cannot open data connection: {e}")
            self.data_mgr.cleanup()
            return

        mode_str = "BINARY" if self.rep_type == TYPE_IMAGE else "ASCII"
        self.reply(
            R_150_FILE_STATUS_OK_OPEN_DATA,
            f"Opening {mode_str} mode data connection for {clean_vpath} ({file_size} bytes)."
        )

        hasher = hashlib.sha256()
        total_sent = 0
        chunks_count = 0

        try:
            with open(real_path, "rb") as f:
                if self.rest_offset > 0:
                    f.seek(self.rest_offset)
                    self.logger.info(f"Resumed transfer from byte offset {self.rest_offset}")
                    self.rest_offset = 0
                RATE_LIMIT_BYTES_PER_SEC = 1048576

                while True:
                    start_time = time.time()
                    chunk = f.read(BUFFER_SIZE)
                    if not chunk:
                        break
                    data_sock.sendall(chunk)
                    hasher.update(chunk)
                    total_sent += len(chunk)
                    chunks_count += 1
                    elapsed_time = time.time() - start_time 
                    expected_time = len(chunk) / RATE_LIMIT_BYTES_PER_SEC
                    if expected_time > elapsed_time:
                        time.sleep(expected_time - elapsed_time)

            self.logger.data_event(
                "STRM",
                f"Streamed {total_sent} bytes in {chunks_count} chunks ({BUFFER_SIZE} B/chunk).",
                self.client_id
            )
        except Exception as e:
            self.logger.error(f"Error streaming RETR file: {e}")
            self.reply(R_426_CONN_CLOSED_TRANSFER_ABORT, f"Transfer aborted: {e}")
            return
        finally:
            try:
                data_sock.close()
                self.logger.data_event("CLSE", "Data channel closed at EOF.", self.client_id)
            except Exception:
                pass
            self.data_mgr.cleanup()

        sha256_hex = hasher.hexdigest()
        self.reply(
            R_226_CLOSING_DATA_CONN_SUCCESS,
            f"Transfer complete. {total_sent} bytes sent. SHA-256: {sha256_hex}"
        )

    def handle_STOR(self, arg: str):
        """Receives a file uploaded from the client over the data channel."""
        self._receive_file(arg, append=False)

    def handle_APPE(self, arg: str):
        """Appends uploaded data to an existing or new file."""
        self._receive_file(arg, append=True)

    def _receive_file(self, filename: str, append: bool = False):
        if not filename:
            self.reply(R_501_SYNTAX_ERROR_IN_PARAMS, "Filename required.")
            return
        if self.current_user and self.current_user.read_only:
            self.reply(R_550_FILE_NOT_FOUND_OR_NO_ACC, "Permission denied: read-only user.")
            return
        if self.current_user:
            user_sandbox_dir = f"storage/server_root/{self.current_user.username}"
            user_quota = 52428800 # 50 MB
            current_usage = get_dir_size(user_sandbox_dir)
            if current_usage >= user_quota:
                self.reply(552, "Exceeded storage allocation")
                return
        try:
            real_path, clean_vpath = self.vfs.resolve(filename)
        except Exception as e:
            self.reply(R_550_FILE_NOT_FOUND_OR_NO_ACC, f"Invalid destination path: {e}")
            self.data_mgr.cleanup()
            return

        try:
            data_sock = self.data_mgr.open_connection(prot=self.data_prot, ssl_context=self.ssl_context)
            self.logger.data_event("ESTB", f"Data channel connected for RETR {clean_vpath}", self.client_id)
        except Exception as e:
            self.reply(R_425_CANT_OPEN_DATA_CONN, f"Cannot open data connection: {e}")
            self.data_mgr.cleanup()
            return

        mode_str = "BINARY" if self.rep_type == TYPE_IMAGE else "ASCII"
        self.reply(
            R_150_FILE_STATUS_OK_OPEN_DATA,
            f"Opening {mode_str} mode data connection for {clean_vpath}."
        )

        hasher = hashlib.sha256()
        total_recv = 0
        chunks_count = 0
        open_mode = "ab" if append else "wb"

        try:
            with open(real_path, open_mode) as f:
                while True:
                    chunk = data_sock.recv(BUFFER_SIZE)
                    if not chunk:
                        break  # EOF received
                    f.write(chunk)
                    hasher.update(chunk)
                    total_recv += len(chunk)
                    chunks_count += 1

            self.logger.data_event(
                "STRM",
                f"Received {total_recv} bytes in {chunks_count} chunks ({BUFFER_SIZE} B/chunk).",
                self.client_id
            )
        except Exception as e:
            self.logger.error(f"Error receiving file: {e}")
            self.reply(R_426_CONN_CLOSED_TRANSFER_ABORT, f"Transfer aborted: {e}")
            return
        finally:
            try:
                data_sock.close()
                self.logger.data_event("CLSE", "Data channel closed at EOF.", self.client_id)
            except Exception:
                pass
            self.data_mgr.cleanup()

        sha256_hex = hasher.hexdigest()
        self.reply(
            R_226_CLOSING_DATA_CONN_SUCCESS,
            f"Transfer complete. {total_recv} bytes received. SHA-256: {sha256_hex}"
        )

    def handle_AUTH(self, arg: str):
        if arg.strip().upper() == "TLS":
            if not getattr(self, 'ssl_context', None):
                self.reply(504, "TLS not configured on server.")
                return
            
            self.reply(234, "AUTH TLS OK. Initiating TLS negotiation.")
            try:
                # Upgrade the raw socket to an SSL socket
                self.sock = self.ssl_context.wrap_socket(self.sock, server_side=True)
                self.logger.success(f"Control channel upgraded to TLS for {self.client_id}")
            except Exception as e:
                self.logger.error(f"TLS Negotiation failed: {e}")
                self.is_running = False
        else:
            self.reply(504, f"AUTH {arg} not supported.")

    def handle_PBSZ(self, arg: str):
        # RFC 4217 requires the client to send PBSZ 0 before PROT
        self.reply(200, "PBSZ set to 0.")

    def handle_PROT(self, arg: str):
        mode = arg.strip().upper()
        if mode == "C":
            self.data_prot = "C"
            self.reply(200, "Data channel protection set to Cleartext.")
        elif mode == "P":
            self.data_prot = "P"
            self.reply(200, "Data channel protection set to Private (TLS).")
        else:
            self.reply(504, "PROT mode not supported.")

def get_dir_size(directory_path):
    total_size = 0
# rglob('*') recursively finds all files and folders
    for filepath in Path(directory_path).rglob('*'):
        if filepath.is_file():
            total_size += filepath.stat().st_size
    return total_size