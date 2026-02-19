import hashlib
import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

if not ENCRYPTION_KEY:
    raise RuntimeError(
        "ENCRYPTION_KEY não configurada. "
        "Gere uma com: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\" "
        "e adicione como variável de ambiente no Render."
    )

cipher_suite = Fernet(ENCRYPTION_KEY.encode())

def encrypt_cpf(cpf: str) -> str:
    if not cpf:
        return None
    clean_cpf = "".join(filter(str.isdigit, cpf))
    if not clean_cpf:
        return None
    return cipher_suite.encrypt(clean_cpf.encode()).decode()

def decrypt_cpf(encrypted_cpf: str) -> str:
    if not encrypted_cpf:
        return None
    try:
        return cipher_suite.decrypt(encrypted_cpf.encode()).decode()
    except Exception as e:
        print(f"Erro ao descriptografar CPF: {e}")
        return None

def hash_ip(ip_address: str) -> str:
    if not ip_address:
        return None
    return hashlib.sha256(ip_address.encode()).hexdigest()
