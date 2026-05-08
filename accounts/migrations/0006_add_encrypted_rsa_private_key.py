from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_alter_user_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='encrypted_rsa_private_key',
            field=models.TextField(blank=True, null=True),
        ),
    ]