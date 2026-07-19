import json
import hashlib
import warnings
from uuid import uuid4
from pathlib import Path
from urllib.parse import urlsplit

from PIL import Image, UnidentifiedImageError
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.contrib.sessions.models import Session
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.text import slugify
from django.utils.cache import patch_vary_headers
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods
from .models import Article, ArticleBlock, ArticleComment, ArticleLike, ArticleSave, Car, CarTrim, Club, ContentReport, Event, Guide, MarketItem, Post, PostComment, PostLike, PostSave, PrivateMessage, ProjectCarRecord, PublishState, Shop, Topic, UserDailyActivity, UserFollow, UserGarageVehicle, UserProfile


def with_cors(response, request=None):
    origin = request.headers.get("Origin") if request else None
    if origin and request:
        parsed_origin = urlsplit(origin)
        same_origin = (
            parsed_origin.scheme == request.scheme
            and parsed_origin.netloc == request.get_host()
        )
        allowed_origin = same_origin or origin in settings.TUNERHUB_CORS_ALLOWED_ORIGINS
        patch_vary_headers(response, ["Origin"])
        if allowed_origin:
            response["Access-Control-Allow-Origin"] = origin
            response["Access-Control-Allow-Credentials"] = "true"
            response["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
            response["Access-Control-Allow-Headers"] = "Content-Type"
    return response


def options_response(request):
    return with_cors(JsonResponse({}), request)


def read_json(request):
    if not request.body:
      return {}
    return json.loads(request.body.decode("utf-8"))


def request_client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR", "")


def validate_uploaded_image(upload, label="图片", max_size_mb=10):
    if upload.size > max_size_mb * 1024 * 1024:
        return f"{label}不能超过 {max_size_mb}MB"
    if upload.content_type and not upload.content_type.startswith("image/"):
        return f"{label}必须是图片文件"
    if Path(upload.name).suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
        return f"{label}仅支持 JPG、PNG 或 WebP"

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(upload) as image:
                image.verify()
                image_format = (image.format or "").upper()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombWarning, Image.DecompressionBombError):
        return f"{label}文件已损坏或不是有效图片"
    finally:
        upload.seek(0)
    if image_format not in {"JPEG", "PNG", "WEBP"}:
        return f"{label}仅支持 JPG、PNG 或 WebP"
    return None


def normalize_post_specs(raw_specs):
    if raw_specs in (None, ""):
        return []
    if isinstance(raw_specs, str):
        try:
            raw_specs = json.loads(raw_specs)
        except json.JSONDecodeError as error:
            raise ValueError("参数格式不正确") from error
    if not isinstance(raw_specs, list):
        raise ValueError("参数格式不正确")
    if len(raw_specs) > 8:
        raise ValueError("最多添加 8 项参数")

    specs = []
    for raw_spec in raw_specs:
        if not isinstance(raw_spec, str):
            raise ValueError("参数格式不正确")
        text = raw_spec.strip()
        if not text:
            continue
        if len(text) > 120:
            raise ValueError("单项参数不能超过 120 个字符")
        specs.append(text)
    return specs


def profile_for(user):
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={"nickname": user.first_name or user.username},
    )
    return profile


def ban_response(request, profile=None):
    reason = profile.banned_reason if profile and profile.banned_reason else "账号已被封禁"
    return with_cors(JsonResponse({"error": reason}, status=403), request)


def ensure_active_user(request):
    if not request.user.is_authenticated:
        return None
    profile = profile_for(request.user)
    if profile.is_banned or not request.user.is_active:
        logout(request)
        return ban_response(request, profile)
    return None


def author_names_for(user, profile=None):
    if profile is None:
        profile = getattr(user, "profile", None)
    names = [user.username, user.first_name]
    if profile:
        names.append(profile.nickname)
    return [name for name in set(names) if name]


def daily_activity_for(user):
    activity, _ = UserDailyActivity.objects.get_or_create(user=user, date=timezone.localdate())
    return activity


def record_visit(user):
    if not user.is_authenticated:
        return
    activity = daily_activity_for(user)
    activity.visit_count += 1
    activity.save(update_fields=["visit_count", "updated_at"])


def record_active_action(user):
    if not user.is_authenticated:
        return
    activity = daily_activity_for(user)
    activity.active_actions += 1
    activity.save(update_fields=["active_actions", "updated_at"])


