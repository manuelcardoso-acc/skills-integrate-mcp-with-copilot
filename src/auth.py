import hashlib
import json
import secrets
import time
from dataclasses import dataclass, field
from typing import Literal


Role = Literal["student", "staff", "administrator"]
PASSWORD_ITERATIONS = 310_000
SESSION_LIFETIME_SECONDS = 8 * 60 * 60


@dataclass
class User:
    username: str
    email: str
    role: Role
    password_hash: str
    activities: set[str] = field(default_factory=set)


@dataclass
class Session:
    username: str
    expires_at: float


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, digest_text = encoded_hash.split("$")
        iterations = int(iterations_text)
        salt = bytes.fromhex(salt_text)
        expected_digest = bytes.fromhex(digest_text)
    except (AttributeError, ValueError):
        return False

    if (
        algorithm != "pbkdf2_sha256"
        or not 100_000 <= iterations <= 1_000_000
        or len(salt) != 16
        or len(expected_digest) != 32
    ):
        return False

    actual_digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    return secrets.compare_digest(actual_digest, expected_digest)


class AuthManager:
    def __init__(self, users: list[User] | None = None):
        self.users: dict[str, User] = {}
        self.sessions: dict[str, Session] = {}
        self._dummy_password_hash = hash_password(secrets.token_urlsafe(32))

        for user in users or []:
            self.add_user(user)

    @classmethod
    def from_environment(cls) -> "AuthManager":
        import os

        raw_users = os.getenv("APP_USERS_JSON", "[]")
        try:
            configured_users = json.loads(raw_users)
        except json.JSONDecodeError as error:
            raise RuntimeError("APP_USERS_JSON must contain a JSON array") from error

        if not isinstance(configured_users, list):
            raise RuntimeError("APP_USERS_JSON must contain a JSON array")

        users = []
        for configured_user in configured_users:
            if not isinstance(configured_user, dict):
                raise RuntimeError("Each APP_USERS_JSON entry must be an object")

            try:
                username = configured_user["username"]
                email = configured_user["email"]
                role = configured_user["role"]
                password_hash = configured_user["password_hash"]
                activities = configured_user.get("activities", [])
            except KeyError as error:
                raise RuntimeError(
                    f"APP_USERS_JSON entry is missing {error.args[0]}"
                ) from error

            if (
                not isinstance(username, str)
                or not username
                or not isinstance(email, str)
                or not email
                or role not in ("student", "staff", "administrator")
                or not isinstance(password_hash, str)
                or not cls._is_valid_password_hash(password_hash)
                or not isinstance(activities, list)
                or any(not isinstance(activity, str) for activity in activities)
            ):
                raise RuntimeError("APP_USERS_JSON contains an invalid user entry")

            users.append(
                User(
                    username=username,
                    email=email,
                    role=role,
                    password_hash=password_hash,
                    activities=set(activities),
                )
            )

        return cls(users)

    @staticmethod
    def _is_valid_password_hash(encoded_hash: str) -> bool:
        try:
            algorithm, iterations_text, salt_text, digest_text = encoded_hash.split("$")
            iterations = int(iterations_text)
            salt = bytes.fromhex(salt_text)
            digest = bytes.fromhex(digest_text)
        except (AttributeError, ValueError):
            return False
        return (
            algorithm == "pbkdf2_sha256"
            and 100_000 <= iterations <= 1_000_000
            and len(salt) == 16
            and len(digest) == 32
        )

    def add_user(self, user: User) -> None:
        key = user.username.casefold()
        if key in self.users:
            raise ValueError("Username already exists")
        if any(
            existing.email.casefold() == user.email.casefold()
            for existing in self.users.values()
        ):
            raise ValueError("Email already exists")
        if not self._is_valid_password_hash(user.password_hash):
            raise ValueError("Invalid password hash")
        self.users[key] = user

    def create_user(
        self,
        username: str,
        email: str,
        role: Role,
        password: str,
        activities: set[str] | None = None,
    ) -> User:
        user = User(
            username=username,
            email=email,
            role=role,
            password_hash=hash_password(password),
            activities=activities or set(),
        )
        self.add_user(user)
        return user

    def login(self, username: str, password: str) -> str | None:
        user = self.users.get(username.casefold())
        password_hash = user.password_hash if user else self._dummy_password_hash
        if not verify_password(password, password_hash) or user is None:
            return None

        token = secrets.token_urlsafe(32)
        token_key = hashlib.sha256(token.encode("ascii")).hexdigest()
        self.sessions[token_key] = Session(
            username=user.username,
            expires_at=time.time() + SESSION_LIFETIME_SECONDS,
        )
        return token

    def authenticate(self, token: str) -> User | None:
        token_key = hashlib.sha256(token.encode("utf-8")).hexdigest()
        session = self.sessions.get(token_key)
        if session is None:
            return None
        if session.expires_at <= time.time():
            del self.sessions[token_key]
            return None
        return self.users.get(session.username.casefold())

    def logout(self, token: str) -> None:
        token_key = hashlib.sha256(token.encode("utf-8")).hexdigest()
        self.sessions.pop(token_key, None)

    def public_user(self, user: User) -> dict[str, object]:
        return {
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "activities": sorted(user.activities),
        }
