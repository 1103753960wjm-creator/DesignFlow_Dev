import base64
import hashlib
from pathlib import Path

from cryptography.fernet import Fernet


def _fernet_key_from_secret(secret: str) -> bytes:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_bytes(data: bytes, secret: str) -> bytes:
    return Fernet(_fernet_key_from_secret(secret)).encrypt(data)


def decrypt_bytes(token: bytes, secret: str) -> bytes:
    return Fernet(_fernet_key_from_secret(secret)).decrypt(token)


def read_file_bytes(path: Path) -> bytes:
    return path.read_bytes()


def write_file_bytes(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)

