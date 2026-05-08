import os
import json
from pathlib import Path
from .rsa_core import encrypt, decrypt


def _read_dotenv_value(key_name):
    # Read a single value from the repository .env file if it exists
    env_path = Path(__file__).resolve().parent.parent / '.env'
    if not env_path.exists():
        return None

    try:
        lines = env_path.read_text(encoding='utf-8').splitlines()
    except Exception:
        return None

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith('#') or '=' not in stripped:
            continue
        name, value = stripped.split('=', 1)
        if name.strip() == key_name:
            return value.strip()
    return None


def _load_server_keys_from_env():
    # Load the server's RSA public and private keys from environment variables or .env file.
    pub_raw = os.environ.get('SERVER_RSA_PUBLIC_KEY') or _read_dotenv_value('SERVER_RSA_PUBLIC_KEY')
    priv_raw = os.environ.get('SERVER_RSA_PRIVATE_KEY') or _read_dotenv_value('SERVER_RSA_PRIVATE_KEY')
    
    # Fallback to Django settings if env vars not found
    if not pub_raw or not priv_raw:
        try:
            from django.conf import settings
            pub_raw = pub_raw or getattr(settings, 'SERVER_RSA_PUBLIC_KEY', None)
            priv_raw = priv_raw or getattr(settings, 'SERVER_RSA_PRIVATE_KEY', None)
        except Exception:
            pass
    
    if not pub_raw or not priv_raw:
        return None, None
    try:
        pub = tuple(json.loads(pub_raw)) if isinstance(pub_raw, str) else pub_raw
        priv = tuple(json.loads(priv_raw)) if isinstance(priv_raw, str) else priv_raw
        return pub, priv
    except Exception:
        return None, None


def wrap_user_private_key(user_private_key):
    # Encrypt (wrap) the user's RSA private key using the server public key.
    server_pub, _ = _load_server_keys_from_env()
    if not server_pub:
        raise RuntimeError('Server public key not configured in environment')
    
    # serialize the private key (tuple) into JSON string
    payload = json.dumps(list(user_private_key))
    ciphertext = encrypt(server_pub, payload)
    return ciphertext


def unwrap_user_private_key(encrypted_array):
    # Decrypt (unwrap) the user's RSA private key using the server private key.
    _, server_priv = _load_server_keys_from_env()
    if not server_priv:
        raise RuntimeError('Server private key not configured in environment')

    # If passed as JSON string, parse it
    if isinstance(encrypted_array, str):
        try:
            encrypted = json.loads(encrypted_array)
        except Exception:
            raise
    else:
        encrypted = encrypted_array

    decrypted = decrypt(server_priv, encrypted)
    # decrypted JSON list like [d, n]
    try:
        arr = json.loads(decrypted)
        return tuple(arr)
    except Exception:
        raise
