from django.db import migrations


def backfill_post_ecc_public_key(apps, schema_editor):
    import json

    from crypto_engine.ecc_core import G, scalar_multiply
    from crypto_engine.rsa_core import decrypt
    from crypto_engine.server_keyring import _load_server_keys_from_env

    Post = apps.get_model('network', 'Post')
    _, server_priv = _load_server_keys_from_env()
    if not server_priv:
        return

    for post in Post.objects.all():
        if post.ecc_public_key:
            continue

        try:
            wrapped_ecc_priv = json.loads(post.encrypted_ecc_private_key)
            ecc_priv_key_str = decrypt(server_priv, wrapped_ecc_priv)
            ecc_priv_key = int(ecc_priv_key_str)
            ecc_public_key = scalar_multiply(ecc_priv_key, G)
            post.ecc_public_key = json.dumps(ecc_public_key)
            post.save(update_fields=['ecc_public_key'])
        except Exception:
            continue


class Migration(migrations.Migration):

    dependencies = [
        ('network', '0009_add_post_ecc_public_key'),
    ]

    operations = [
        migrations.RunPython(backfill_post_ecc_public_key, migrations.RunPython.noop),
    ]