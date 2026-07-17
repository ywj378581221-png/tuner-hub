import base64
import json
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
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

    def test_request_includes_each_legacy_account_using_the_same_email(self):
        get_user_model().objects.create_user(
            username="second_owner",
            email="owner@example.com",
            password="SecondPass2026!",
        )

        response = self.client.post(
            "/api/auth/password-reset/request/",
            data=json.dumps({"email": "owner@example.com"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("账号：reset_owner", mail.outbox[0].body)
        self.assertIn("账号：second_owner", mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].body.count("/reset-password/"), 2)

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


class RegistrationEmailTests(TestCase):
    def test_requires_email(self):
        response = self.client.post(
            "/api/auth/register/",
            data=json.dumps({
                "username": "new_owner",
                "nickname": "新车主",
                "password": "SecureRegister2026!",
                "email": "",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_rejects_invalid_email(self):
        response = self.client.post(
            "/api/auth/register/",
            data=json.dumps({
                "username": "new_owner",
                "nickname": "新车主",
                "password": "SecureRegister2026!",
                "email": "not-an-email",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "请输入有效的邮箱地址")

    def test_rejects_email_already_in_use(self):
        get_user_model().objects.create_user(
            username="existing_owner",
            email="owner@example.com",
            password="ExistingPass2026!",
        )

        response = self.client.post(
            "/api/auth/register/",
            data=json.dumps({
                "username": "new_owner",
                "nickname": "新车主",
                "password": "SecureRegister2026!",
                "email": "OWNER@example.com",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"], "该邮箱已绑定其他账号")


class UpdateEmailTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="email_owner",
            email="old@example.com",
            password="CurrentPass2026!",
        )

    def test_requires_current_password(self):
        self.client.force_login(self.user)

        response = self.client.post(
            "/api/auth/email/",
            data=json.dumps({"email": "new@example.com", "current_password": ""}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_rejects_email_used_by_another_user(self):
        get_user_model().objects.create_user(
            username="another_owner",
            email="used@example.com",
            password="AnotherPass2026!",
        )
        self.client.force_login(self.user)

        response = self.client.post(
            "/api/auth/email/",
            data=json.dumps({
                "email": "USED@example.com",
                "current_password": "CurrentPass2026!",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 409)

    def test_updates_recovery_email(self):
        self.client.force_login(self.user)

        response = self.client.post(
            "/api/auth/email/",
            data=json.dumps({
                "email": "NEW@example.com",
                "current_password": "CurrentPass2026!",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "new@example.com")
        self.assertEqual(response.json()["user"]["email"], "new@example.com")


class CorsPolicyTests(TestCase):
    def test_rejects_untrusted_origin(self):
        response = self.client.options(
            "/api/auth/email/",
            HTTP_ORIGIN="https://evil.example",
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Access-Control-Allow-Origin", response)

    def test_allows_same_origin(self):
        response = self.client.options(
            "/api/auth/email/",
            HTTP_ORIGIN="http://testserver",
        )

        self.assertEqual(response["Access-Control-Allow-Origin"], "http://testserver")
        self.assertEqual(response["Access-Control-Allow-Credentials"], "true")

    @override_settings(TUNERHUB_CORS_ALLOWED_ORIGINS=["https://frontend.example"])
    def test_allows_configured_frontend_origin(self):
        response = self.client.options(
            "/api/auth/email/",
            HTTP_ORIGIN="https://frontend.example",
        )

        self.assertEqual(response["Access-Control-Allow-Origin"], "https://frontend.example")


class LoginThrottleTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(
            username="throttle_owner",
            password="CorrectPass2026!",
        )

    def test_blocks_after_five_failed_attempts(self):
        for _ in range(5):
            response = self.client.post(
                "/api/auth/login/",
                data=json.dumps({"username": "throttle_owner", "password": "wrong"}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 401)

        blocked_response = self.client.post(
            "/api/auth/login/",
            data=json.dumps({"username": "throttle_owner", "password": "CorrectPass2026!"}),
            content_type="application/json",
        )

        self.assertEqual(blocked_response.status_code, 429)

    def test_successful_login_clears_failed_attempts(self):
        for _ in range(2):
            self.client.post(
                "/api/auth/login/",
                data=json.dumps({"username": "throttle_owner", "password": "wrong"}),
                content_type="application/json",
            )

        response = self.client.post(
            "/api/auth/login/",
            data=json.dumps({"username": "throttle_owner", "password": "CorrectPass2026!"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)


class AvatarUploadSecurityTests(TestCase):
    valid_png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    )

    def setUp(self):
        self.media_directory = tempfile.TemporaryDirectory()
        self.media_override = override_settings(MEDIA_ROOT=self.media_directory.name)
        self.media_override.enable()
        self.user = get_user_model().objects.create_user(
            username="avatar_owner",
            password="AvatarPass2026!",
        )
        self.client.force_login(self.user)

    def tearDown(self):
        self.media_override.disable()
        self.media_directory.cleanup()

    def test_accepts_valid_png(self):
        avatar = SimpleUploadedFile("avatar.png", self.valid_png, content_type="image/png")

        response = self.client.post("/api/auth/avatar/", {"avatar": avatar})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["user"]["avatar"].endswith(".png"))

    def test_rejects_disguised_non_image(self):
        avatar = SimpleUploadedFile("avatar.png", b"<html>not an image</html>", content_type="image/png")

        response = self.client.post("/api/auth/avatar/", {"avatar": avatar})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "头像文件已损坏或不是有效图片")

    def test_rejects_oversized_file(self):
        avatar = SimpleUploadedFile(
            "avatar.png",
            b"x" * (5 * 1024 * 1024 + 1),
            content_type="image/png",
        )

        response = self.client.post("/api/auth/avatar/", {"avatar": avatar})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "头像不能超过 5MB")


class PostImageUploadTests(TestCase):
    def setUp(self):
        self.media_directory = tempfile.TemporaryDirectory()
        self.media_override = override_settings(MEDIA_ROOT=self.media_directory.name)
        self.media_override.enable()
        self.user = get_user_model().objects.create_user(
            username="post_owner",
            password="PostOwnerPass2026!",
            first_name="帖子车主",
        )
        self.client.force_login(self.user)

    def tearDown(self):
        self.media_override.disable()
        self.media_directory.cleanup()

    def test_creates_post_with_uploaded_image(self):
        image = SimpleUploadedFile(
            "m2c.png",
            AvatarUploadSecurityTests.valid_png,
            content_type="image/png",
        )

        response = self.client.post(
            "/api/posts/create/",
            {
                "title": "M2C 改装记录",
                "body": "更换轮毂与刹车后的驾驶感受。",
                "type": "改装进度",
                "car": "",
                "specs": json.dumps(["轮毂: 18x9.5J", "动力: 450 hp"]),
                "location": "上海国际赛车场",
                "image": image,
            },
        )

        self.assertEqual(response.status_code, 200)
        post = Post.objects.get()
        self.assertTrue(post.image_upload.name.startswith("posts/"))
        self.assertEqual(post.specs, ["轮毂: 18x9.5J", "动力: 450 hp"])
        self.assertEqual(post.location, "上海国际赛车场")
        self.assertTrue(response.json()["post"]["image"].startswith("/media/posts/"))
        self.assertEqual(response.json()["post"]["location"], "上海国际赛车场")

    def test_rejects_disguised_post_image(self):
        image = SimpleUploadedFile(
            "fake.png",
            b"<script>alert('not an image')</script>",
            content_type="image/png",
        )

        response = self.client.post(
            "/api/posts/create/",
            {
                "title": "无效图片",
                "body": "这条内容不应保存。",
                "type": "改装进度",
                "image": image,
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "帖子图片文件已损坏或不是有效图片")
        self.assertEqual(Post.objects.count(), 0)

    def test_keeps_json_post_creation_compatible(self):
        response = self.client.post(
            "/api/posts/create/",
            data=json.dumps({
                "title": "纯文字记录",
                "body": "没有图片也可以正常发布。",
                "type": "改装进度",
                "car": "",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Post.objects.count(), 1)

    def test_rejects_more_than_eight_specs(self):
        response = self.client.post(
            "/api/posts/create/",
            {
                "title": "参数数量测试",
                "body": "参数数量超过限制时不应保存帖子。",
                "type": "改装进度",
                "specs": json.dumps([f"参数 {index}" for index in range(9)]),
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "最多添加 8 项参数")
        self.assertEqual(Post.objects.count(), 0)
