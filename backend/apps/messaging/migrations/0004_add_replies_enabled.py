from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('messaging', '0003_add_recipient_programmes'),
    ]

    operations = [
        migrations.AddField(
            model_name='conversation',
            name='replies_enabled',
            field=models.BooleanField(
                default=True,
                help_text='When False, participants cannot reply (used for broadcast-only messages)',
            ),
        ),
        migrations.AddField(
            model_name='massmessage',
            name='replies_enabled',
            field=models.BooleanField(
                default=True,
                help_text='Allow recipients to reply to this broadcast. When disabled, the reply UI is hidden.',
            ),
        ),
    ]
