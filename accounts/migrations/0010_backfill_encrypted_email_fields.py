import json

from django.db import migrations

from crypto_engine.rsa_core import encrypt


def _encrypt_with_user_public_key(user, plaintext):
    if not plaintext or not user.rsa_public_key:
        return None
    try:
        public_key = tuple(json.loads(user.rsa_public_key))
        encrypted_array = encrypt(public_key, plaintext)
        return json.dumps(encrypted_array)
    except Exception:
        return None


def backfill_encrypted_email(apps, schema_editor):
    User = apps.get_model('accounts', 'User')

    for user in User.objects.all().iterator():
        has_changes = False

        if user.email and not user.encrypted_email:
            encrypted_email = _encrypt_with_user_public_key(user, user.email)
            if encrypted_email:
                user.encrypted_email = encrypted_email
                user.email = ''
                has_changes = True

        if user.pending_email and not user.pending_encrypted_email:
            encrypted_pending = _encrypt_with_user_public_key(user, user.pending_email)
            if encrypted_pending:
                user.pending_encrypted_email = encrypted_pending
                user.pending_email = None
                has_changes = True

        if has_changes:
            user.save(update_fields=['encrypted_email', 'email', 'pending_encrypted_email', 'pending_email'])


def noop_reverse(apps, schema_editor):
    # Intentionally left empty: we do not restore plaintext emails.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_user_encrypted_email_user_pending_encrypted_email'),
    ]

    operations = [
        migrations.RunPython(backfill_encrypted_email, noop_reverse),
    ]
