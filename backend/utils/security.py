import hashlib
import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

if not ENCRYPTION_KEY:
    raise RuntimeError(
        "ENCRYPTION_KEY não configurada. "
        "Gere com: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
    )

cipher_suite = Fernet(ENCRYPTION_KEY.encode())

def encrypt_cpf(cpf: str) -> str | None:
    if not cpf:
        return None
    clean = "".join(filter(str.isdigit, cpf))
    if not clean:
        return None
    return cipher_suite.encrypt(clean.encode()).decode()

def decrypt_cpf(encrypted_cpf: str) -> str | None:
    if not encrypted_cpf:
        return None
    try:
        return cipher_suite.decrypt(encrypted_cpf.encode()).decode()
    except Exception:
        return None

def hash_ip(ip: str) -> str | None:
    if not ip:
        return None
    return hashlib.sha256(ip.encode()).hexdigest()

def encrypt_aes256(data: str) -> str | None:
    if not data: return None
    return cipher_suite.encrypt(data.encode()).decode()

def decrypt_aes256(encrypted_data: str) -> str | None:
    if not encrypted_data: return None
    try:
        return cipher_suite.decrypt(encrypted_data.encode()).decode()
    except Exception:
        return None
