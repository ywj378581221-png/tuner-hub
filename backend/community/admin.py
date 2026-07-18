from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from .models import Article, ArticleBlock, ArticleComment, ArticleLike, ArticleSave, Car, CarTrim, Club, ContentReport, Event, Guide, MarketItem, Post, PostComment, PostLike, PostSave, PrivateMessage, ProjectCarRecord, Shop, Topic, UserDailyActivity, UserFollow, UserGarageVehicle, UserProfile
from .views import user_level_points


class ImageUploadAdminMixin:
    readonly_fields = ("image_preview",)

    @admin.display(description="图片预览")
    def image_preview(self, obj):
        upload = getattr(obj, "image_upload", None)
        image_url = upload.url if upload else getattr(obj, "image", "")
        if not image_url:
            return "暂无图片"
        return format_html('<img src="{}" style="max-width:180px;max-height:110px;border-radius:6px;" />', image_url)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "nickname", "ban_status", "live_level", "live_points", "live_followers", "live_following", "updated_at")
    list_filter = ("is_banned",)
    search_fields = ("user__username", "user__email", "nickname")
    readonly_fields = ("avatar_preview",)
    fields = ("user", "nickname", "avatar", "avatar_preview", "signature", "is_banned", "banned_reason", "banned_at")
    actions = ("ban_users", "unban_users")

    def save_model(self, request, obj, form, change):
        if obj.is_banned and not obj.banned_at:
            obj.banned_at = timezone.now()
        if not obj.is_banned:
            obj.banned_at = None
            obj.banned_reason = ""
        obj.user.is_active = not obj.is_banned
        obj.user.save(update_fields=["is_active"])
        super().save_model(request, obj, form, change)

    @admin.display(description="封禁状态")
    def ban_status(self, obj):
        return "已封禁" if obj.is_banned else "正常"

    @admin.action(description="封禁选中账号")
    def ban_users(self, request, queryset):
        for profile in queryset.select_related("user"):
            profile.is_banned = True
            if not profile.banned_reason:
                profile.banned_reason = "账号已被管理员封禁"
            profile.banned_at = timezone.now()
            profile.save(update_fields=["is_banned", "banned_reason", "banned_at", "updated_at"])
            profile.user.is_active = False
            profile.user.save(update_fields=["is_active"])

    @admin.action(description="解封选中账号")
    def unban_users(self, request, queryset):
        for profile in queryset.select_related("user"):
            profile.is_banned = False
            profile.banned_reason = ""
            profile.banned_at = None
            profile.save(update_fields=["is_banned", "banned_reason", "banned_at", "updated_at"])
            profile.user.is_active = True
            profile.user.save(update_fields=["is_active"])

    @admin.display(description="头像预览")
    def avatar_preview(self, obj):
        if not obj.avatar:
            return "暂无头像"
        return format_html('<img src="{}" style="width:72px;height:72px;border-radius:50%;object-fit:cover;" />', obj.avatar.url)

    @admin.display(description="实时粉丝")
    def live_followers(self, obj):
        return obj.user.follower_relations.count()

    @admin.display(description="实时关注")
    def live_following(self, obj):
        return obj.user.following_relations.count()

    @admin.display(description="实时等级")
    def live_level(self, obj):
        return f"Lv.{min(30, self.live_points(obj) // 100 + 1)}"

    @admin.display(description="活跃积分")
    def live_points(self, obj):
        return user_level_points(obj.user, obj)["total"]


@admin.register(UserDailyActivity)
class UserDailyActivityAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "visit_count", "active_actions", "updated_at")
    list_filter = ("date",)
    search_fields = ("user__username", "user__email")


@admin.register(UserGarageVehicle)
class UserGarageVehicleAdmin(admin.ModelAdmin):
    list_display = ("custom_name", "car", "user", "year", "color", "updated_at")
    list_filter = ("car", "year", "color")
    search_fields = ("custom_name", "user__username", "car__name", "mods")
    autocomplete_fields = ("user", "car")


@admin.register(ProjectCarRecord)
class ProjectCarRecordAdmin(admin.ModelAdmin):
    list_display = ("title", "vehicle", "user", "stage", "updated_at")
    list_filter = ("stage",)
    search_fields = ("title", "content", "user__username", "vehicle__custom_name", "vehicle__car__name")
    autocomplete_fields = ("user", "vehicle")


@admin.register(UserFollow)
class UserFollowAdmin(admin.ModelAdmin):
    list_display = ("follower", "following", "created_at")
    search_fields = ("follower__username", "following__username")
    autocomplete_fields = ("follower", "following")


