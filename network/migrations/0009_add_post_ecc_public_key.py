# Generated manually to store the ECC public key used for post encryption.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('network', '0008_add_post_ecc_key'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='ecc_public_key',
            field=models.TextField(default='[]'),
        ),
    ]