"""
User authentication and permission management for the FTP server.
"""

from typing import Optional, Dict


class UserAccount:
    def __init__(self, username: str, password: Optional[str], read_only: bool = False, home_dir: str = "/"):
        self.username = username
        self.password = password  # None means any password accepted (e.g. anonymous)
        self.read_only = read_only
        self.home_dir = home_dir

    USER_DB = {
    "mandeep": {
        "password": "password123",
        "quota_bytes": 52428800  # 50 MB
    },
    "soumyadip": {
        "password": "secure",
        "quota_bytes": 52428800  # 50 MB
    }
}


class AuthManager:
    """Manages user authentication and permissions."""

    def __init__(self):
        self._users: Dict[str, UserAccount] = {}
        # Prepopulate default users:
        # 1. Anonymous user with read-only permission
        self.add_user(UserAccount("anonymous", password=None, read_only=False, home_dir="/"))
        self.add_user(UserAccount("guest", password=None, read_only=False, home_dir="/"))
        # 2. Authenticated user with full read-write permission
        self.add_user(UserAccount("admin", password="password123", read_only=False, home_dir="/"))
        self.add_user(UserAccount("student", password="cnlab", read_only=False, home_dir="/"))

    def add_user(self, account: UserAccount):
        self._users[account.username.lower()] = account

    def user_exists(self, username: str) -> bool:
        return username.lower() in self._users

    def verify_password(self, username: str, password: str) -> Optional[UserAccount]:
        user = self._users.get(username.lower())
        if not user:
            return None
        # If password is None, anonymous access is allowed
        if user.password is None:
            return user
        if user.password == password:
            return user
        return None

USER_DB = {
    "mandeep": {
        "password": "password123",
        "quota_bytes": 52428800  # 50 MB
    },
    "soumyadip": {
        "password": "secure",
        "quota_bytes": 52428800  # 50 MB
    }
}