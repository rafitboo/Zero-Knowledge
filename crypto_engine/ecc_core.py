import random


# 1. CURVE PARAMETERS (secp256k1 standard)
# Equation: y^2 = x^3 + ax + b (mod P)
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
A = 0
B = 7


# G is the base "Generator" point (x, y)
G = (
    0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
    0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
)


# N is the order of the curve
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141



# 2. MODULAR ARITHMETIC UTILITIES

def mod_inverse(k, p):
    # Finds the modular inverse using Fermat's Little Theorem or Extended Euclidean
    if k == 0:
        raise ZeroDivisionError('Division by zero')
    if k < 0:
        return p - mod_inverse(-k, p)
    return pow(k, p - 2, p)



# 3. ELLIPTIC CURVE POINT MATH
def point_add(point1, point2):
    # Adds two points on the elliptic curve.
    if point1 is None: return point2
    if point2 is None: return point1

    x1, y1 = point1
    x2, y2 = point2

    if x1 == x2 and y1 != y2:
        return None # Point at infinity

    if x1 == x2:
        # Point Doubling (Tangent line)
        m = (3 * x1 * x1 + A) * mod_inverse(2 * y1, P)
    else:
        # Point Addition (Secant line)
        m = (y1 - y2) * mod_inverse(x1 - x2, P)

    x3 = (m * m - x1 - x2) % P
    y3 = (y1 + m * (x3 - x1)) % P
    
    # We reflect across the x-axis
    return (x3, (P - y3) % P)

def scalar_multiply(k, point):
    # Multiplies a point by an integer k using the 'Double-and-Add' algorithm.
    # This is the core of ECC cryptography (fast to do, impossible to reverse).
    result = None
    addend = point

    while k:
        if k & 1:
            result = point_add(result, addend)
        addend = point_add(addend, addend)
        k >>= 1

    return result


# 4. ECC KEY GENERATION

def generate_ecc_keypair():
    # Generates an ECC Private Key (random integer) and Public Key (Point on curve).
    # Private key is a random integer between 1 and N-1
    private_key = random.randrange(1, N)
    
    # Public key is the Generator point multiplied by the private key
    public_key = scalar_multiply(private_key, G)
    
    return public_key, private_key


# 5. ASYMMETRIC ENCRYPTION (ElGamal over ECC)

def encrypt_post(public_key, plaintext):
    
    # Encrypts a string strictly using asymmetric ECC.
    # We map each character to a ciphertext pair (C1, C2) using a random ephemeral key.

    ciphertext_array = []
    
    for char in plaintext:
        m = ord(char)
        # 1. Choose a random ephemeral key 'k' for this specific character
        k = random.randrange(1, N)
        
        # 2. C1 = k * G
        C1 = scalar_multiply(k, G)
        
        # 3. Shared Secret Point = k * Public_Key
        shared_secret = scalar_multiply(k, public_key)
        
        # 4. C2 = Message * x-coordinate of shared secret (mod P)
        C2 = (m * shared_secret[0]) % P
        
        ciphertext_array.append((C1, C2))
        
    return ciphertext_array

def decrypt_post(private_key, ciphertext_array):
    # Decrypts the ECC ciphertext array back to the original string.
    plaintext = ""
    
    for C1, C2 in ciphertext_array:
        # 1. Reconstruct the shared secret: Private_Key * C1
        shared_secret = scalar_multiply(private_key, C1)
        
        # 2. Recover message: m = C2 / x-coordinate of shared secret (mod P)
        m = (C2 * mod_inverse(shared_secret[0], P)) % P
        
        plaintext += chr(m)
        
    return plaintext


# 6. TERMINAL TEST
if __name__ == "__main__":
    print("Generating ECC Key Pair...")
    pub_key, priv_key = generate_ecc_keypair()
    
    print(f"\nPublic Key (Point on Curve):\n  X = {pub_key[0]}\n  Y = {pub_key[1]}")
    print(f"\nPrivate Key (Integer):\n  d = {priv_key}")
    
    message = "Classified Feed Update!"
    print(f"\n--- TESTING ECC ASYMMETRIC ENCRYPTION ---")
    print(f"Original: {message}")
    
    encrypted = encrypt_post(pub_key, message)
    print(f"\nEncrypted (First character pair C1, C2 shown):\n  C1: {encrypted[0][0]}\n  C2: {encrypted[0][1]}")
    
    decrypted = decrypt_post(priv_key, encrypted)
    print(f"\nDecrypted: {decrypted}")
    
    if message == decrypted:
        print("\n✅ SUCCESS! The ECC math works.")