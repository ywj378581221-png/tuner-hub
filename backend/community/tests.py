import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

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


class ChangePasswordTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="password_owner",
            password="CurrentPass2026!",
        )

    def test_requires_login(self):
        response = self.client.post(
            "/api/auth/password/",
            data=json.dumps({
                "current_password": "CurrentPass2026!",
                "new_password": "NewSecurePass2026!",
                "confirm_password": "NewSecurePass2026!",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)

    def test_rejects_incorrect_current_password(self):
        self.client.force_login(self.user)

        response = self.client.post(
            "/api/auth/password/",
            data=json.dumps({
                "current_password": "WrongPass2026!",
                "new_password": "NewSecurePass2026!",
                "confirm_password": "NewSecurePass2026!",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "当前密码不正确")

    def test_rejects_mismatched_confirmation(self):
        self.client.force_login(self.user)

        response = self.client.post(
            "/api/auth/password/",
            data=json.dumps({
                "current_password": "CurrentPass2026!",
                "new_password": "NewSecurePass2026!",
                "confirm_password": "AnotherPass2026!",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "两次输入的新密码不一致")

    def test_changes_password_and_keeps_current_session(self):
        self.client.force_login(self.user)

        response = self.client.post(
            "/api/auth/password/",
            data=json.dumps({
                "current_password": "CurrentPass2026!",
                "new_password": "NewSecurePass2026!",
                "confirm_password": "NewSecurePass2026!",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewSecurePass2026!"))
        self.assertFalse(self.user.check_password("CurrentPass2026!"))
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me/").json()["user"]["id"], self.user.id)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="noreply@tunerhub.test",
    TUNERHUB_PUBLIC_URL="https://tunerhub.test",
)
class PasswordResetTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(
            username="reset_owner",
            email="owner@example.com",
            password="CurrentPass2026!",
        )

    def test_request_sends_reset_link_for_registered_email(self):
        response = self.client.post(
            "/api/auth/password-reset/request/",
            data=json.dumps({"email": "owner@example.com"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("https://tunerhub.test/reset-password/", mail.outbox[0].body)

    def test_request_does_not_reveal_unknown_email(self):
        response = self.client.post(
            "/api/auth/password-reset/request/",
            data=json.dumps({"email": "unknown@example.com"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "如果该邮箱已注册，重置链接会发送到邮箱")
        self.assertEqual(len(mail.outbox), 0)

    @patch("community.views.send_mail", side_effect=RuntimeError("SMTP unavailable"))
    def test_request_does_not_reveal_mail_delivery_failure(self, _send_mail):
        response = self.client.post(
            "/api/auth/password-reset/request/",
            data=json.dumps({"email": "owner@example.com"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "如果该邮箱已注册，重置链接会发送到邮箱")

    def test_confirm_resets_password_and_invalidates_token(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        payload = {
            "uid": uid,
            "token": token,
            "new_password": "ResetSecurePass2026!",
            "confirm_password": "ResetSecurePass2026!",
        }

        response = self.client.post(
            "/api/auth/password-reset/confirm/",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("ResetSecurePass2026!"))
        reused_response = self.client.post(
            "/api/auth/password-reset/confirm/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(reused_response.status_code, 400)

# Create your tests here.
