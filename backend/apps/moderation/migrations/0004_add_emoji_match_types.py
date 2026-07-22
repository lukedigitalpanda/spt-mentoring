from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('moderation', '0003_add_moderation_term'),
    ]

    operations = [
        migrations.AlterField(
            model_name='moderationterm',
            name='match_type',
            field=models.CharField(
                choices=[
                    ('EXACT', 'Exact'),
                    ('SUBSTRING', 'Substring'),
                    ('WILDCARD', 'Wildcard'),
                    ('REGEX', 'Regex'),
                    ('EMAIL_PATTERN', 'Email Pattern'),
                    ('URL_FRAGMENT', 'URL Fragment'),
                    ('EMOJI_SINGLE', 'Emoji Single'),
                    ('EMOJI_COMBO', 'Emoji Combination'),
                    ('EMOJI_OR_SET', 'Emoji OR Set'),
                ],
                default='SUBSTRING',
                max_length=20,
            ),
        ),
    ]
