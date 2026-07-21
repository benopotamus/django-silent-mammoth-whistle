from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('silent_mammoth_whistle', '0009_whistle_referer'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='whistle',
            index=models.Index(fields=['datetime'], name='smw_datetime_idx'),
        ),
        migrations.AddIndex(
            model_name='whistle',
            index=models.Index(fields=['user_id'], name='smw_user_id_idx'),
        ),
        migrations.AddIndex(
            model_name='whistle',
            index=models.Index(fields=['is_authenticated', 'datetime'], name='smw_auth_datetime_idx'),
        ),
        migrations.AddIndex(
            model_name='whistle',
            index=models.Index(condition=models.Q(('request', 'PING')), fields=['user_id'], name='smw_ping_user_idx'),
        ),
    ]
