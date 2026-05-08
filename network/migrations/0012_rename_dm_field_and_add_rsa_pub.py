from django.db import migrations, models


def rename_dm_field_and_add_rsa_pub(apps, schema_editor):
    DirectMessage = apps.get_model('network', 'DirectMessage')
    # If old field exists, copy data to new field name; migrations.RenameField below handles most DBs.
    # This function is kept minimal for compatibility.
    return


class Migration(migrations.Migration):

    dependencies = [
        ('network', '0011_rename_encrypted_ecc_key'),
    ]

    operations = [
        migrations.RenameField(
            model_name='directmessage',
            old_name='encrypted_ecc_private_key',
            new_name='encrypted_rsa_private_key',
        ),
        migrations.AddField(
            model_name='directmessage',
            name='rsa_public_key',
            field=models.TextField(default='[]'),
        ),
    ]
