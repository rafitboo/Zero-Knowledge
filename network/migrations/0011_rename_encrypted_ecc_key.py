from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('network', '0010_backfill_post_ecc_public_key'),
    ]

    operations = [
        migrations.RenameField(
            model_name='post',
            old_name='encrypted_ecc_key',
            new_name='encrypted_ecc_private_key',
        ),
        migrations.RenameField(
            model_name='directmessage',
            old_name='encrypted_ecc_key',
            new_name='encrypted_ecc_private_key',
        ),
    ]