@admin.register(PrivateMessage)
class PrivateMessageAdmin(admin.ModelAdmin):
    list_display = ("sender", "receiver", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("sender__username", "receiver__username", "body")
    autocomplete_fields = ("sender", "receiver")


@admin.register(Post)
class PostAdmin(ImageUploadAdminMixin, admin.ModelAdmin):
    list_display = ("title", "post_type", "owner", "author", "car", "club", "is_pinned", "featured", "state", "created_at")
    list_filter = ("post_type", "is_pinned", "featured", "state", "created_at")
    search_fields = ("title", "body", "author")
    list_editable = ("is_pinned", "featured", "state")
    fields = ("title", "body", "post_type", "tone", "image_upload", "image_preview", "image_caption", "image", "owner", "author", "time_label", "car", "club", "shop", "location", "likes", "comments", "progress", "specs", "is_pinned", "featured", "state")


@admin.register(PostSave)
class PostSaveAdmin(admin.ModelAdmin):
    list_display = ("user", "post", "created_at")
    search_fields = ("user__username", "post__title")
    autocomplete_fields = ("user", "post")


@admin.register(PostLike)
class PostLikeAdmin(admin.ModelAdmin):
    list_display = ("user", "post", "created_at")
    search_fields = ("user__username", "post__title")
    autocomplete_fields = ("user", "post")


@admin.register(PostComment)
class PostCommentAdmin(admin.ModelAdmin):
    list_display = ("user", "post", "created_at")
    search_fields = ("user__username", "post__title", "body")
    autocomplete_fields = ("user", "post")


@admin.register(Car)
class CarAdmin(ImageUploadAdminMixin, admin.ModelAdmin):
    list_display = ("name", "tag", "heat", "state")
    list_filter = ("state", "tag")
    search_fields = ("name", "tag")
    prepopulated_fields = {"slug": ("name",)}
    fields = ("name", "slug", "tag", "heat", "image_upload", "image_preview", "image", "state")


@admin.register(CarTrim)
class CarTrimAdmin(admin.ModelAdmin):
    list_display = ("name", "car", "engine", "horsepower", "drivetrain", "featured", "state")
    list_filter = ("car", "featured", "state", "drivetrain", "fuel")
    search_fields = ("name", "car__name", "engine", "gearbox")
    list_editable = ("featured", "state")


@admin.register(Club)
class ClubAdmin(ImageUploadAdminMixin, admin.ModelAdmin):
    list_display = ("short_name", "name", "member_count", "state")
    list_filter = ("state",)
    search_fields = ("short_name", "name")
    prepopulated_fields = {"slug": ("name",)}
    fields = ("short_name", "name", "slug", "member_count", "image_upload", "image_preview", "image", "state")


@admin.register(Shop)
class ShopAdmin(ImageUploadAdminMixin, admin.ModelAdmin):
    list_display = ("short_name", "name", "rating", "services", "certified", "state")
    list_filter = ("certified", "state")
    search_fields = ("short_name", "name", "services")
    prepopulated_fields = {"slug": ("name",)}
    fields = ("short_name", "name", "slug", "rating", "services", "image_upload", "image_preview", "image", "certified", "state")


@admin.register(Event)
class EventAdmin(ImageUploadAdminMixin, admin.ModelAdmin):
    list_display = ("name", "meta", "count", "state")
    list_filter = ("state",)
    search_fields = ("name", "meta")
    prepopulated_fields = {"slug": ("name",)}
    fields = ("name", "slug", "meta", "count", "image_upload", "image_preview", "image", "state")


@admin.register(MarketItem)
class MarketItemAdmin(ImageUploadAdminMixin, admin.ModelAdmin):
    list_display = ("name", "state")
    list_filter = ("state",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    fields = ("name", "slug", "image_upload", "image_preview", "image", "state")


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("title", "count", "state")
    list_filter = ("state",)
    search_fields = ("title", "desc")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Guide)
class GuideAdmin(admin.ModelAdmin):
    list_display = ("title", "state", "created_at")
    list_filter = ("state",)
    search_fields = ("title", "body")


class ArticleBlockInline(admin.StackedInline):
    model = ArticleBlock
    extra = 0
    fields = ("position", "block_type", "text", "image_upload", "caption")
    ordering = ("position",)


@admin.register(Article)
class ArticleAdmin(ImageUploadAdminMixin, admin.ModelAdmin):
    list_display = ("title", "category", "owner", "author", "car", "views", "likes", "comments", "is_pinned", "featured", "state", "created_at")
    list_filter = ("category", "is_pinned", "featured", "state", "created_at")
    search_fields = ("title", "summary", "body", "author", "owner__username")
    list_editable = ("is_pinned", "featured", "state")
    prepopulated_fields = {"slug": ("title",)}
    fields = ("title", "slug", "category", "summary", "body", "image_upload", "image_preview", "image_caption", "image", "owner", "author", "car", "views", "likes", "comments", "is_pinned", "featured", "state")
    inlines = (ArticleBlockInline,)


@admin.register(ArticleSave)
class ArticleSaveAdmin(admin.ModelAdmin):
    list_display = ("user", "article", "created_at")
    search_fields = ("user__username", "article__title")
    autocomplete_fields = ("user", "article")


@admin.register(ArticleLike)
class ArticleLikeAdmin(admin.ModelAdmin):
    list_display = ("user", "article", "created_at")
    search_fields = ("user__username", "article__title")
    autocomplete_fields = ("user", "article")


@admin.register(ArticleComment)
class ArticleCommentAdmin(admin.ModelAdmin):
    list_display = ("user", "article", "created_at")
    search_fields = ("user__username", "article__title", "body")
    autocomplete_fields = ("user", "article")


@admin.register(ContentReport)
class ContentReportAdmin(admin.ModelAdmin):
    list_display = ("target_title", "target_type", "reason", "reporter", "status", "reviewed_by", "created_at")
    list_filter = ("status", "target_type", "reason", "created_at")
    search_fields = ("target_title", "detail", "reporter__username")
    readonly_fields = ("reporter", "target_type", "target_id", "target_title", "reason", "detail", "created_at", "updated_at")
    fields = ("reporter", "target_type", "target_id", "target_title", "reason", "detail", "status", "reviewed_by", "reviewed_at", "created_at", "updated_at")

    def save_model(self, request, obj, form, change):
        if obj.status != "pending":
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()
        else:
            obj.reviewed_by = None
            obj.reviewed_at = None
        super().save_model(request, obj, form, change)