def online_points(visit_count):
    if visit_count <= 0:
        return 0
    return min(5, max(1, (visit_count + 3) // 4))


def discussion_points(active_actions):
    if active_actions <= 0:
        return 0
    return min(5, active_actions)


def post_quality_points(post):
    relevance = 10 if post.car_id or post.club_id or post.shop_id else 0
    detail = min(30, len(post.body or "") // 20)
    interaction = post.likes * 5 + post.comments * 10
    featured = 50 if post.featured else 0
    return relevance + detail + interaction + featured


def user_level_points(user, profile=None):
    names = author_names_for(user, profile)
    activities = UserDailyActivity.objects.filter(user=user)
    online_total = sum(online_points(item.visit_count) for item in activities)
    discussion_total = sum(discussion_points(item.active_actions) for item in activities)

    quality_by_day = {}
    owned_posts = Q(owner=user) | Q(owner__isnull=True, author__in=names)
    for post in Post.objects.filter(owned_posts, state=PublishState.PUBLISHED):
        day = timezone.localdate(post.created_at)
        quality_by_day[day] = quality_by_day.get(day, 0) + post_quality_points(post)
    quality_total = sum(min(1000, points) for points in quality_by_day.values())

    social_by_day = {}
    for relation in UserFollow.objects.filter(follower=user):
        day = timezone.localdate(relation.created_at)
        social_by_day[day] = social_by_day.get(day, 0) + 1
    for relation in UserFollow.objects.filter(following=user):
        day = timezone.localdate(relation.created_at)
        social_by_day[day] = social_by_day.get(day, 0) + 1
    social_total = sum(min(2, points) for points in social_by_day.values())

    total = online_total + discussion_total + quality_total + social_total
    return {
        "total": total,
        "online": online_total,
        "discussion": discussion_total,
        "quality": quality_total,
        "social": social_total,
    }


def user_payload(user):
    profile = profile_for(user)
    if user.first_name and not profile.nickname:
        profile.nickname = user.first_name
        profile.save(update_fields=["nickname"])
    names = author_names_for(user, profile)
    posts_count = Post.objects.filter(Q(owner=user) | Q(owner__isnull=True, author__in=names)).count()
    followers_count = user.follower_relations.count()
    following_count = user.following_relations.count()
    points = user_level_points(user, profile)
    activity_points = points["total"]
    level = min(30, activity_points // 100 + 1)
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "nickname": profile.nickname or user.first_name or user.username,
        "avatar": profile.avatar.url if profile.avatar else "",
        "level": level,
        "level_label": f"Lv.{level}",
        "activity_points": activity_points,
        "level_points": points,
        "posts_count": posts_count,
        "followers_count": followers_count,
        "following_count": following_count,
        "signature": profile.signature,
        "is_banned": profile.is_banned,
        "banned_reason": profile.banned_reason,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
    }


def public_user_payload(user, viewer=None):
    private_data = user_payload(user)
    public_fields = (
        "id", "username", "nickname", "avatar", "level", "level_label",
        "activity_points", "posts_count", "followers_count", "following_count", "signature",
    )
    data = {field: private_data[field] for field in public_fields}
    data["is_following"] = bool(
        viewer
        and viewer.is_authenticated
        and viewer.id != user.id
        and UserFollow.objects.filter(follower=viewer, following=user).exists()
    )
    data["can_message"] = bool(viewer and viewer.is_authenticated and viewer.id != user.id)
    return data


def message_payload(message):
    return {
        "id": message.id,
        "sender": public_user_payload(message.sender),
        "receiver": public_user_payload(message.receiver),
        "body": message.body,
        "is_read": message.is_read,
        "time": message.created_at.strftime("%Y-%m-%d %H:%M"),
    }


def garage_vehicle_payload(vehicle):
    return {
        "id": vehicle.id,
        "name": vehicle.custom_name or (vehicle.car.name if vehicle.car else "未命名车辆"),
        "car": vehicle.car.name if vehicle.car else "",
        "car_id": vehicle.car_id,
        "year": vehicle.year,
        "color": vehicle.color,
        "mods": vehicle.mods,
        "created_at": vehicle.created_at.strftime("%Y-%m-%d"),
    }


def project_record_payload(record):
    return {
        "id": record.id,
        "title": record.title,
        "stage": record.stage,
        "content": record.content,
        "vehicle": garage_vehicle_payload(record.vehicle) if record.vehicle else None,
        "created_at": record.created_at.strftime("%Y-%m-%d"),
    }


def public_queryset(model):
    return model.objects.filter(state=PublishState.PUBLISHED)


def clear_other_user_sessions(user, current_session_key=None):
    for session in Session.objects.filter(expire_date__gte=timezone.now()):
        data = session.get_decoded()
        if str(data.get("_auth_user_id")) == str(user.id) and session.session_key != current_session_key:
            session.delete()


def static_asset_url(value):
    if isinstance(value, str) and value.startswith("/assets/"):
        return value.replace("/assets/", "/static/assets/", 1)
    return value


def content_image_url(obj):
    upload = getattr(obj, "image_upload", None)
    if upload:
        return upload.url
    return static_asset_url(getattr(obj, "image", ""))


def relative_time_label(created_at):
    seconds = max(0, int((timezone.now() - created_at).total_seconds()))
    if seconds < 60:
        return "刚刚"
    if seconds < 3600:
        return f"{seconds // 60} 分钟前"
    if seconds < 86400:
        return f"{seconds // 3600} 小时前"
    if seconds < 604800:
        return f"{seconds // 86400} 天前"
    return timezone.localtime(created_at).strftime("%Y-%m-%d")


def post_payload(post, saved_ids=None, liked_ids=None):
    return {
        "id": post.id,
        "type": post.post_type,
        "tone": post.tone,
        "image": content_image_url(post),
        "image_caption": post.image_caption,
        "author": post.author,
        "time": relative_time_label(post.created_at),
        "created_at": post.created_at.isoformat(),
        "title": post.title,
        "body": post.body,
        "club": post.club.name if post.club else "",
        "car": post.car.name if post.car else "",
        "likes": post.likes,
        "comments": post.comments,
        "progress": post.progress,
        "specs": post.specs,
        "location": post.location,
        "is_saved": bool(saved_ids is not None and post.id in saved_ids),
        "is_liked": bool(liked_ids is not None and post.id in liked_ids),
        "featured": post.featured,
        "is_pinned": post.is_pinned,
    }


def comment_payload(comment):
    profile = profile_for(comment.user)
    return {
        "id": comment.id,
        "body": comment.body,
        "author": profile.nickname or comment.user.first_name or comment.user.username,
        "username": comment.user.username,
        "avatar": profile.avatar.url if profile.avatar else "",
        "time": relative_time_label(comment.created_at),
        "created_at": comment.created_at.isoformat(),
    }


def article_block_payload(block):
    return {
        "id": block.id,
        "type": block.block_type,
        "position": block.position,
        "text": block.text,
        "image": content_image_url(block),
        "caption": block.caption,
    }


def article_payload(article, saved_ids=None, liked_ids=None):
    blocks = list(article.blocks.all())
    stored_cover_image = content_image_url(article)
    cover_image = stored_cover_image
    if not cover_image:
        first_image = next((block for block in blocks if block.block_type == "image" and block.image_upload), None)
        cover_image = content_image_url(first_image) if first_image else ""
    owner_profile = profile_for(article.owner) if article.owner else None
    return {
        "id": article.id,
        "title": article.title,
        "slug": article.slug,
        "category": article.category,
        "summary": article.summary,
        "body": article.body,
        "image": cover_image,
        "has_cover": bool(stored_cover_image),
        "image_caption": article.image_caption,
        "author": article.author or (owner_profile.nickname if owner_profile else ""),
        "owner_id": article.owner_id,
        "author_avatar": owner_profile.avatar.url if owner_profile and owner_profile.avatar else "",
        "car": article.car.name if article.car else "",
        "created_at": article.created_at.isoformat(),
        "time": relative_time_label(article.created_at),
        "views": article.views,
        "likes": article.likes,
        "comments": article.comments,
        "is_saved": bool(saved_ids is not None and article.id in saved_ids),
        "is_liked": bool(liked_ids is not None and article.id in liked_ids),
        "featured": article.featured,
        "is_pinned": article.is_pinned,
        "state": article.state,
        "trashed_at": article.trashed_at.isoformat() if article.trashed_at else "",
        "blocks": [article_block_payload(block) for block in blocks],
    }


def trim_payload(trim):
    return {
        "id": trim.id,
        "name": trim.name,
        "car": trim.car.name,
        "engine": trim.engine,
        "horsepower": trim.horsepower,
        "drivetrain": trim.drivetrain,
        "gearbox": trim.gearbox,
        "acceleration": trim.acceleration,
        "fuel": trim.fuel,
        "featured": trim.featured,
    }


def car_payload(car):
    return {
        "id": car.id,
        "name": car.name,
        "heat": car.heat,
        "tag": car.tag,
        "img": content_image_url(car),
        "slug": car.slug,
        "trims": [trim_payload(trim) for trim in car.trims.filter(state=PublishState.PUBLISHED)],
    }


@require_GET
def site_data(request):
    blocked = ensure_active_user(request)
    if blocked:
        return blocked
    if request.user.is_authenticated:
        record_visit(request.user)
    User = get_user_model()
    visible_posts = list(public_queryset(Post).select_related("car", "club", "shop", "owner"))
    visible_articles = list(
        public_queryset(Article)
        .select_related("car", "owner", "owner__profile")
        .prefetch_related("blocks")
    )
    saved_ids = set()
    liked_ids = set()
    saved_article_ids = set()
    liked_article_ids = set()
    if request.user.is_authenticated:
        saved_ids = set(PostSave.objects.filter(user=request.user, post__in=visible_posts).values_list("post_id", flat=True))
        liked_ids = set(PostLike.objects.filter(user=request.user, post__in=visible_posts).values_list("post_id", flat=True))
        saved_article_ids = set(ArticleSave.objects.filter(user=request.user, article__in=visible_articles).values_list("article_id", flat=True))
        liked_article_ids = set(ArticleLike.objects.filter(user=request.user, article__in=visible_articles).values_list("article_id", flat=True))
    data = {
        "posts": [post_payload(post, saved_ids, liked_ids) for post in visible_posts],
        "cars": [car_payload(item) for item in public_queryset(Car).prefetch_related("trims")],
        "trims": [trim_payload(item) for item in public_queryset(CarTrim).select_related("car")],
        "clubs": [[item.short_name, item.name, item.member_count, item.slug, content_image_url(item)] for item in public_queryset(Club)],
        "events": [
            {"img": content_image_url(item), "name": item.name, "meta": item.meta, "count": item.count, "slug": item.slug}
            for item in public_queryset(Event)
        ],
        "shops": [[item.short_name, item.name, str(item.rating), item.services, item.slug, content_image_url(item)] for item in public_queryset(Shop)],
        "market": [
            {"img": content_image_url(item), "name": item.name, "status": "配件动态", "slug": item.slug}
            for item in public_queryset(MarketItem)
        ],
        "topics": [
            {"title": item.title, "count": item.count, "desc": item.desc, "slug": item.slug}
            for item in public_queryset(Topic)
        ],
        "guides": [
            {"id": item.id, "title": item.title, "body": item.body}
            for item in public_queryset(Guide)
        ],
        "articles": [article_payload(item, saved_article_ids, liked_article_ids) for item in visible_articles],
        "users": [
            public_user_payload(item, request.user)
            for item in User.objects.filter(is_active=True).order_by("-date_joined")[:24]
        ],
        "garage": [
            garage_vehicle_payload(item)
            for item in UserGarageVehicle.objects.filter(user=request.user).select_related("car")
        ] if request.user.is_authenticated else [],
        "projects": [
            project_record_payload(item)
            for item in ProjectCarRecord.objects.filter(user=request.user).select_related("vehicle", "vehicle__car")
        ] if request.user.is_authenticated else [],
    }
    return with_cors(JsonResponse(data, json_dumps_params={"ensure_ascii": False}), request)


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def create_garage_vehicle(request):
    if request.method == "OPTIONS":
        return options_response(request)
    if not request.user.is_authenticated:
        return with_cors(JsonResponse({"error": "请先登录再添加车辆"}, status=401), request)
    blocked = ensure_active_user(request)
    if blocked:
        return blocked
    try:
        data = read_json(request)
    except json.JSONDecodeError:
        return with_cors(JsonResponse({"error": "请求格式不正确"}, status=400), request)

    car_id = data.get("car_id")
    car = Car.objects.filter(id=car_id).first() if car_id else None
    custom_name = (data.get("custom_name") or "").strip()
    year = (data.get("year") or "").strip()
    color = (data.get("color") or "").strip()
    mods = (data.get("mods") or "").strip()
    if not car and not custom_name:
        return with_cors(JsonResponse({"error": "请选择车型或输入车辆名称"}, status=400), request)
    if len(custom_name) > 120 or len(year) > 20 or len(color) > 40:
        return with_cors(JsonResponse({"error": "车辆信息长度超出限制"}, status=400), request)
    if len(mods) > 5000:
        return with_cors(JsonResponse({"error": "改装清单不能超过 5000 个字符"}, status=400), request)

    vehicle = UserGarageVehicle.objects.create(
        user=request.user,
        car=car,
        custom_name=custom_name,
        year=year,
        color=color,
        mods=mods,
    )
    record_active_action(request.user)
    return with_cors(JsonResponse({"vehicle": garage_vehicle_payload(vehicle)}, json_dumps_params={"ensure_ascii": False}), request)


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def create_project_record(request):
    if request.method == "OPTIONS":
        return options_response(request)
    if not request.user.is_authenticated:
        return with_cors(JsonResponse({"error": "请先登录再添加项目记录"}, status=401), request)
    blocked = ensure_active_user(request)
    if blocked:
        return blocked
    try:
        data = read_json(request)
    except json.JSONDecodeError:
        return with_cors(JsonResponse({"error": "请求格式不正确"}, status=400), request)

    title = (data.get("title") or "").strip()
    if not title:
        return with_cors(JsonResponse({"error": "请输入记录标题"}, status=400), request)
    stage = (data.get("stage") or "").strip()
    content = (data.get("content") or "").strip()
    if len(title) > 160 or len(stage) > 80:
        return with_cors(JsonResponse({"error": "项目记录信息长度超出限制"}, status=400), request)
    if len(content) > 10000:
        return with_cors(JsonResponse({"error": "记录内容不能超过 10000 个字符"}, status=400), request)
    vehicle_id = data.get("vehicle_id")
    vehicle = UserGarageVehicle.objects.filter(id=vehicle_id, user=request.user).first() if vehicle_id else None
    if vehicle_id and not vehicle:
        return with_cors(JsonResponse({"error": "关联车辆不存在"}, status=400), request)
    record = ProjectCarRecord.objects.create(
        user=request.user,
        vehicle=vehicle,
        title=title,
        stage=stage,
        content=content,
    )
    record_active_action(request.user)
    return with_cors(JsonResponse({"record": project_record_payload(record)}, json_dumps_params={"ensure_ascii": False}), request)


@csrf_exempt
@require_http_methods(["GET", "OPTIONS"])
def current_user(request):
    if request.method == "OPTIONS":
        return options_response(request)
    if not request.user.is_authenticated:
        return with_cors(JsonResponse({"user": None}), request)
    blocked = ensure_active_user(request)
    if blocked:
        return blocked
    record_visit(request.user)
    return with_cors(JsonResponse({"user": user_payload(request.user)}, json_dumps_params={"ensure_ascii": False}), request)


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def register_user(request):
    if request.method == "OPTIONS":
        return options_response(request)
    try:
        data = read_json(request)
    except json.JSONDecodeError:
        return with_cors(JsonResponse({"error": "请求格式不正确"}, status=400), request)

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    email = (data.get("email") or "").strip()
    nickname = (data.get("nickname") or username).strip()

    if not username or not password or not email:
        return with_cors(JsonResponse({"error": "请输入账号、邮箱和密码"}, status=400), request)
    try:
        validate_email(email)
    except ValidationError:
        return with_cors(JsonResponse({"error": "请输入有效的邮箱地址"}, status=400), request)
    if data.get("accepted_terms") is not True:
        return with_cors(JsonResponse({"error": "请先同意用户协议和隐私政策"}, status=400), request)

    User = get_user_model()
    if User.objects.filter(username=username).exists():
        return with_cors(JsonResponse({"error": "账号已存在"}, status=409), request)
    if User.objects.filter(email__iexact=email).exists():
        return with_cors(JsonResponse({"error": "该邮箱已绑定其他账号"}, status=409), request)

    candidate_user = User(username=username, email=email, first_name=nickname)
    try:
        validate_password(password, candidate_user)
    except ValidationError as error:
        return with_cors(JsonResponse({"error": error.messages[0]}, status=400), request)

    user = User.objects.create_user(username=username, password=password, email=email)
    user.first_name = nickname
    user.save(update_fields=["first_name"])
    UserProfile.objects.create(user=user, nickname=nickname)
    login(request, user)
    clear_other_user_sessions(user, request.session.session_key)
    return with_cors(JsonResponse({"user": user_payload(user)}, json_dumps_params={"ensure_ascii": False}), request)


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def login_user(request):
    if request.method == "OPTIONS":
        return options_response(request)
    try:
        data = read_json(request)
    except json.JSONDecodeError:
        return with_cors(JsonResponse({"error": "请求格式不正确"}, status=400), request)

    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    throttle_digest = hashlib.sha256(
        f"{request_client_ip(request)}:{username.lower()}".encode("utf-8")
    ).hexdigest()
    throttle_key = f"login-failures:{throttle_digest}"
    failures = int(cache.get(throttle_key, 0))
    if failures >= 5:
        return with_cors(JsonResponse({"error": "登录尝试次数过多，请 15 分钟后再试"}, status=429), request)

    user = authenticate(request, username=username, password=password)
    if not user:
        cache.set(throttle_key, failures + 1, 900)
        User = get_user_model()
        banned_user = User.objects.filter(username=username).first()
        if banned_user:
            profile = profile_for(banned_user)
            if profile.is_banned:
                return ban_response(request, profile)
        return with_cors(JsonResponse({"error": "账号或密码错误"}, status=401), request)
    profile = profile_for(user)
    if profile.is_banned or not user.is_active:
        return ban_response(request, profile)

    cache.delete(throttle_key)
    login(request, user)
    clear_other_user_sessions(user, request.session.session_key)
    return with_cors(JsonResponse({"user": user_payload(user)}, json_dumps_params={"ensure_ascii": False}), request)


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def logout_user(request):
    if request.method == "OPTIONS":
        return options_response(request)
    logout(request)
    return with_cors(JsonResponse({"ok": True}), request)


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def update_profile(request):
    if request.method == "OPTIONS":
        return options_response(request)
    if not request.user.is_authenticated:
        return with_cors(JsonResponse({"error": "请先登录再修改昵称"}, status=401), request)
    blocked = ensure_active_user(request)
    if blocked:
        return blocked

    try:
        data = read_json(request)
    except json.JSONDecodeError:
        return with_cors(JsonResponse({"error": "请求格式不正确"}, status=400), request)

    nickname = (data.get("nickname") or "").strip()
    if not nickname:
        return with_cors(JsonResponse({"error": "昵称不能为空"}, status=400), request)
    if len(nickname) > 20:
        return with_cors(JsonResponse({"error": "昵称不能超过 20 个字符"}, status=400), request)
    if not nickname.isprintable():
        return with_cors(JsonResponse({"error": "昵称包含无效字符"}, status=400), request)

    profile = profile_for(request.user)
    profile.nickname = nickname
    profile.save(update_fields=["nickname", "updated_at"])
    request.user.first_name = nickname
    request.user.save(update_fields=["first_name"])
    Post.objects.filter(owner=request.user).update(author=nickname)

    return with_cors(JsonResponse({"user": user_payload(request.user)}, json_dumps_params={"ensure_ascii": False}), request)


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def update_email(request):
    if request.method == "OPTIONS":
        return options_response(request)
    if not request.user.is_authenticated:
        return with_cors(JsonResponse({"error": "请先登录再设置邮箱"}, status=401), request)
    blocked = ensure_active_user(request)
    if blocked:
        return blocked

    try:
        data = read_json(request)
    except json.JSONDecodeError:
        return with_cors(JsonResponse({"error": "请求格式不正确"}, status=400), request)

    email = (data.get("email") or "").strip().lower()
    current_password = data.get("current_password") or ""
    if not email or not current_password:
        return with_cors(JsonResponse({"error": "请输入邮箱和当前密码"}, status=400), request)
    try:
        validate_email(email)
    except ValidationError:
        return with_cors(JsonResponse({"error": "请输入有效的邮箱地址"}, status=400), request)
    if not request.user.check_password(current_password):
        return with_cors(JsonResponse({"error": "当前密码不正确"}, status=400), request)

    User = get_user_model()
    if User.objects.filter(email__iexact=email).exclude(pk=request.user.pk).exists():
        return with_cors(JsonResponse({"error": "该邮箱已绑定其他账号"}, status=409), request)

    request.user.email = email
    request.user.save(update_fields=["email"])
    return with_cors(JsonResponse({"user": user_payload(request.user)}, json_dumps_params={"ensure_ascii": False}), request)


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def change_password(request):
    if request.method == "OPTIONS":
        return options_response(request)
    if not request.user.is_authenticated:
        return with_cors(JsonResponse({"error": "请先登录再修改密码"}, status=401), request)
    blocked = ensure_active_user(request)
    if blocked:
        return blocked

    try:
        data = read_json(request)
    except json.JSONDecodeError:
        return with_cors(JsonResponse({"error": "请求格式不正确"}, status=400), request)

    current_password = data.get("current_password") or ""
    new_password = data.get("new_password") or ""
    confirm_password = data.get("confirm_password") or ""
    if not current_password or not new_password or not confirm_password:
        return with_cors(JsonResponse({"error": "请填写完整的密码信息"}, status=400), request)
    if not request.user.check_password(current_password):
        return with_cors(JsonResponse({"error": "当前密码不正确"}, status=400), request)
    if new_password != confirm_password:
        return with_cors(JsonResponse({"error": "两次输入的新密码不一致"}, status=400), request)
    if current_password == new_password:
        return with_cors(JsonResponse({"error": "新密码不能与当前密码相同"}, status=400), request)

    try:
        validate_password(new_password, request.user)
    except ValidationError as error:
        return with_cors(JsonResponse({"error": error.messages[0]}, status=400), request)

    request.user.set_password(new_password)
    request.user.save(update_fields=["password"])
    update_session_auth_hash(request, request.user)
    clear_other_user_sessions(request.user, request.session.session_key)
    return with_cors(JsonResponse({"ok": True}), request)


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def request_password_reset(request):
    if request.method == "OPTIONS":
        return options_response(request)
    try:
        data = read_json(request)
    except json.JSONDecodeError:
        return with_cors(JsonResponse({"error": "请求格式不正确"}, status=400), request)

    email = (data.get("email") or "").strip().lower()
    if not email:
        return with_cors(JsonResponse({"error": "请输入注册邮箱"}, status=400), request)

    client_ip = request_client_ip(request)
    throttle_digest = hashlib.sha256(f"{client_ip}:{email}".encode("utf-8")).hexdigest()
    throttle_key = f"password-reset:{throttle_digest}"
    generic_message = "如果该邮箱已注册，重置链接会发送到邮箱"
    if cache.get(throttle_key):
        return with_cors(JsonResponse({"message": generic_message}), request)
    cache.set(throttle_key, True, 60)

    User = get_user_model()
    users = list(User.objects.filter(email__iexact=email, is_active=True).order_by("id")[:10])
    if users:
        public_url = settings.TUNERHUB_PUBLIC_URL or request.build_absolute_uri("/").rstrip("/")
        reset_entries = []
        for user in users:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = f"{public_url.rstrip('/')}/reset-password/{uid}/{token}"
            reset_entries.append(f"账号：{user.username}\n{reset_url}")
        try:
            send_mail(
                "重置 Tuner Hub 登录密码",
                "你正在重置 Tuner Hub 登录密码。请根据账号打开对应链接：\n\n"
                + "\n\n".join(reset_entries)
                + "\n\n如果不是你本人操作，请忽略此邮件。",
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
        except Exception:
            # Keep the response indistinguishable from an unknown email address.
            pass

    return with_cors(JsonResponse({"message": generic_message}), request)


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def confirm_password_reset(request):
    if request.method == "OPTIONS":
        return options_response(request)
    try:
        data = read_json(request)
    except json.JSONDecodeError:
        return with_cors(JsonResponse({"error": "请求格式不正确"}, status=400), request)

    uid = data.get("uid") or ""
    token = data.get("token") or ""
    new_password = data.get("new_password") or ""
    confirm_password = data.get("confirm_password") or ""
    if not uid or not token or not new_password or not confirm_password:
        return with_cors(JsonResponse({"error": "请填写完整的密码信息"}, status=400), request)
    if new_password != confirm_password:
        return with_cors(JsonResponse({"error": "两次输入的新密码不一致"}, status=400), request)

    User = get_user_model()
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(uid)), is_active=True)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if not user or not default_token_generator.check_token(user, token):
        return with_cors(JsonResponse({"error": "重置链接无效或已过期"}, status=400), request)

    try:
        validate_password(new_password, user)
    except ValidationError as error:
        return with_cors(JsonResponse({"error": error.messages[0]}, status=400), request)

    user.set_password(new_password)
    user.save(update_fields=["password"])
    clear_other_user_sessions(user)
    return with_cors(JsonResponse({"ok": True}), request)


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def upload_avatar(request):
    if request.method == "OPTIONS":
        return options_response(request)
    if not request.user.is_authenticated:
        return with_cors(JsonResponse({"error": "请先登录再上传头像"}, status=401), request)
    blocked = ensure_active_user(request)
    if blocked:
        return blocked

    avatar = request.FILES.get("avatar")
    if not avatar:
        return with_cors(JsonResponse({"error": "请选择头像图片"}, status=400), request)
    image_error = validate_uploaded_image(avatar, label="头像", max_size_mb=5)
    if image_error:
        return with_cors(JsonResponse({"error": image_error}, status=400), request)

    profile, _ = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={"nickname": request.user.first_name or request.user.username},
    )
    old_avatar_name = profile.avatar.name if profile.avatar else ""
    profile.avatar = avatar
    profile.save(update_fields=["avatar", "updated_at"])
    if old_avatar_name and old_avatar_name != profile.avatar.name:
        profile.avatar.storage.delete(old_avatar_name)
    return with_cors(JsonResponse({"user": user_payload(request.user)}, json_dumps_params={"ensure_ascii": False}), request)


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def toggle_follow_user(request, user_id):
    if request.method == "OPTIONS":
        return options_response(request)
    if not request.user.is_authenticated:
        return with_cors(JsonResponse({"error": "请先登录再关注用户"}, status=401), request)
    blocked = ensure_active_user(request)
    if blocked:
        return blocked
    if request.user.id == user_id:
        return with_cors(JsonResponse({"error": "不能关注自己"}, status=400), request)

    User = get_user_model()
    try:
        target = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return with_cors(JsonResponse({"error": "用户不存在"}, status=404), request)

    relation, created = UserFollow.objects.get_or_create(follower=request.user, following=target)
    if not created:
        relation.delete()

    return with_cors(JsonResponse({
        "following": created,
        "current_user": user_payload(request.user),
        "target_user": public_user_payload(target, request.user),
    }, json_dumps_params={"ensure_ascii": False}), request)


@csrf_exempt
@require_http_methods(["GET", "OPTIONS"])
def user_connections(request):
    if request.method == "OPTIONS":
        return options_response(request)
    if not request.user.is_authenticated:
        return with_cors(JsonResponse({"error": "请先登录再查看关注关系"}, status=401), request)
    blocked = ensure_active_user(request)
    if blocked:
        return blocked

    connection_type = request.GET.get("type", "followers")
    if connection_type == "followers":
        relations = UserFollow.objects.filter(
            following=request.user,
            follower__is_active=True,
        ).select_related("follower", "follower__profile")[:200]
        users = [relation.follower for relation in relations]
    elif connection_type == "following":
        relations = UserFollow.objects.filter(
            follower=request.user,
            following__is_active=True,
        ).select_related("following", "following__profile")[:200]
        users = [relation.following for relation in relations]
    else:
        return with_cors(JsonResponse({"error": "关注关系类型无效"}, status=400), request)

    return with_cors(JsonResponse({
        "type": connection_type,
        "count": len(users),
        "users": [public_user_payload(user, request.user) for user in users],
    }, json_dumps_params={"ensure_ascii": False}), request)


@csrf_exempt
@require_http_methods(["GET", "OPTIONS"])
def private_messages(request):
    if request.method == "OPTIONS":
        return options_response(request)
    if not request.user.is_authenticated:
        return with_cors(JsonResponse({"error": "请先登录再查看私信"}, status=401), request)
    blocked = ensure_active_user(request)
    if blocked:
        return blocked
    messages = PrivateMessage.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user)
    ).select_related("sender", "receiver", "sender__profile", "receiver__profile")[:100]
    unread_count = PrivateMessage.objects.filter(receiver=request.user, is_read=False).count()
    return with_cors(JsonResponse({
        "messages": [message_payload(item) for item in messages],
        "unread_count": unread_count,
    }, json_dumps_params={"ensure_ascii": False}), request)


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def mark_private_message_read(request, message_id):
    if request.method == "OPTIONS":
        return options_response(request)
    if not request.user.is_authenticated:
        return with_cors(JsonResponse({"error": "请先登录再查看私信"}, status=401), request)
    blocked = ensure_active_user(request)
    if blocked:
        return blocked
    try:
        message = PrivateMessage.objects.select_related("sender", "receiver").get(id=message_id, receiver=request.user)
    except PrivateMessage.DoesNotExist:
        return with_cors(JsonResponse({"error": "私信不存在"}, status=404), request)
    if not message.is_read:
        message.is_read = True
        message.save(update_fields=["is_read", "updated_at"])
    unread_count = PrivateMessage.objects.filter(receiver=request.user, is_read=False).count()
    return with_cors(JsonResponse({
        "message": message_payload(message),
        "unread_count": unread_count,
    }, json_dumps_params={"ensure_ascii": False}), request)


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def send_private_message(request, user_id):
    if request.method == "OPTIONS":
        return options_response(request)
    if not request.user.is_authenticated:
        return with_cors(JsonResponse({"error": "请先登录再发送私信"}, status=401), request)
    blocked = ensure_active_user(request)
    if blocked:
        return blocked
    if request.user.id == user_id:
        return with_cors(JsonResponse({"error": "不能给自己发私信"}, status=400), request)

    try:
        data = read_json(request)
    except json.JSONDecodeError:
        return with_cors(JsonResponse({"error": "请求格式不正确"}, status=400), request)

    body = (data.get("body") or "").strip()
    if not body:
        return with_cors(JsonResponse({"error": "请输入私信内容"}, status=400), request)
    if len(body) > 2000:
        return with_cors(JsonResponse({"error": "私信不能超过 2000 个字符"}, status=400), request)

    User = get_user_model()
    try:
        receiver = User.objects.get(id=user_id, is_active=True)
    except User.DoesNotExist:
        return with_cors(JsonResponse({"error": "用户不存在"}, status=404), request)

    message = PrivateMessage.objects.create(sender=request.user, receiver=receiver, body=body)
    return with_cors(JsonResponse({"message": message_payload(message)}, json_dumps_params={"ensure_ascii": False}), request)


