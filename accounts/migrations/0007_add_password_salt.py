from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_add_encrypted_rsa_private_key'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='password_salt',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
    ]
