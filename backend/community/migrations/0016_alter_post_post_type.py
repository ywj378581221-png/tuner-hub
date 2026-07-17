from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("community", "0015_post_owner_postcomment_postlike_postsave"),
    ]

    operations = [
        migrations.AlterField(
            model_name="post",
            name="post_type",
            field=models.CharField(
                choices=[
                    ("聊车", "聊车"),
                    ("改装进度", "改装进度"),
                    ("聚会", "聚会"),
                    ("店家施工", "店家施工"),
                    ("二手市场", "二手市场"),
                ],
                default="聊车",
                max_length=30,
                verbose_name="内容类型",
            ),
        ),
        migrations.AlterField(
            model_name="post",
            name="tone",
            field=models.CharField(default="gray", max_length=20, verbose_name="颜色标识"),
        ),
    ]