def normalize_article_blocks(raw_blocks, files, existing_images=None):
    existing_images = existing_images or {}
    if isinstance(raw_blocks, str):
        try:
            raw_blocks = json.loads(raw_blocks)
        except json.JSONDecodeError as error:
            raise ValueError("文章内容格式不正确") from error
    if not isinstance(raw_blocks, list) or not raw_blocks:
        raise ValueError("请添加文章正文")
    if len(raw_blocks) > 40:
        raise ValueError("文章最多添加 40 个内容段落")

    blocks = []
    text_length = 0
    image_count = 0
    for raw_block in raw_blocks:
        if not isinstance(raw_block, dict):
            raise ValueError("文章内容格式不正确")
        block_type = raw_block.get("type")
        if block_type not in {"paragraph", "heading", "image"}:
            raise ValueError("文章中包含不支持的内容类型")
        text = str(raw_block.get("text") or "").strip()
        caption = str(raw_block.get("caption") or "").strip()
        if len(caption) > 200:
            raise ValueError("单张图片说明不能超过 200 个字符")

        upload = None
        existing_image = ""
        if block_type == "image":
            image_count += 1
            if image_count > 20:
                raise ValueError("文章最多添加 20 张正文图片")
            image_key = str(raw_block.get("image_key") or "")
            upload = files.get(image_key)
            if not upload:
                existing_image = existing_images.get(str(raw_block.get("existing_id") or ""), "")
                if not existing_image:
                    raise ValueError("正文图片未成功选择，请重新添加")
            else:
                image_error = validate_uploaded_image(upload, label="正文图片", max_size_mb=10)
                if image_error:
                    raise ValueError(image_error)
        else:
            if not text:
                continue
            limit = 120 if block_type == "heading" else 10000
            if len(text) > limit:
                label = "小标题" if block_type == "heading" else "正文段落"
                raise ValueError(f"{label}内容过长")
            text_length += len(text)

        blocks.append({
            "type": block_type,
            "text": text,
            "caption": caption,
            "upload": upload,
            "existing_image": existing_image,
        })

    if not blocks or text_length == 0:
        raise ValueError("文章至少需要一段文字内容")
    if text_length > 50000:
        raise ValueError("文章正文不能超过 50000 个字符")
    return blocks


