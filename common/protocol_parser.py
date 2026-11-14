"""
Protocol parser for RFC 959 NVT/ASCII framing and address calculations.
"""

import re
from typing import Tuple, Optional, List
from common.rfc959 import TELNET_EOL


def parse_command_line(raw_line: str) -> Tuple[str, str]:
    """
    Parses a raw NVT/ASCII command line into (command, argument).
    Example: 'USER anonymous\r\n' -> ('USER', 'anonymous')
             'LIST\r\n' -> ('LIST', '')
             'CWD /my folder/test\r\n' -> ('CWD', '/my folder/test')
    """
    line = raw_line.rstrip("\r\n")
    if not line:
        return "", ""
    parts = line.split(" ", 1)
    cmd = parts[0].strip().upper()
    arg = parts[1].strip() if len(parts) > 1 else ""
    return cmd, arg


def format_reply(code: int, message: str) -> str:
    """
    Formats a standard single-line RFC 959 reply.
    Example: (220, "Service ready") -> "220 Service ready\r\n"
    """
    return f"{code} {message}{TELNET_EOL}"


def format_multiline_reply(code: int, lines: List[str]) -> str:
    """
    Formats a standard multi-line RFC 959 reply.
    Example:
    211-Features:
     SIZE
     PASV
    211 End\r\n
    """
    if not lines:
        return f"{code} End{TELNET_EOL}"
    out = []
    first = lines[0]
    out.append(f"{code}-{first}")
    for mid in lines[1:-1]:
        out.append(f" {mid}")
    if len(lines) > 1:
        out.append(f"{code} {lines[-1]}")
    else:
        out.append(f"{code} End")
    return TELNET_EOL.join(out) + TELNET_EOL


def parse_reply_line(raw_line: str) -> Tuple[int, str, bool]:
    """
    Parses a reply line from server.
    Returns: (code, message, is_multiline_continuation)
    """
    line = raw_line.rstrip("\r\n")
    if len(line) < 3 or not line[:3].isdigit():
        return 0, line, False
    code = int(line[:3])
    is_multi = False
    if len(line) > 3 and line[3] == "-":
        is_multi = True
        msg = line[4:]
    elif len(line) > 3 and line[3] == " ":
        msg = line[4:]
    else:
        msg = line[3:]
    return code, msg, is_multi


def parse_port_command(arg: str) -> Tuple[str, int]:
    """
    Parses the argument of a PORT command.
    Format: h1,h2,h3,h4,p1,p2
    Returns: (ip_address_str, port_int)
    Raises ValueError if format is invalid.
    """
    parts = [p.strip() for p in arg.split(",")]
    if len(parts) != 6:
        raise ValueError(f"Invalid PORT argument: '{arg}'. Must have 6 comma-separated octets.")
    try:
        octets = [int(p) for p in parts]
    except ValueError:
        raise ValueError(f"Invalid PORT argument: '{arg}'. All octets must be integers.")

    for o in octets:
        if not 0 <= o <= 255:
            raise ValueError(f"Invalid octet value in PORT: {o}")

    ip_str = f"{octets[0]}.{octets[1]}.{octets[2]}.{octets[3]}"
    port = (octets[4] << 8) + octets[5]
    if not 1 <= port <= 65535:
        raise ValueError(f"Calculated port {port} out of range [1, 65535]")

    return ip_str, port


def format_port_command(ip: str, port: int) -> str:
    """
    Encodes an IP and port into PORT argument format: 'h1,h2,h3,h4,p1,p2'
    """
    octets = [str(int(o)) for o in ip.split(".")]
    if len(octets) != 4:
        raise ValueError(f"Invalid IPv4 address: {ip}")
    p1 = (port >> 8) & 0xFF
    p2 = port & 0xFF
    return f"{','.join(octets)},{p1},{p2}"


def format_pasv_reply(ip: str, port: int) -> str:
    """
    Formats the 227 reply for Entering Passive Mode.
    Example: 227 Entering Passive Mode (127,0,0,1,195,84)\r\n
    """
    encoded_addr = format_port_command(ip, port)
    return format_reply(227, f"Entering Passive Mode ({encoded_addr})")


def parse_pasv_reply(reply_message: str) -> Tuple[str, int]:
    """
    Parses a 227 Entering Passive Mode response to extract (ip, port).
    Finds (h1,h2,h3,h4,p1,p2) in message.
    """
    match = re.search(r"\((\d+,\d+,\d+,\d+,\d+,\d+)\)", reply_message)
    if not match:
        # Fallback to finding 6 comma separated numbers
        match = re.search(r"(\d+,\d+,\d+,\d+,\d+,\d+)", reply_message)
    if not match:
        raise ValueError(f"Could not parse IP and port from PASV response: '{reply_message}'")
    return parse_port_command(match.group(1))


def format_epsv_reply(port: int) -> str:
    """
    Formats the RFC 2428 229 Entering Extended Passive Mode reply.
    Format: 229 Entering Extended Passive Mode (|||<port>|)\r\n
    """
    return format_reply(229, f"Entering Extended Passive Mode (|||{port}|)")


def parse_eprt_command(arg: str) -> Tuple[str, int]:
    """
    Parses RFC 2428 EPRT command argument.
    Format: |<net-prt>|<net-addr>|<tcp-port>|
    Example: |1|127.0.0.1|62005|
    """
    if not arg or len(arg) < 3:
        raise ValueError("Invalid EPRT argument")
    delim = arg[0]
    parts = arg.split(delim)
    # Splitting "|1|127.0.0.1|62005|" gives ['', '1', '127.0.0.1', '62005', '']
    if len(parts) < 5:
        raise ValueError(f"Malformed EPRT string: '{arg}'")
    ip_str = parts[2]
    port = int(parts[3])
    return ip_str, port

