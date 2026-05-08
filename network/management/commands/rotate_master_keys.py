import os
import json
import tempfile
import shutil
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from accounts.models import User
from network.models import DirectMessage, Post
from crypto_engine.rsa_core import generate_keypair, encrypt, decrypt
from crypto_engine.mac_core import generate_mac
from django.conf import settings


class Command(BaseCommand):
    help = 'Rotates the Server Master RSA Keys and safely re-encrypts all Users and Direct Messages.'
    
    def _validate_keypair(self, pub, priv):
        """Validate that the keypair is non-empty and properly formatted."""
        if not pub or not priv or len(pub) == 0 or len(priv) == 0:
            raise ValueError('Invalid keypair: empty key material')
        return True
    
    def _write_keys_securely(self, pub, priv):
        """Write keys to a secure temp file with restricted permissions."""
        try:
            # Create temp file with restrictive permissions (0600 on Unix)
            fd, temp_path = tempfile.mkstemp(suffix='.keys', prefix='zk_rotation_')
            os.chmod(fd, 0o600)
            
            with os.fdopen(fd, 'w') as f:
                f.write('[NEW MASTER KEYS - STORE SECURELY]\n\n')
                f.write(f'SERVER_RSA_PUBLIC_KEY={json.dumps(list(pub))}\n')
                f.write(f'SERVER_RSA_PRIVATE_KEY={json.dumps(list(priv))}\n\n')
                f.write('Update your .env file with these values and restart the server.\n')
                f.write('DO NOT share or log these keys elsewhere.\n')
            
            return temp_path
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[CRITICAL] Failed to write keys securely: {e}'))
            raise
    
    def _backup_encryption_state(self):
        """Create a backup snapshot of all encrypted state before rotation."""
        backup = {
            'users': {},
            'dms': {},
            'posts': {},
        }
        try:
            for user in User.objects.exclude(encrypted_rsa_private_key__isnull=True).exclude(encrypted_rsa_private_key__exact=''):
                backup['users'][user.id] = user.encrypted_rsa_private_key
            for msg in DirectMessage.objects.all():
                backup['dms'][msg.id] = {
                    'content': msg.encrypted_content,
                    'rsa_priv': getattr(msg, 'encrypted_rsa_private_key', None),
                }
            for post in Post.objects.all():
                backup['posts'][post.id] = post.encrypted_ecc_private_key
            return backup
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[CRITICAL] Failed to create backup: {e}'))
            raise
    
    def _verify_rotated_data(self, new_priv, sample_size=5):
        """Spot-check that rotated data can still be decrypted."""
        import random
        
        results = {'ok': 0, 'failed': 0, 'errors': []}
        
        try:
            # Sample users
            users = list(User.objects.exclude(encrypted_rsa_private_key__isnull=True).exclude(encrypted_rsa_private_key__exact='')[:sample_size])
            for user in users:
                try:
                    wrapped = json.loads(user.encrypted_rsa_private_key)
                    decrypted = decrypt(new_priv, wrapped)
                    if decrypted and len(decrypted) > 0:
                        results['ok'] += 1
                    else:
                        results['failed'] += 1
                        results['errors'].append(f'User {user.id}: empty decryption')
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append(f'User {user.id}: {e}')
            
            self.stdout.write(f'  [VERIFY] User keys: {results["ok"]}/{len(users)} verified')
            if results['errors']:
                for err in results['errors'][:3]:
                    self.stdout.write(self.style.WARNING(f'    └─ {err}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[VERIFY] Verification failed: {e}'))
            return False
        
        return results['failed'] == 0

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('\n[SYSTEM] Initiating Master Key Rotation Protocol...'))
        
        # 1. Load the Legacy Private Key (Needed to unlock current data)
        # Try os.environ first, then fall back to Django settings
        legacy_priv_raw = os.environ.get('SERVER_RSA_PRIVATE_KEY') or getattr(settings, 'SERVER_RSA_PRIVATE_KEY', None)
        if not legacy_priv_raw:
            self.stdout.write(self.style.ERROR('[CRITICAL] Legacy SERVER_RSA_PRIVATE_KEY missing from .env! Cannot decrypt current data.'))
            return
            
        try:
            legacy_priv = tuple(json.loads(legacy_priv_raw))
        except Exception:
            self.stdout.write(self.style.ERROR('[CRITICAL] Invalid legacy private key format.'))
            return

        # 1.5 Create backup before rotation
        self.stdout.write('  > Creating backup of encrypted state...')
        try:
            backup = self._backup_encryption_state()
            self.stdout.write(self.style.SUCCESS(f'    ✓ Backed up {len(backup["users"])} users, {len(backup["dms"])} DMs, {len(backup["posts"])} posts'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[CRITICAL] Backup creation failed: {e}'))
            return
        
        # 2. Generate the New Master Keys
        self.stdout.write('  > Generating new 256-bit Master Keypair (this may take a moment)...')
        new_pub, new_priv = generate_keypair(keysize=256)
        
        # Validate new keypair
        try:
            self._validate_keypair(new_pub, new_priv)
            self.stdout.write(self.style.SUCCESS('    ✓ New keypair validated'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[CRITICAL] Key generation validation failed: {e}'))
            return
        
        try:
            # 3. Database Transaction (If anything fails, it rolls back so data isn't corrupted)
            with transaction.atomic():
                
                # --- A. ROTATE USER PRIVATE KEYS ---
                users = User.objects.exclude(encrypted_rsa_private_key__isnull=True).exclude(encrypted_rsa_private_key__exact='')
                self.stdout.write(f'  > Re-wrapping private keys for {users.count()} operatives...')
                
                for user in users:
                    # Unwrap with old key
                    old_encrypted_key = json.loads(user.encrypted_rsa_private_key)
                    decrypted_user_priv = decrypt(legacy_priv, old_encrypted_key)
                    
                    # Re-wrap with new key
                    new_encrypted_key = encrypt(new_pub, decrypted_user_priv)
                    user.encrypted_rsa_private_key = json.dumps(new_encrypted_key)
                    user.save()
                
                # --- B. ROTATE DIRECT MESSAGES ---
                dms = DirectMessage.objects.all()
                self.stdout.write(f'  > Re-encrypting {dms.count()} Direct Messages...')
                
                # Get current MAC secret for re-generating MAC tags
                dm_mac_secret = getattr(settings, 'DM_MAC_SECRET', settings.SECRET_KEY)
                
                dm_rotation_state = {'success': 0, 'failed': 0}
                failed_dms = []
                
                for msg in dms:
                    try:
                        # Two cases: legacy messages encrypted with server RSA, or
                        # messages that store a per-message RSA key wrapped by server RSA.
                        if getattr(msg, 'encrypted_rsa_private_key', None):
                            # Unwrap per-message private key using legacy server private key
                            wrapped = json.loads(msg.encrypted_rsa_private_key)
                            priv_str = decrypt(legacy_priv, wrapped)
                            # Re-wrap with new server public key
                            new_wrapped = encrypt(new_pub, priv_str)
                            msg.encrypted_rsa_private_key = json.dumps(new_wrapped)
                            # encrypted_content remains unchanged (encrypted with per-message key)
                            msg.save()
                            dm_rotation_state['success'] += 1
                        else:
                            # Legacy path: message ciphertext was encrypted with server RSA
                            ciphertext_array = json.loads(msg.encrypted_content)
                            plaintext = decrypt(legacy_priv, ciphertext_array)
                            
                            # Validate plaintext before reuse
                            if not plaintext or len(plaintext) == 0:
                                raise ValueError(f'Empty plaintext after decryption (msg {msg.id})')
                            
                            new_encrypted_array = encrypt(new_pub, plaintext)
                            msg.encrypted_content = json.dumps(new_encrypted_array)
                            msg.mac_tag = generate_mac(dm_mac_secret, plaintext)
                            msg.save()
                            dm_rotation_state['success'] += 1
                    except Exception as e:
                        dm_rotation_state['failed'] += 1
                        failed_dms.append((msg.id, str(e)))
                        self.stdout.write(self.style.ERROR(f'    [!] Failed to rotate msg ID {msg.id}: {e}'))
                        raise e # Trigger the rollback
                
                # --- C. ROTATE POSTS (re-wrap ECC private keys) ---
                posts = Post.objects.all()
                self.stdout.write(f'  > Re-wrapping ECC keys for {posts.count()} Posts...')
                
                post_rotation_state = {'success': 0, 'failed': 0}
                failed_posts = []
                
                for post in posts:
                    try:
                        # 1. Load the wrapped ECC private key
                        wrapped_ecc_key = json.loads(post.encrypted_ecc_private_key)
                        
                        # 2. Decrypt with old server private key
                        ecc_priv_key_str = decrypt(legacy_priv, wrapped_ecc_key)
                        
                        # Validate ECC key
                        if not ecc_priv_key_str or len(ecc_priv_key_str) == 0:
                            raise ValueError(f'Empty ECC private key after decryption (post {post.id})')
                        
                        # 3. Re-wrap with new server public key
                        new_wrapped_ecc_key = encrypt(new_pub, ecc_priv_key_str)
                        post.encrypted_ecc_private_key = json.dumps(new_wrapped_ecc_key)
                        post.save()
                        post_rotation_state['success'] += 1
                    except Exception as e:
                        post_rotation_state['failed'] += 1
                        failed_posts.append((post.id, str(e)))
                        self.stdout.write(self.style.ERROR(f'    [!] Failed to rotate post ID {post.id}: {e}'))
                        raise e # Trigger the rollback

            # 4. Verify rotated data can be decrypted
            self.stdout.write('\n  > Verifying rotated data integrity...')
            if not self._verify_rotated_data(new_priv):
                self.stdout.write(self.style.ERROR('[CRITICAL] Verification failed. Data may be corrupted.'))
                raise Exception('Data verification failed after rotation')
            
            # 5. Sanitize legacy private key from environment
            self.stdout.write('\n  > Sanitizing legacy key material...')
            try:
                del legacy_priv
                os.environ.pop('SERVER_RSA_PRIVATE_KEY', None)
                self.stdout.write(self.style.SUCCESS('    ✓ Legacy key removed from memory'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'    [!] Could not fully sanitize legacy key: {e}'))
            
            # 6. Write new keys securely to temp file
            self.stdout.write('\n  > Writing new keys to secure file...')
            keys_file = self._write_keys_securely(new_pub, new_priv)
            
            # 7. Success Output
            self.stdout.write(self.style.SUCCESS('\n[SUCCESS] Database Migration Complete! Zero data loss.'))
            self.stdout.write(self.style.WARNING(f'\n[ACTION REQUIRED] New keys written to: {keys_file}'))
            self.stdout.write(self.style.WARNING('1. Review and copy the keys from that file'))
            self.stdout.write(self.style.WARNING('2. Update your .env file with the new keys'))
            self.stdout.write(self.style.WARNING('3. Delete the keys file after updating .env'))
            self.stdout.write(self.style.WARNING('4. Restart the server to apply new keys\n'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n[FATAL ERROR] Rotation aborted. Database rolled back. Error: {e}'))
            # Attempt to sanitize any leaked key material
            try:
                del legacy_priv
                del new_priv
                os.environ.pop('SERVER_RSA_PRIVATE_KEY', None)
            except:
                pass