def article_payload_for_viewer(article, user):
    saved_ids = {article.id} if user.is_authenticated and ArticleSave.objects.filter(user=user, article=article).exists() else set()
    liked_ids = {article.id} if user.is_authenticated and ArticleLike.objects.filter(user=user, article=article).exists() else set()
    return article_payload(article, saved_ids, liked_ids)


def can_manage_article(user, article):
    return bool(
        user.is_authenticated
        and (user.is_staff or user.is_superuser or article.owner_id == user.id)
    )


def truthy_form_value(value):
    return str(value or "").lower() in {"1", "true", "yes", "on"}


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def create_article(request):
    if request.method == "OPTIONS":
        return options_response(request)
    if not request.user.is_authenticated:
        return with_cors(JsonResponse({"error": "请先登录再发布文章"}, status=401), request)
    blocked = ensure_active_user(request)
    if blocked:
        return blocked

    data = request.POST if request.content_type and request.content_type.startswith("multipart/form-data") else None
    if data is None:
        try:
            data = read_json(request)
        except json.JSONDecodeError:
            return with_cors(JsonResponse({"error": "请求格式不正确"}, status=400), request)

    title = (data.get("title") or "").strip()
    summary = (data.get("summary") or "").strip()
    category = (data.get("category") or "车主故事").strip()
    car_value = (data.get("car") or "").strip()
    cover_caption = (data.get("image_caption") or "").strip()
    if not title:
        return with_cors(JsonResponse({"error": "请输入文章标题"}, status=400), request)
    if len(title) > 180:
        return with_cors(JsonResponse({"error": "文章标题不能超过 180 个字符"}, status=400), request)
    if len(summary) > 500:
        return with_cors(JsonResponse({"error": "文章摘要不能超过 500 个字符"}, status=400), request)
    if len(cover_caption) > 200:
        return with_cors(JsonResponse({"error": "封面说明不能超过 200 个字符"}, status=400), request)
    valid_categories = {choice[0] for choice in Article.CATEGORY_CHOICES}
    if category not in valid_categories:
        return with_cors(JsonResponse({"error": "文章栏目不正确"}, status=400), request)

    cover_image = request.FILES.get("cover_image")
    if cover_caption and not cover_image:
        return with_cors(JsonResponse({"error": "添加封面后才能填写封面说明"}, status=400), request)
    if cover_image:
        image_error = validate_uploaded_image(cover_image, label="文章封面", max_size_mb=10)
        if image_error:
            return with_cors(JsonResponse({"error": image_error}, status=400), request)

    try:
        blocks = normalize_article_blocks(data.get("blocks"), request.FILES)
    except ValueError as error:
        return with_cors(JsonResponse({"error": str(error)}, status=400), request)

    body_parts = []
    for block in blocks:
        if block["type"] == "heading":
            body_parts.append(f"## {block['text']}")
        elif block["type"] == "paragraph":
            body_parts.append(block["text"])
    body = "\n\n".join(body_parts)
    if not summary:
        summary = next((block["text"][:240] for block in blocks if block["type"] == "paragraph"), "")
    car = None
    if car_value:
        car = Car.objects.filter(name=car_value).first() or Car.objects.filter(slug=car_value).first()
    slug_base = slugify(title, allow_unicode=True)[:150] or "article"
    article_slug = f"{slug_base}-{uuid4().hex[:10]}"

    with transaction.atomic():
        article = Article.objects.create(
            title=title,
            slug=article_slug,
            category=category,
            summary=summary,
            body=body,
            image_upload=cover_image,
            image_caption=cover_caption,
            owner=request.user,
            author=profile_for(request.user).nickname or request.user.first_name or request.user.username,
            car=car,
            is_pinned=truthy_form_value(data.get("is_pinned")) if (request.user.is_staff or request.user.is_superuser) else False,
            state=PublishState.PUBLISHED,
        )
        for position, block in enumerate(blocks):
            ArticleBlock.objects.create(
                article=article,
                block_type=block["type"],
                position=position,
                text=block["text"],
                image_upload=block["upload"] or block["existing_image"],
                caption=block["caption"],
            )

    record_active_action(request.user)
    article = Article.objects.select_related("car", "owner", "owner__profile").prefetch_related("blocks").get(id=article.id)
    return with_cors(JsonResponse({"article": article_payload_for_viewer(article, request.user)}, json_dumps_params={"ensure_ascii": False}), request)


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def update_article(request, article_id):
    if request.method == "OPTIONS":
        return options_response(request)
    if not request.user.is_authenticated:
        return with_cors(JsonResponse({"error": "请先登录再编辑文章"}, status=401), request)
    blocked = ensure_active_user(request)
    if blocked:
        return blocked
    try:
        article = Article.objects.select_related("owner", "car").prefetch_related("blocks").get(id=article_id)
    except Article.DoesNotExist:
        return with_cors(JsonResponse({"error": "文章不存在"}, status=404), request)
    if not can_manage_article(request.user, article):
        return with_cors(JsonResponse({"error": "无权编辑这篇文章"}, status=403), request)
    if article.trashed_at:
        return with_cors(JsonResponse({"error": "请先从回收站恢复文章再编辑"}, status=400), request)

    data = request.POST if request.content_type and request.content_type.startswith("multipart/form-data") else None
    if data is None:
        try:
            data = read_json(request)
        except json.JSONDecodeError:
            return with_cors(JsonResponse({"error": "请求格式不正确"}, status=400), request)

    title = (data.get("title") or "").strip()
    summary = (data.get("summary") or "").strip()
    category = (data.get("category") or "车主故事").strip()
    car_value = (data.get("car") or "").strip()
    cover_caption = (data.get("image_caption") or "").strip()
    remove_cover = truthy_form_value(data.get("remove_cover"))
    if not title:
        return with_cors(JsonResponse({"error": "请输入文章标题"}, status=400), request)
    if len(title) > 180:
        return with_cors(JsonResponse({"error": "文章标题不能超过 180 个字符"}, status=400), request)
    if len(summary) > 500:
        return with_cors(JsonResponse({"error": "文章摘要不能超过 500 个字符"}, status=400), request)
    if len(cover_caption) > 200:
        return with_cors(JsonResponse({"error": "封面说明不能超过 200 个字符"}, status=400), request)
    if category not in {choice[0] for choice in Article.CATEGORY_CHOICES}:
        return with_cors(JsonResponse({"error": "文章栏目不正确"}, status=400), request)

    cover_image = request.FILES.get("cover_image")
    if cover_image:
        image_error = validate_uploaded_image(cover_image, label="文章封面", max_size_mb=10)
        if image_error:
            return with_cors(JsonResponse({"error": image_error}, status=400), request)
    has_existing_cover = bool(article.image_upload or article.image) and not remove_cover
    if cover_caption and not (cover_image or has_existing_cover):
        return with_cors(JsonResponse({"error": "添加封面后才能填写封面说明"}, status=400), request)

    existing_blocks = list(article.blocks.all())
    existing_images = {
        str(block.id): block.image_upload.name
        for block in existing_blocks
        if block.block_type == "image" and block.image_upload
    }
    try:
        blocks = normalize_article_blocks(data.get("blocks"), request.FILES, existing_images)
    except ValueError as error:
        return with_cors(JsonResponse({"error": str(error)}, status=400), request)

    body_parts = []
    for block in blocks:
        if block["type"] == "heading":
            body_parts.append(f"## {block['text']}")
        elif block["type"] == "paragraph":
            body_parts.append(block["text"])
    body = "\n\n".join(body_parts)
    if not summary:
        summary = next((block["text"][:240] for block in blocks if block["type"] == "paragraph"), "")
    car = None
    if car_value:
        car = Car.objects.filter(name=car_value).first() or Car.objects.filter(slug=car_value).first()

    old_cover_name = article.image_upload.name if article.image_upload else ""
    old_block_names = set(existing_images.values())
    retained_block_names = {block["existing_image"] for block in blocks if block["existing_image"]}
    with transaction.atomic():
        article.title = title
        article.summary = summary
        article.category = category
        article.body = body
        article.image_caption = cover_caption
        article.car = car
        if request.user.is_staff or request.user.is_superuser:
            article.is_pinned = truthy_form_value(data.get("is_pinned"))
        if cover_image:
            article.image_upload = cover_image
            article.image = ""
        elif remove_cover:
            article.image_upload = ""
            article.image = ""
            article.image_caption = ""
        article.save()

        article.blocks.all().delete()
        for position, block in enumerate(blocks):
            ArticleBlock.objects.create(
                article=article,
                block_type=block["type"],
                position=position,
                text=block["text"],
                image_upload=block["upload"] or block["existing_image"],
                caption=block["caption"],
            )

    block_storage = ArticleBlock._meta.get_field("image_upload").storage
    for image_name in old_block_names - retained_block_names:
        block_storage.delete(image_name)
    if old_cover_name and (cover_image or remove_cover):
        Article._meta.get_field("image_upload").storage.delete(old_cover_name)

    article = Article.objects.select_related("car", "owner", "owner__profile").prefetch_related("blocks").get(id=article.id)
    return with_cors(JsonResponse({"article": article_payload_for_viewer(article, request.user)}, json_dumps_params={"ensure_ascii": False}), request)


