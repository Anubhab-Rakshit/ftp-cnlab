"""
Multi-threaded RFC 959 FTP Server Daemon.
"""

import argparse
import os
import socket
import sys
import threading
import ssl
from typing import List


from common.logger import WireLogger
from common.rfc959 import DEFAULT_FTP_CONTROL_PORT
from server.auth import AuthManager
from server.session import FTPSession


class FTPServer:
    """Multi-client TCP Server coordinating control sockets and client threads."""

    def __init__(self, host: str = "0.0.0.0", port: int = DEFAULT_FTP_CONTROL_PORT, root_dir: str = "storage/server_root"):
        self.host = host
        self.port = port
        self.root_dir = os.path.realpath(os.path.abspath(root_dir))
        os.makedirs(self.root_dir, exist_ok=True)

        self.auth_mgr = AuthManager()
        self.logger = WireLogger(prefix="SERVER", show_wire=True)
        self.server_sock: socket.socket = None
        self.is_running = False
        self.active_sessions: List[FTPSession] = []
        self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        try:
            self.ssl_context.load_cert_chain(certfile="server.crt", keyfile="server.key")
            self.logger.info("SSL Certificate loaded successfully. Ready for FTPS.")
        except Exception as e:
            self.logger.warn(f"Could not load SSL certs. FTPS will be disabled: {e}")
            self.ssl_context = None

    def start(self):
        """Starts the server listening loop."""
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self.server_sock.bind((self.host, self.port))
        except OSError as e:
            self.logger.error(f"Failed to bind {self.host}:{self.port} - {e}")
            sys.exit(1)

        self.server_sock.listen(10)
        self.is_running = True

        self.logger.success("=========================================================")
        self.logger.success("   RFC 959 Multi-Threaded Pure Socket FTP Server")
        self.logger.success(f"   Listening on: {self.host}:{self.port}")
        self.logger.success(f"   Root Sandbox: {self.root_dir}")
        self.logger.success("   Active Mode (PORT) & Passive Mode (PASV) Supported")
        self.logger.success("   NVT/ASCII Control Inspector Enabled")
        self.logger.success("=========================================================")

        try:
            while self.is_running:
                try:
                    client_sock, client_addr = self.server_sock.accept()
                except socket.error:
                    if not self.is_running:
                        break
                    continue

                session = FTPSession(
                    ctrl_socket=client_sock,
                    client_addr=client_addr,
                    root_dir=self.root_dir,
                    auth_mgr=self.auth_mgr,
                    logger=self.logger,
                )
                self.active_sessions.append(session)

                t = threading.Thread(
                    target=self._session_wrapper,
                    args=(session,),
                    daemon=True,
                    name=f"Client-{client_addr[0]}:{client_addr[1]}"
                )
                t.start()

        except KeyboardInterrupt:
            self.logger.info("Shutdown signal received (Ctrl+C).")
        finally:
            self.stop()

    def _session_wrapper(self, session: FTPSession):
        try:
            session.run()
        finally:
            if session in self.active_sessions:
                self.active_sessions.remove(session)

    def stop(self):
        """Stops the server gracefully."""
        self.is_running = False
        self.logger.info("Stopping FTP server...")
        for s in list(self.active_sessions):
            s.cleanup()
        if self.server_sock:
            try:
                self.server_sock.close()
            except Exception:
                pass
        self.logger.success("FTP Server stopped cleanly.")


def main():
    parser = argparse.ArgumentParser(description="RFC 959 Compliant Pure Socket FTP Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=DEFAULT_FTP_CONTROL_PORT, help=f"Control port (default: {DEFAULT_FTP_CONTROL_PORT})")
    parser.add_argument("--root", default="storage/server_root", help="Root directory for VFS sandbox")
    args = parser.parse_args()

    server = FTPServer(host=args.host, port=args.port, root_dir=args.root)
    server.start()


if __name__ == "__main__":
    main()

