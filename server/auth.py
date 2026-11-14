"""
User authentication and permission management for the FTP server.
"""

from typing import Optional, Dict

# Central User Database
DEFAULT_QUOTA_BYTES = 52428800  # 50 MB

USER_DB = {
    "anubhab": {
        "password": "password123",
        "quota_bytes": DEFAULT_QUOTA_BYTES,
        "read_only": False,
        "home_dir": "/"
    },
    "susruto": {
        "password": "password123",
        "quota_bytes": DEFAULT_QUOTA_BYTES,
        "read_only": False,
        "home_dir": "/"
    },
    "mandeep": {
        "password": "password123",
        "quota_bytes": DEFAULT_QUOTA_BYTES,
        "read_only": False,
        "home_dir": "/"
    },
    "soumyadip": {
        "password": "secure",
        "quota_bytes": DEFAULT_QUOTA_BYTES,
        "read_only": False,
        "home_dir": "/"
    },
    "admin": {
        "password": "password123",
        "quota_bytes": DEFAULT_QUOTA_BYTES,
        "read_only": False,
        "home_dir": "/"
    },
    "student": {
        "password": "cnlab",
        "quota_bytes": DEFAULT_QUOTA_BYTES,
        "read_only": False,
        "home_dir": "/"
    },
    "anonymous": {
        "password": None,  # None means any password accepted
        "quota_bytes": DEFAULT_QUOTA_BYTES,
        "read_only": False,
        "home_dir": "/"
    },
    "guest": {
        "password": None,
        "quota_bytes": DEFAULT_QUOTA_BYTES,
        "read_only": False,
        "home_dir": "/"
    },
}


class UserAccount:
    def __init__(
        self,
        username: str,
        password: Optional[str],
        read_only: bool = False,
        home_dir: str = "/",
        quota_bytes: int = DEFAULT_QUOTA_BYTES,
    ):
        self.username = username
        self.password = password
        self.read_only = read_only
        self.home_dir = home_dir
        self.quota_bytes = quota_bytes


class AuthManager:
    """Manages user authentication, quotas, and permissions."""

    def __init__(self):
        self._users: Dict[str, UserAccount] = {}
        # Prepopulate users from USER_DB
        for uname, udata in USER_DB.items():
            self.add_user(
                UserAccount(
                    username=uname,
                    password=udata["password"],
                    read_only=udata.get("read_only", False),
                    home_dir=udata.get("home_dir", "/"),
                    quota_bytes=udata.get("quota_bytes", DEFAULT_QUOTA_BYTES),
                )
            )

    def add_user(self, account: UserAccount):
        self._users[account.username.lower()] = account

    def user_exists(self, username: str) -> bool:
        return username.lower() in self._users

    def get_user(self, username: str) -> Optional[UserAccount]:
        return self._users.get(username.lower())

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
