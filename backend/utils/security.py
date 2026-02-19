import hashlib
import os
import base64
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

if not ENCRYPTION_KEY:
    # Generate a key if not present for development, but warn
    print("WARNING: ENCRYPTION_KEY not set. Using a temporary one. DATA LOSS ON RESTART.")
    ENCRYPTION_KEY = Fernet.generate_key().decode()

cipher_suite = Fernet(ENCRYPTION_KEY.encode())

def encrypt_cpf(cpf: str) -> str:
    """Encrypts a CPF string using AES-256 (Fernet)."""
    if not cpf:
        return None
    # Remove non-digits
    clean_cpf = "".join(filter(str.isdigit, cpf))
    if not clean_cpf:
        return None
    encrypted_bytes = cipher_suite.encrypt(clean_cpf.encode())
    return encrypted_bytes.decode()

def decrypt_cpf(encrypted_cpf: str) -> str:
    """Decrypts an encrypted CPF string."""
    if not encrypted_cpf:
        return None
    try:
        decrypted_bytes = cipher_suite.decrypt(encrypted_cpf.encode())
        return decrypted_bytes.decode()
    except Exception as e:
        print(f"Error decrypting CPF: {e}")
        return None

def hash_ip(ip_address: str) -> str:
    """Hashes an IP address using SHA-256 for anonymization."""
    if not ip_address:
        return None
    return hashlib.sha256(ip_address.encode()).hexdigest()
