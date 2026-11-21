"""Token encryption at rest (Fernet / AES-128-CBC + HMAC) and password hashing (bcrypt)."""
from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings

import bcrypt


def _fernet() -> Fernet:
    return Fernet(get_settings().token_encryption_key.encode())


def encrypt_token(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:  # key rotated or data corrupted: fail loudly
        raise ValueError("Stored token could not be decrypted. Reconnect the platform.") from exc


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode()[:72], hashed.encode())
    except ValueError:
        return False
