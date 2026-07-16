from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.db.models.functions import Lower


class Command(BaseCommand):
    help = "检查缺少找回邮箱或邮箱重复的用户账号"

    def handle(self, *args, **options):
        User = get_user_model()
        missing_users = list(
            User.objects.filter(email="").order_by("username").values_list("username", flat=True)
        )
        duplicate_emails = list(
            User.objects.exclude(email="")
            .annotate(normalized_email=Lower("email"))
            .values("normalized_email")
            .annotate(total=Count("id"))
            .filter(total__gt=1)
            .order_by("normalized_email")
        )

        if missing_users:
            self.stdout.write(self.style.WARNING("缺少邮箱的账号：" + "、".join(missing_users)))
        if duplicate_emails:
            values = "、".join(item["normalized_email"] for item in duplicate_emails)
            self.stdout.write(self.style.WARNING("重复绑定的邮箱：" + values))
        if not missing_users and not duplicate_emails:
            self.stdout.write(self.style.SUCCESS("所有用户均已绑定唯一找回邮箱。"))