@csrf_exempt
@require_http_methods(["GET", "OPTIONS"])
def article_detail(request, article_id):
    if request.method == "OPTIONS":
        return options_response(request)
    blocked = ensure_active_user(request)
    if blocked:
        return blocked
    try:
        article = public_queryset(Article).select_related("car", "owner", "owner__profile").prefetch_related("blocks").get(id=article_id)
    except Article.DoesNotExist:
        return with_cors(JsonResponse({"error": "文章不存在"}, status=404), request)
    Article.objects.filter(id=article.id).update(views=F("views") + 1)
    article.refresh_from_db(fields=["views"])
    comments = ArticleComment.objects.filter(article=article).select_related("user", "user__profile")[:100]
    return with_cors(JsonResponse({
        "article": article_payload_for_viewer(article, request.user),
        "comments": [comment_payload(comment) for comment in comments],
    }, json_dumps_params={"ensure_ascii": False}), request)


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def toggle_article_save(request, article_id):
    if request.method == "OPTIONS":
        return options_response(request)
    if not request.user.is_authenticated:
        return with_cors(JsonResponse({"error": "请先登录再收藏文章"}, status=401), request)
    blocked = ensure_active_user(request)
    if blocked:
        return blocked
    try:
        article = public_queryset(Article).prefetch_related("blocks").get(id=article_id)
    except Article.DoesNotExist:
        return with_cors(JsonResponse({"error": "文章不存在"}, status=404), request)
    relation, created = ArticleSave.objects.get_or_create(user=request.user, article=article)
    if not created:
        relation.delete()
    return with_cors(JsonResponse({"saved": created, "article": article_payload_for_viewer(article, request.user)}, json_dumps_params={"ensure_ascii": False}), request)


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def toggle_article_like(request, article_id):
    if request.method == "OPTIONS":
        return options_response(request)
    if not request.user.is_authenticated:
        return with_cors(JsonResponse({"error": "请先登录再点赞"}, status=401), request)
    blocked = ensure_active_user(request)
    if blocked:
        return blocked
    with transaction.atomic():
        try:
            article = public_queryset(Article).select_for_update().prefetch_related("blocks").get(id=article_id)
        except Article.DoesNotExist:
            return with_cors(JsonResponse({"error": "文章不存在"}, status=404), request)
        relation, created = ArticleLike.objects.get_or_create(user=request.user, article=article)
        if not created:
            relation.delete()
        article.likes = ArticleLike.objects.filter(article=article).count()
        article.save(update_fields=["likes", "updated_at"])
    record_active_action(request.user)
    return with_cors(JsonResponse({"liked": created, "article": article_payload_for_viewer(article, request.user)}, json_dumps_params={"ensure_ascii": False}), request)


