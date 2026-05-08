from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('network', '0006_remove_post_encrypted_ecc_key'),
    ]

    operations = [
        migrations.CreateModel(
            name='Conversation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('encrypted_shared_secret', models.TextField(blank=True, null=True)),
                ('user_a', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='convo_as_a', to='accounts.user')),
                ('user_b', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='convo_as_b', to='accounts.user')),
            ],
            options={
                'unique_together': {('user_a', 'user_b')},
            },
        ),
    ]
