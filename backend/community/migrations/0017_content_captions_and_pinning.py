from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0016_alter_post_post_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="article",
            name="image_caption",
            field=models.CharField(blank=True, max_length=200, verbose_name="图片说明"),
        ),
        migrations.AddField(
            model_name="article",
            name="is_pinned",
            field=models.BooleanField(default=False, verbose_name="置顶"),
        ),
        migrations.AddField(
            model_name="post",
            name="image_caption",
            field=models.CharField(blank=True, max_length=200, verbose_name="图片说明"),
        ),
        migrations.AddField(
            model_name="post",
            name="is_pinned",
            field=models.BooleanField(default=False, verbose_name="置顶"),
        ),
        migrations.AlterModelOptions(
            name="article",
            options={"ordering": ["-is_pinned", "-created_at"], "verbose_name": "资讯文章", "verbose_name_plural": "资讯文章"},
        ),
        migrations.AlterModelOptions(
            name="post",
            options={"ordering": ["-is_pinned", "-created_at"], "verbose_name": "帖子", "verbose_name_plural": "帖子"},
        ),
    ]
