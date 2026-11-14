"""
Data Channel Manager for RFC 959 FTP Server.
Implements Active (PORT) and Passive (PASV) modes using raw TCP sockets.
"""

import socket
from typing import Tuple, Optional


class DataChannelManager:
    """Manages the lifecycle of ephemeral data connection sockets."""

    MODE_NONE = "NONE"
    MODE_ACTIVE = "ACTIVE"
    MODE_PASSIVE = "PASSIVE"

    def __init__(self, server_host: str = "127.0.0.1", timeout: float = 30.0):
        self.server_host = server_host
        self.timeout = timeout
        self.mode = self.MODE_NONE

        # Active mode target
        self.active_host: Optional[str] = None
        self.active_port: Optional[int] = None

        # Passive mode listener
        self.pasv_listener: Optional[socket.socket] = None
        self.pasv_port: Optional[int] = None

    def set_active(self, host: str, port: int):
        """Configures active mode with target client host and port."""
        self.cleanup()
        self.mode = self.MODE_ACTIVE
        self.active_host = host
        self.active_port = port

    def setup_passive(self, advertise_ip: Optional[str] = None) -> Tuple[str, int]:
        """
        Creates an ephemeral listening TCP socket for passive mode.
        Returns: (advertise_ip, ephemeral_port)
        """
        self.cleanup()
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.settimeout(self.timeout)

        # Bind to 0 to let OS select an available high port
        bind_ip = "0.0.0.0"
        listener.bind((bind_ip, 0))
        listener.listen(1)

        _, assigned_port = listener.getsockname()
        self.pasv_listener = listener
        self.pasv_port = assigned_port
        self.mode = self.MODE_PASSIVE

        # Determine advertised IP
        pub_ip = advertise_ip or self.server_host
        if pub_ip == "0.0.0.0":
            pub_ip = "127.0.0.1"

        return pub_ip, assigned_port

    def open_connection(self, prot: str = "C", ssl_context = None) -> socket.socket:
        """Establishes and returns the active or passive data socket."""
        if self.mode == "ACTIVE":
            # ... existing active mode code ...
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.settimeout(30.0)
            conn.connect((self.active_host, self.active_port))
            
        elif self.mode == "PASSIVE":
            # FIXED: Changed passive_listener to pasv_listener to match Mandeep's code
            conn, addr = self.pasv_listener.accept()
            conn.settimeout(30.0)
            self.pasv_listener.close()
            self.pasv_listener = None
            
        else:
            raise RuntimeError("Data channel mode not configured.")
            
        # --- NEW ENCRYPTION LOGIC (Applied just once at the very end!) ---
        if prot == "P" and ssl_context:
            conn = ssl_context.wrap_socket(conn, server_side=True)
            
        return conn

    def cleanup(self):
        """Closes any open passive listeners and resets data channel state."""
        if self.pasv_listener:
            try:
                self.pasv_listener.close()
            except Exception:
                pass
            self.pasv_listener = None
        self.pasv_port = None
        self.active_host = None
        self.active_port = None
        self.mode = self.MODE_NONE