@csrf_exempt
@require_http_methods(["GET", "POST", "OPTIONS"])
def article_comments(request, article_id):
    if request.method == "OPTIONS":
        return options_response(request)
    try:
        article = public_queryset(Article).prefetch_related("blocks").get(id=article_id)
    except Article.DoesNotExist:
        return with_cors(JsonResponse({"error": "文章不存在"}, status=404), request)
    if request.method == "GET":
        comments = ArticleComment.objects.filter(article=article).select_related("user", "user__profile")[:100]
        return with_cors(JsonResponse({"comments": [comment_payload(comment) for comment in comments]}, json_dumps_params={"ensure_ascii": False}), request)
    if not request.user.is_authenticated:
        return with_cors(JsonResponse({"error": "请先登录再评论"}, status=401), request)
    blocked = ensure_active_user(request)
    if blocked:
        return blocked
    try:
        data = read_json(request)
    except json.JSONDecodeError:
        return with_cors(JsonResponse({"error": "请求格式不正确"}, status=400), request)
    body = (data.get("body") or "").strip()
    if not body:
        return with_cors(JsonResponse({"error": "请输入评论内容"}, status=400), request)
    if len(body) > 1000:
        return with_cors(JsonResponse({"error": "评论不能超过 1000 个字符"}, status=400), request)
    with transaction.atomic():
        article = Article.objects.select_for_update().get(id=article.id)
        comment = ArticleComment.objects.create(user=request.user, article=article, body=body)
        article.comments = ArticleComment.objects.filter(article=article).count()
        article.save(update_fields=["comments", "updated_at"])
    record_active_action(request.user)
    return with_cors(JsonResponse({
        "comment": comment_payload(comment),
        "article": article_payload_for_viewer(article, request.user),
    }, json_dumps_params={"ensure_ascii": False}), request)


