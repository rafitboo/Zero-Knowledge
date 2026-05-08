import hmac
import hashlib

def generate_mac(shared_secret, message):

    # Generates an HMAC-SHA256 tag using Python built-in hmac/hashlib.
    # Requires a shared secret password/key that only trusted parties know.
    
    secret_bytes = shared_secret.encode('utf-8')
    message_bytes = message.encode('utf-8')
    
    # Generate the cryptographic hash
    mac_tag = hmac.new(secret_bytes, message_bytes, hashlib.sha256).hexdigest()
    return mac_tag

def verify_mac(shared_secret, message, provided_mac):

    #Verifies message integrity using constant-time comparison.
    
    expected_mac = generate_mac(shared_secret, message)
    
    # hmac.compare_digest prevents timing attacks during comparison
    return hmac.compare_digest(expected_mac, provided_mac)