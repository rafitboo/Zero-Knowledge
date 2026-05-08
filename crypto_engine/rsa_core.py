import random

# 1. PRIME NUMBER GENERATION (Miller-Rabin Primality Test)
def is_prime(n, k=40):
    
    # Tests if a number is prime using the Miller-Rabin algorithm.
    # k is the number of rounds of testing to perform.
    if n == 2 or n == 3:
        return True
    if n <= 1 or n % 2 == 0:
        return False

    # Find r and d such that n - 1 = 2^r * d
    r, d = 0, n - 1
    while d % 2 == 0:
        r += 1
        d //= 2

    # Perform k rounds of testing
    for _ in range(k):
        a = random.randrange(2, n - 1)
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True

def generate_large_prime(keysize=512):
    # Generates a random prime number of the specified bit length
    while True:
        # Generate a random odd number of the given bit length
        num = random.randrange(2**(keysize-1) + 1, 2**keysize - 1, 2)
        if is_prime(num):
            return num

# 2. MODULAR ARITHMETIC UTILITIES

def gcd(a, b):
    # Euclidean algorithm to find the greatest common divisor
    while b != 0:
        a, b = b, a % b
    return a

def multiplicative_inverse(e, phi):
    
    # Extended Euclidean Algorithm to find the modular inverse (d).
    # This ensures that (e * d) % phi == 1
    
    old_r, r = e, phi
    old_s, s = 1, 0
    
    while r != 0:
        quotient = old_r // r
        old_r, r = r, old_r - quotient * r
        old_s, s = s, old_s - quotient * s
        
    if old_s < 0:
        old_s += phi
        
    return old_s


# 3. RSA KEY PAIR GENERATION

def generate_keypair(keysize=512):
    # Generates the Public and Private keys for RSA encryption.
    # 1. Generate two distinct large primes, p and q
    p = generate_large_prime(keysize)
    q = generate_large_prime(keysize)
    
    # Ensure they aren't the same (extremely rare, but mathematically required)
    while p == q:
        q = generate_large_prime(keysize)
        
    # 2. Calculate n (the modulus)
    n = p * q
    
    # 3. Calculate Euler's Totient Function, phi(n)
    phi = (p - 1) * (q - 1)
    
    # 4. Choose an integer e such that 1 < e < phi and gcd(e, phi) = 1
    # Commonly, 65537 is used, but we'll generate it randomly to be fully "from scratch"
    e = random.randrange(2, phi)
    g = gcd(e, phi)
    while g != 1:
        e = random.randrange(2, phi)
        g = gcd(e, phi)
        
    # 5. Calculate d, the modular inverse of e
    d = multiplicative_inverse(e, phi)
    
    # Return Public Key (e, n) and Private Key (d, n)
    return ((e, n), (d, n))



# 4. ENCRYPTION & DECRYPTION LOGIC

def encrypt(public_key, plaintext):
    """
    Encrypts a string using the RSA public key.
    Converts each character to its integer value,
    then applies the textbook RSA formula: c = m^e mod n.
    """
    e, n = public_key
    # Convert each character to a number using ord() and encrypt it
    cipher = [pow(ord(char), e, n) for char in plaintext]
    return cipher

def decrypt(private_key, ciphertext):
    """
    Decrypts an array of integers using the RSA private key.
    Applies the RSA formula: m = c^d mod n, then converts back to characters.
    """
    d, n = private_key
    # Decrypt each number and convert back to a character using chr()
    plain = [chr(pow(char, d, n)) for char in ciphertext]
    return ''.join(plain)



# TERMINAL TEST

if __name__ == "__main__":
    import time
    
    print("Generating RSA Key Pair (This might take a few seconds)...")
    start_time = time.time()
    
    # Use 256-bit primes (512-bit n) to keep terminal generation fast
    public, private = generate_keypair(keysize=256) 
    
    print(f"\n--- KEY PAIR GENERATED in {round(time.time() - start_time, 2)}s ---")
    print(f"Public Key (e, n):\n  e = {public[0]}\n  n = {public[1]}\n")
    print(f"Private Key (d, n):\n  d = {private[0]}\n  n = {private[1]}\n")
    
    # Testing with some sample data
    message = "Dhaka, Bangladesh - Secret Project!"
    print(f"--- TESTING ENCRYPTION ---")
    print(f"Original Message: {message}")
    
    encrypted_msg = encrypt(public, message)
    print(f"\nEncrypted Ciphertext (Array of Integers):\n{encrypted_msg}")
    
    decrypted_msg = decrypt(private, encrypted_msg)
    print(f"\nDecrypted Message: {decrypted_msg}")
    
    if message == decrypted_msg:
        print("\n✅ SUCCESS! The RSA math works perfectly.")
    else:
        print("\n❌ FAILURE! Something went wrong.")