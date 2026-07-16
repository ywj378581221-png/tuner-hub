import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Post, UserProfile


class UpdateProfileTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="m2_owner",
            password="test-password",
            first_name="旧昵称",
        )
        UserProfile.objects.create(user=self.user, nickname="旧昵称")

    def test_requires_login(self):
        response = self.client.post(
            "/api/auth/profile/",
            data=json.dumps({"nickname": "新昵称"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)

    def test_updates_nickname_and_existing_post_author(self):
        Post.objects.create(title="M2C 分享", body="改装记录", author="旧昵称")
        self.client.force_login(self.user)

        response = self.client.post(
            "/api/auth/profile/",
            data=json.dumps({"nickname": "M2C车主"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.first_name, "M2C车主")
        self.assertEqual(self.user.profile.nickname, "M2C车主")
        self.assertEqual(Post.objects.get().author, "M2C车主")
        self.assertEqual(response.json()["user"]["nickname"], "M2C车主")

    def test_rejects_blank_nickname(self):
        self.client.force_login(self.user)

        response = self.client.post(
            "/api/auth/profile/",
            data=json.dumps({"nickname": "   "}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "昵称不能为空")

# Create your tests here.