@csrf_exempt
@require_http_methods(["POST", "DELETE", "OPTIONS"])
def delete_article(request, article_id):
    if request.method == "OPTIONS":
        return options_response(request)
    if not request.user.is_authenticated:
        return with_cors(JsonResponse({"error": "请先登录"}, status=401), request)
    blocked = ensure_active_user(request)
    if blocked:
        return blocked
    try:
        article = Article.objects.get(id=article_id)
    except Article.DoesNotExist:
        return with_cors(JsonResponse({"error": "文章不存在"}, status=404), request)
    if not can_manage_article(request.user, article):
        return with_cors(JsonResponse({"error": "无权删除这篇文章"}, status=403), request)
    if not article.trashed_at:
        article.trashed_at = timezone.now()
        article.state = PublishState.HIDDEN
        article.save(update_fields=["trashed_at", "state", "updated_at"])
    return with_cors(JsonResponse({
        "ok": True,
        "id": article_id,
        "trashed_at": article.trashed_at.isoformat(),
    }), request)


@csrf_exempt
@require_http_methods(["GET", "OPTIONS"])
def article_trash(request):
    if request.method == "OPTIONS":
        return options_response(request)
    if not request.user.is_authenticated:
        return with_cors(JsonResponse({"error": "请先登录再查看回收站"}, status=401), request)
    blocked = ensure_active_user(request)
    if blocked:
        return blocked

    queryset = Article.objects.filter(trashed_at__isnull=False)
    if not (request.user.is_staff or request.user.is_superuser):
        queryset = queryset.filter(owner=request.user)
    queryset = queryset.select_related("car", "owner", "owner__profile").prefetch_related("blocks").order_by("-trashed_at")[:200]
    return with_cors(JsonResponse({
        "articles": [article_payload_for_viewer(article, request.user) for article in queryset],
    }, json_dumps_params={"ensure_ascii": False}), request)


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def restore_article(request, article_id):
    if request.method == "OPTIONS":
        return options_response(request)
    if not request.user.is_authenticated:
        return with_cors(JsonResponse({"error": "请先登录"}, status=401), request)
    blocked = ensure_active_user(request)
    if blocked:
        return blocked
    try:
        article = Article.objects.select_related("owner", "car").prefetch_related("blocks").get(id=article_id, trashed_at__isnull=False)
    except Article.DoesNotExist:
        return with_cors(JsonResponse({"error": "回收站中没有这篇文章"}, status=404), request)
    if not can_manage_article(request.user, article):
        return with_cors(JsonResponse({"error": "无权恢复这篇文章"}, status=403), request)

    article.trashed_at = None
    article.state = PublishState.PUBLISHED
    article.save(update_fields=["trashed_at", "state", "updated_at"])
    return with_cors(JsonResponse({
        "article": article_payload_for_viewer(article, request.user),
    }, json_dumps_params={"ensure_ascii": False}), request)


