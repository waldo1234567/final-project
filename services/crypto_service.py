from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

def encrypt_chunk(chunk_bytes: bytes, data_key: bytes) -> bytes:
    aesgcm = AESGCM(data_key)
    nonce = os.urandom(12)  
    ct = aesgcm.encrypt(nonce, chunk_bytes, None)
    return nonce + ct

def decrypt_chunk(encrypted_chunk: bytes, data_key: bytes) -> bytes:
    aesgcm = AESGCM(data_key)
    nonce = encrypted_chunk[:12]  #
    ct = encrypted_chunk[12:]  
    return aesgcm.decrypt(nonce, ct, None)