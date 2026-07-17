import base64
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .models import Post, PostComment, PostLike, PostSave, PrivateMessage, ProjectCarRecord, UserGarageVehicle, UserProfile


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
        Post.objects.create(title="M2C 分享", body="改装记录", owner=self.user, author="旧昵称")
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
        self.assertEqual(post.owner, self.user)
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

    def test_defaults_plain_post_to_chat_category(self):
        response = self.client.post(
            "/api/posts/create/",
            data=json.dumps({
                "title": "日常驾驶感受",
                "body": "分享一次普通的用车体验。",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        post = Post.objects.get()
        self.assertEqual(post.post_type, "聊车")
        self.assertEqual(post.tone, "gray")

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


class PostInteractionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.owner = User.objects.create_user(username="owner", password="OwnerPass2026!")
        self.viewer = User.objects.create_user(username="viewer", password="ViewerPass2026!")
        self.post = Post.objects.create(
            owner=self.owner,
            author="owner",
            title="真实交互测试",
            body="用于验证收藏、点赞和评论会写入数据库。",
        )
        self.client.force_login(self.viewer)

    def test_save_toggle_is_persisted_and_user_scoped(self):
        response = self.client.post(f"/api/posts/{self.post.id}/save/", data="{}", content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["saved"])
        self.assertTrue(PostSave.objects.filter(user=self.viewer, post=self.post).exists())
        self.assertTrue(response.json()["post"]["is_saved"])

        response = self.client.post(f"/api/posts/{self.post.id}/save/", data="{}", content_type="application/json")
        self.assertFalse(response.json()["saved"])
        self.assertFalse(PostSave.objects.exists())

    def test_like_toggle_updates_real_count(self):
        response = self.client.post(f"/api/posts/{self.post.id}/like/", data="{}", content_type="application/json")

        self.post.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["liked"])
        self.assertEqual(self.post.likes, 1)
        self.assertEqual(PostLike.objects.filter(post=self.post).count(), 1)

        response = self.client.post(f"/api/posts/{self.post.id}/like/", data="{}", content_type="application/json")
        self.post.refresh_from_db()
        self.assertFalse(response.json()["liked"])
        self.assertEqual(self.post.likes, 0)

    def test_comment_creation_and_public_listing(self):
        response = self.client.post(
            f"/api/posts/{self.post.id}/comments/",
            data=json.dumps({"body": "这条评论需要真实保存。"}),
            content_type="application/json",
        )

        self.post.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.post.comments, 1)
        self.assertEqual(PostComment.objects.get().body, "这条评论需要真实保存。")

        self.client.logout()
        response = self.client.get(f"/api/posts/{self.post.id}/comments/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["comments"][0]["body"], "这条评论需要真实保存。")

    def test_anonymous_user_cannot_mutate_post_interactions(self):
        self.client.logout()

        self.assertEqual(self.client.post(f"/api/posts/{self.post.id}/save/").status_code, 401)
        self.assertEqual(self.client.post(f"/api/posts/{self.post.id}/like/").status_code, 401)
        self.assertEqual(self.client.post(f"/api/posts/{self.post.id}/comments/", data="{}", content_type="application/json").status_code, 401)


class PrivateMessageFlowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="message_user", password="MessagePass2026!")
        self.other = User.objects.create_user(username="message_other", password="MessagePass2026!")
        self.received = PrivateMessage.objects.create(sender=self.other, receiver=self.user, body="收到的未读消息")
        self.sent = PrivateMessage.objects.create(sender=self.user, receiver=self.other, body="已发送消息")
        self.client.force_login(self.user)

    def test_message_list_contains_sent_and_received_with_unread_count(self):
        response = self.client.get("/api/messages/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual({item["id"] for item in response.json()["messages"]}, {self.received.id, self.sent.id})
        self.assertEqual(response.json()["unread_count"], 1)

    def test_receiver_can_mark_message_read(self):
        response = self.client.post(f"/api/messages/{self.received.id}/read/", data="{}", content_type="application/json")

        self.received.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.received.is_read)
        self.assertEqual(response.json()["unread_count"], 0)

    def test_sender_cannot_mark_own_sent_message_as_read(self):
        response = self.client.post(f"/api/messages/{self.sent.id}/read/", data="{}", content_type="application/json")

        self.assertEqual(response.status_code, 404)
        self.sent.refresh_from_db()
        self.assertFalse(self.sent.is_read)

    def test_sent_message_is_returned_after_refresh(self):
        response = self.client.post(
            f"/api/users/{self.other.id}/message/",
            data=json.dumps({"body": "新发送的真实私信"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        list_response = self.client.get("/api/messages/")
        self.assertIn("新发送的真实私信", [item["body"] for item in list_response.json()["messages"]])


class UserContentBoundaryTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="garage_user", password="GaragePass2026!")
        self.other = User.objects.create_user(username="garage_other", password="GaragePass2026!")
        self.other_vehicle = UserGarageVehicle.objects.create(user=self.other, custom_name="他人的车辆")
        self.client.force_login(self.user)

    def test_project_record_cannot_attach_another_users_vehicle(self):
        response = self.client.post(
            "/api/projects/create/",
            data=json.dumps({"vehicle_id": self.other_vehicle.id, "title": "越权关联"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "关联车辆不存在")
        self.assertEqual(ProjectCarRecord.objects.count(), 0)

    def test_garage_rejects_oversized_vehicle_name(self):
        response = self.client.post(
            "/api/garage/create/",
            data=json.dumps({"custom_name": "M" * 121}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "车辆信息长度超出限制")

    def test_garage_and_project_record_persist_in_site_data(self):
        vehicle_response = self.client.post(
            "/api/garage/create/",
            data=json.dumps({"custom_name": "我的 M2C", "year": "2020", "color": "蓝色", "mods": "避震与刹车"}),
            content_type="application/json",
        )
        vehicle_id = vehicle_response.json()["vehicle"]["id"]
        record_response = self.client.post(
            "/api/projects/create/",
            data=json.dumps({"vehicle_id": vehicle_id, "title": "第一阶段", "stage": "底盘", "content": "完成避震安装"}),
            content_type="application/json",
        )

        self.assertEqual(vehicle_response.status_code, 200)
        self.assertEqual(record_response.status_code, 200)
        site_response = self.client.get("/api/site-data/")
        self.assertEqual(site_response.json()["garage"][0]["name"], "我的 M2C")
        self.assertEqual(site_response.json()["projects"][0]["title"], "第一阶段")


class FollowAndModerationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="follow_user", password="FollowPass2026!")
        self.target = User.objects.create_user(username="follow_target", password="FollowPass2026!")
        self.post = Post.objects.create(owner=self.target, author="follow_target", title="管理测试", body="真实内容")
        self.client.force_login(self.user)

    def test_follow_counts_update_from_database(self):
        response = self.client.post(f"/api/users/{self.target.id}/follow/", data="{}", content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["current_user"]["following_count"], 1)
        self.assertEqual(response.json()["target_user"]["followers_count"], 1)

    def test_regular_user_cannot_delete_post(self):
        response = self.client.post(f"/api/posts/{self.post.id}/delete/", data="{}", content_type="application/json")

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Post.objects.filter(id=self.post.id).exists())

    def test_staff_user_can_delete_post(self):
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])

        response = self.client.post(f"/api/posts/{self.post.id}/delete/", data="{}", content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Post.objects.filter(id=self.post.id).exists())


class FrontendInteractionContractTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        app_path = Path(settings.BASE_DIR).parent / "src" / "App.vue"
        cls.source = app_path.read_text(encoding="utf-8-sig")

    def test_public_controls_do_not_use_known_placeholder_routes(self):
        forbidden_patterns = [
            "/create/project-car",
            "pathFor('feed'",
            "#likes",
            "toggleSave(post.id); goTo('/saved')",
            "goTo('/settings/shortcuts')",
        ]

        for pattern in forbidden_patterns:
            with self.subTest(pattern=pattern):
                self.assertNotIn(pattern, self.source)

    def test_post_and_message_controls_call_real_apis(self):
        required_patterns = [
            "/save/",
            "/like/",
            "/comments/",
            "/read/",
            "unreadMessageCount",
        ]

        for pattern in required_patterns:
            with self.subTest(pattern=pattern):
                self.assertIn(pattern, self.source)

    def test_community_page_has_publish_controls_and_filters(self):
        community_section = self.source.split('<template v-else-if="activePage === 3">', 1)[1]
        community_section = community_section.split('<template v-else-if="activePage === 4">', 1)[0]

        self.assertIn('@click="openComposer"', community_section)
        self.assertIn('@click="openPhotoComposer"', community_section)
        self.assertIn('@click="openSpecsComposer()"', community_section)
        self.assertIn('class="activity-tabs"', community_section)
        self.assertIn('"聊车"', self.source)


class PublicUserPrivacyTests(TestCase):
    def test_site_data_never_exposes_other_users_email(self):
        get_user_model().objects.create_user(
            username="public_profile",
            email="private@example.com",
            password="PrivacyPass2026!",
        )

        response = self.client.get("/api/site-data/")

        self.assertEqual(response.status_code, 200)
        public_user = next(item for item in response.json()["users"] if item["username"] == "public_profile")
        self.assertNotIn("email", public_user)
        self.assertNotIn("is_staff", public_user)
        self.assertNotIn("banned_reason", public_user)

    def test_follow_response_does_not_expose_target_email(self):
        User = get_user_model()
        viewer = User.objects.create_user(username="privacy_viewer", password="PrivacyPass2026!")
        target = User.objects.create_user(username="privacy_target", email="target-private@example.com", password="PrivacyPass2026!")
        self.client.force_login(viewer)

        response = self.client.post(f"/api/users/{target.id}/follow/", data="{}", content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("email", response.json()["target_user"])


class FrontendRouteSmokeTests(SimpleTestCase):
    def test_all_public_root_routes_render_frontend(self):
        routes = [
            "/", "/cars", "/reviews", "/community", "/market", "/rankings",
            "/garage", "/projects", "/profile", "/saved", "/messages",
            "/notifications", "/topics", "/events", "/clubs", "/shops",
            "/search", "/create", "/create/photos", "/create/specs", "/create/location",
        ]

        for route in routes:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Tuner Hub")
