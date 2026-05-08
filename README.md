# ZK Network 🛡️

**A Secure Web Application with Hybrid Asymmetric Cryptography and Key Escrow**

ZK Network is a secure, encrypted messaging platform built with Django and Django REST Framework. Developed as a lab project for CSE447 (Cryptography and Cryptanalysis), this system implements complex cryptographic protocols entirely from scratch (using only underlying math primitives) to ensure zero plaintext data at rest.

---

## 🚀 Key Features

* **Server-Trusted Key Escrow:** Users never handle raw cryptographic keys. The server generates, wraps, and securely manages user RSA keypairs using a Master Vault.
* **Hybrid Cryptographic Architecture:** * **Posts:** Multi-cast architecture utilizing bespoke Elliptic Curve Cryptography (ECC) wrapped in an RSA Key Ring for author-only visibility.
  * **Direct Messages (DMs):** Peer-to-peer secure messaging utilizing per-message RSA encryption and server-mediated decryption.
* **Cryptographic Integrity (MAC):** All DMs are protected against database tampering via HMAC-SHA256 tags. Modified ciphertexts gracefully fail to `[MESSAGE CORRUPTED]`.
* **Zero Trust Storage:** The SQLite database contains only serialized ciphertext arrays and hashed passwords.
* **Strict 2FA Enforced:** Secondary Time-Limited Email OTP required before session issuance and key unwrapping.
* **Stateless Sessions:** Custom JWT implementation tied to the authentication lifecycle.
* **Role-Based Access Control (RBAC):** Dedicated Admin Console for system auditing and bulk moderation, without exposing plaintext communications.

---

## 🛠️ Technology Stack

* **Backend:** Python 3.10+, Django 6.0.4, Django REST Framework
* **Database:** SQLite3
* **Cryptography:** Custom engines (`rsa_core`, `ecc_core`, `hash_core`, `mac_core`) utilizing `pycryptodome` strictly for mathematical primitives.
* **Frontend:** HTML5, CSS3 (Bootstrap 5), Vanilla JavaScript

---

## ⚙️ Environment Setup & Installation

### 1. Prerequisites
Ensure you have Python 3.10+ installed on your system.

### 2. Clone the Repository
```bash
git clone [https://github.com/your-username/zk-network.git](https://github.com/your-username/zk-network.git)
cd zk-network


### 3. Initialize Virtual Environment
```bash
python -m venv venv

# Windows:
.\venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install django djangorestframework pycryptodome python-dotenv
```

### 5. Configure the Server Vault (.env)
The application **will not boot** without the Master Key Vault. Create a `.env` file in the root directory (next to `manage.py`) and populate it with your cryptographic secrets:

```ini
# .env
# Master RSA Keys (Must be valid JSON arrays representing the key tuples)
SERVER_RSA_PUBLIC_KEY=[...]
SERVER_RSA_PRIVATE_KEY=[...]

# Secret for MAC Generation and JWT Signing
DM_MAC_SECRET=your-super-secure-random-string
SECRET_KEY=django-insecure-your-secret-key
```
*(Note: If you are setting this up for the first time, you can generate an initial RSA keypair using the `crypto_engine.rsa_core.generate_keypair()` function).*

### 6. Initialize Database
```bash
python manage.py makemigrations
python manage.py migrate
```

---

## 🚀 Running the Application

To start the ZK Network server, run:
```bash
python manage.py runserver
```
The application will be available at `http://127.0.0.1:8000/`.

*(Note: During startup, the custom `verify_vault.py` utility will automatically run a cryptographic loop-test to ensure your `.env` keys are mathematically sound).*

---

## 🔐 Cryptographic Maintenance

### Rotating Master Keys
In the event of an infrastructure upgrade or suspected vault compromise, the system's Master RSA Keys must be rotated. We provide a custom atomic transaction script that seamlessly rotates the keys and re-encrypts all user records, DMs, and Posts without data loss.

Run the rotation protocol:
```bash
python manage.py rotate_master_keys
```
**Important:** Follow the terminal prompts immediately after execution to update your `.env` file with the newly generated keys.



---

## ⚠️ Academic Disclaimer
This project was developed strictly for educational purposes to demonstrate the implementation of cryptographic algorithms from scratch as per university coursework requirements. While the architecture models enterprise-grade key escrow, the underlying mathematical engines have not undergone professional security audits and should **not** be used in a real-world production environment to protect actual sensitive data.
```