@csrf_exempt
@require_http_methods(["POST", "DELETE", "OPTIONS"])
def permanently_delete_article(request, article_id):
    if request.method == "OPTIONS":
        return options_response(request)
    if not request.user.is_authenticated:
        return with_cors(JsonResponse({"error": "请先登录"}, status=401), request)
    blocked = ensure_active_user(request)
    if blocked:
        return blocked
    try:
        article = Article.objects.prefetch_related("blocks").get(id=article_id, trashed_at__isnull=False)
    except Article.DoesNotExist:
        return with_cors(JsonResponse({"error": "回收站中没有这篇文章"}, status=404), request)
    if not can_manage_article(request.user, article):
        return with_cors(JsonResponse({"error": "无权永久删除这篇文章"}, status=403), request)

    cover_name = article.image_upload.name if article.image_upload else ""
    block_names = [block.image_upload.name for block in article.blocks.all() if block.image_upload]
    with transaction.atomic():
        article.delete()
    if cover_name:
        Article._meta.get_field("image_upload").storage.delete(cover_name)
    block_storage = ArticleBlock._meta.get_field("image_upload").storage
    for image_name in block_names:
        block_storage.delete(image_name)
    return with_cors(JsonResponse({"ok": True, "id": article_id}), request)


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def create_content_report(request):
    if request.method == "OPTIONS":
        return options_response(request)
    if not request.user.is_authenticated:
        return with_cors(JsonResponse({"error": "请先登录再提交举报"}, status=401), request)
    blocked = ensure_active_user(request)
    if blocked:
        return blocked
    try:
        data = read_json(request)
    except json.JSONDecodeError:
        return with_cors(JsonResponse({"error": "请求格式不正确"}, status=400), request)

    target_type = (data.get("target_type") or "").strip()
    try:
        target_id = int(data.get("target_id"))
    except (TypeError, ValueError):
        return with_cors(JsonResponse({"error": "举报内容不存在"}, status=400), request)
    target_models = {"article": Article, "post": Post}
    target_model = target_models.get(target_type)
    if not target_model:
        return with_cors(JsonResponse({"error": "不支持的举报内容类型"}, status=400), request)
    target = public_queryset(target_model).filter(id=target_id).first()
    if not target:
        return with_cors(JsonResponse({"error": "举报内容不存在"}, status=404), request)

    reason = (data.get("reason") or "").strip()
    allowed_reasons = {value for value, _label in ContentReport.REASON_CHOICES}
    if reason not in allowed_reasons:
        return with_cors(JsonResponse({"error": "请选择有效的举报原因"}, status=400), request)
    detail = (data.get("detail") or "").strip()
    if len(detail) > 1000:
        return with_cors(JsonResponse({"error": "补充说明不能超过 1000 个字符"}, status=400), request)

    report, created = ContentReport.objects.get_or_create(
        reporter=request.user,
        target_type=target_type,
        target_id=target_id,
        defaults={"target_title": target.title, "reason": reason, "detail": detail},
    )
    if not created:
        return with_cors(JsonResponse({"error": "你已经举报过这条内容"}, status=409), request)
    return with_cors(JsonResponse({"report": {"id": report.id, "status": report.status}}, json_dumps_params={"ensure_ascii": False}), request)


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def create_post(request):
    if request.method == "OPTIONS":
        return options_response(request)
    if not request.user.is_authenticated:
        return with_cors(JsonResponse({"error": "请先登录再发布"}, status=401), request)
    blocked = ensure_active_user(request)
    if blocked:
        return blocked

    if request.content_type and request.content_type.startswith("multipart/form-data"):
        data = request.POST
    else:
        try:
            data = read_json(request)
        except json.JSONDecodeError:
            return with_cors(JsonResponse({"error": "请求格式不正确"}, status=400), request)

    title = (data.get("title") or "").strip()
    body = (data.get("body") or "").strip()
    post_type = (data.get("type") or "聊车").strip()
    car_value = (data.get("car") or "").strip()
    location = (data.get("location") or "").strip()
    image_caption = (data.get("image_caption") or "").strip()
    if not title or not body:
        return with_cors(JsonResponse({"error": "标题和正文不能为空"}, status=400), request)
    if len(title) > 180:
        return with_cors(JsonResponse({"error": "标题不能超过 180 个字符"}, status=400), request)
    if len(body) > 20000:
        return with_cors(JsonResponse({"error": "正文不能超过 20000 个字符"}, status=400), request)
    if len(location) > 120:
        return with_cors(JsonResponse({"error": "位置不能超过 120 个字符"}, status=400), request)
    if len(image_caption) > 200:
        return with_cors(JsonResponse({"error": "图片说明不能超过 200 个字符"}, status=400), request)

    try:
        specs = normalize_post_specs(data.get("specs"))
    except ValueError as error:
        return with_cors(JsonResponse({"error": str(error)}, status=400), request)

    post_image = request.FILES.get("image")
    image_url = (data.get("image") or "").strip()
    if image_caption and not post_image and not image_url:
        return with_cors(JsonResponse({"error": "添加图片后才能填写图片说明"}, status=400), request)
    if post_image:
        image_error = validate_uploaded_image(post_image, label="帖子图片", max_size_mb=10)
        if image_error:
            return with_cors(JsonResponse({"error": image_error}, status=400), request)

    tone_map = {"聊车": "gray", "改装进度": "blue", "聚会": "purple", "店家施工": "green", "二手市场": "orange"}
    car = None
    if car_value:
        car = Car.objects.filter(name=car_value).first() or Car.objects.filter(slug=car_value).first()
    post = Post.objects.create(
        title=title,
        body=body,
        post_type=post_type if post_type in tone_map else "聊车",
        tone=tone_map.get(post_type, "gray"),
        image="" if post_image else image_url,
        image_upload=post_image,
        image_caption=image_caption,
        owner=request.user,
        author=request.user.first_name or request.user.username,
        time_label="刚刚",
        car=car,
        location=location,
        likes=0,
        comments=0,
        progress=0,
        specs=specs,
        state=PublishState.PUBLISHED,
    )
    record_active_action(request.user)
    return with_cors(JsonResponse({"post": post_payload(post)}, json_dumps_params={"ensure_ascii": False}), request)


def post_payload_for_viewer(post, user):
    saved_ids = {post.id} if user.is_authenticated and PostSave.objects.filter(user=user, post=post).exists() else set()
    liked_ids = {post.id} if user.is_authenticated and PostLike.objects.filter(user=user, post=post).exists() else set()
    return post_payload(post, saved_ids, liked_ids)


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def toggle_post_save(request, post_id):
    if request.method == "OPTIONS":
        return options_response(request)
    if not request.user.is_authenticated:
        return with_cors(JsonResponse({"error": "请先登录再收藏"}, status=401), request)
    blocked = ensure_active_user(request)
    if blocked:
        return blocked
    try:
        post = Post.objects.get(id=post_id, state=PublishState.PUBLISHED)
    except Post.DoesNotExist:
        return with_cors(JsonResponse({"error": "帖子不存在"}, status=404), request)

    relation, created = PostSave.objects.get_or_create(user=request.user, post=post)
    if not created:
        relation.delete()
    return with_cors(JsonResponse({
        "saved": created,
        "post": post_payload_for_viewer(post, request.user),
    }, json_dumps_params={"ensure_ascii": False}), request)


@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def toggle_post_like(request, post_id):
    if request.method == "OPTIONS":
        return options_response(request)
    if not request.user.is_authenticated:
        return with_cors(JsonResponse({"error": "请先登录再点赞"}, status=401), request)
    blocked = ensure_active_user(request)
    if blocked:
        return blocked

    with transaction.atomic():
        try:
            post = Post.objects.select_for_update().get(id=post_id, state=PublishState.PUBLISHED)
        except Post.DoesNotExist:
            return with_cors(JsonResponse({"error": "帖子不存在"}, status=404), request)
        relation, created = PostLike.objects.get_or_create(user=request.user, post=post)
        if not created:
            relation.delete()
        post.likes = PostLike.objects.filter(post=post).count()
        post.save(update_fields=["likes", "updated_at"])

    record_active_action(request.user)
    return with_cors(JsonResponse({
        "liked": created,
        "post": post_payload_for_viewer(post, request.user),
    }, json_dumps_params={"ensure_ascii": False}), request)


@csrf_exempt
@require_http_methods(["GET", "POST", "OPTIONS"])
def post_comments(request, post_id):
    if request.method == "OPTIONS":
        return options_response(request)
    try:
        post = Post.objects.get(id=post_id, state=PublishState.PUBLISHED)
    except Post.DoesNotExist:
        return with_cors(JsonResponse({"error": "帖子不存在"}, status=404), request)

    if request.method == "GET":
        comments = PostComment.objects.filter(post=post).select_related("user", "user__profile")[:100]
        return with_cors(JsonResponse({
            "comments": [comment_payload(comment) for comment in comments],
        }, json_dumps_params={"ensure_ascii": False}), request)

    if not request.user.is_authenticated:
        return with_cors(JsonResponse({"error": "请先登录再评论"}, status=401), request)
    blocked = ensure_active_user(request)
    if blocked:
        return blocked
    try:
        data = read_json(request)
    except json.JSONDecodeError:
        return with_cors(JsonResponse({"error": "请求格式不正确"}, status=400), request)
    body = (data.get("body") or "").strip()
    if not body:
        return with_cors(JsonResponse({"error": "请输入评论内容"}, status=400), request)
    if len(body) > 1000:
        return with_cors(JsonResponse({"error": "评论不能超过 1000 个字符"}, status=400), request)

    with transaction.atomic():
        post = Post.objects.select_for_update().get(id=post.id)
        comment = PostComment.objects.create(user=request.user, post=post, body=body)
        post.comments = PostComment.objects.filter(post=post).count()
        post.save(update_fields=["comments", "updated_at"])
    record_active_action(request.user)
    return with_cors(JsonResponse({
        "comment": comment_payload(comment),
        "post": post_payload_for_viewer(post, request.user),
    }, json_dumps_params={"ensure_ascii": False}), request)


@csrf_exempt
@require_http_methods(["POST", "DELETE", "OPTIONS"])
def delete_post(request, post_id):
    if request.method == "OPTIONS":
        return options_response(request)
    if not request.user.is_authenticated:
        return with_cors(JsonResponse({"error": "请先登录"}, status=401), request)
    blocked = ensure_active_user(request)
    if blocked:
        return blocked
    if not (request.user.is_staff or request.user.is_superuser):
        return with_cors(JsonResponse({"error": "只有管理员可以删除社区内容"}, status=403), request)

    try:
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:
        return with_cors(JsonResponse({"error": "帖子不存在"}, status=404), request)

    post.delete()
    return with_cors(JsonResponse({"ok": True, "id": post_id}), request)
