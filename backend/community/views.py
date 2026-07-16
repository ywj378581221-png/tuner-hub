import json
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods
from .models import Article, Car, CarTrim, Club, Event, Guide, MarketItem, Post, PrivateMessage, ProjectCarRecord, PublishState, Shop, Topic, UserDailyActivity, UserFollow, UserGarageVehicle, UserProfile


def with_cors(response, request=None):
    origin = request.headers.get("Origin") if request else None
    response["Access-Control-Allow-Origin"] = origin or "*"
    response["Access-Control-Allow-Credentials"] = "true"
    response["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
    response["Access-Control-Allow-Headers"] = "Content-Type"
    response["Vary"] = "Origin"
    return response


def options_response(request):
    return with_cors(JsonResponse({}), request)


def read_json(request):
    if not request.body:
      return {}
    return json.loads(request.body.decode("utf-8"))


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
    for post in Post.objects.filter(author__in=names, state=PublishState.PUBLISHED):
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
    posts_count = Post.objects.filter(author__in=author_names_for(user, profile)).count()
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
    data = user_payload(user)
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


def post_payload(post):
    return {
        "id": post.id,
        "type": post.post_type,
        "tone": post.tone,
        "image": content_image_url(post),
        "author": post.author,
        "time": post.time_label,
        "title": post.title,
        "body": post.body,
        "club": post.club.name if post.club else "",
        "car": post.car.name if post.car else "",
        "likes": post.likes,
        "comments": post.comments,
        "progress": post.progress,
        "specs": post.specs,
        "featured": post.featured,
    }


def article_payload(article):
    return {
        "id": article.id,
        "title": article.title,
        "slug": article.slug,
        "category": article.category,
        "summary": article.summary,
        "body": article.body,
        "image": content_image_url(article),
        "author": article.author,
        "car": article.car.name if article.car else "",
        "featured": article.featured,
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
    data = {
        "posts": [post_payload(post) for post in public_queryset(Post).select_related("car", "club", "shop")],
        "cars": [car_payload(item) for item in public_queryset(Car).prefetch_related("trims")],
        "trims": [trim_payload(item) for item in public_queryset(CarTrim).select_related("car")],
        "clubs": [[item.short_name, item.name, item.member_count, item.slug] for item in public_queryset(Club)],
        "events": [
            {"img": content_image_url(item), "name": item.name, "meta": item.meta, "count": item.count, "slug": item.slug}
            for item in public_queryset(Event)
        ],
        "shops": [[item.short_name, item.name, str(item.rating), item.services, item.slug] for item in public_queryset(Shop)],
        "market": [
            {"img": content_image_url(item), "name": item.name, "status": "配件动态", "slug": item.slug}
            for item in public_queryset(MarketItem)
        ],
        "topics": [
            {"title": item.title, "count": item.count, "desc": item.desc, "slug": item.slug}
            for item in public_queryset(Topic)
        ],
        "guides": [item.title for item in public_queryset(Guide)],
        "articles": [article_payload(item) for item in public_queryset(Article).select_related("car")],
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
    if not car and not custom_name:
        return with_cors(JsonResponse({"error": "请选择车型或输入车辆名称"}, status=400), request)

    vehicle = UserGarageVehicle.objects.create(
        user=request.user,
        car=car,
        custom_name=custom_name,
        year=(data.get("year") or "").strip(),
        color=(data.get("color") or "").strip(),
        mods=(data.get("mods") or "").strip(),
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
    vehicle = UserGarageVehicle.objects.filter(id=data.get("vehicle_id"), user=request.user).first() if data.get("vehicle_id") else None
    record = ProjectCarRecord.objects.create(
        user=request.user,
        vehicle=vehicle,
        title=title,
        stage=(data.get("stage") or "").strip(),
        content=(data.get("content") or "").strip(),
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

    if not username or not password:
        return with_cors(JsonResponse({"error": "请输入账号和密码"}, status=400), request)
    if len(password) < 6:
        return with_cors(JsonResponse({"error": "密码至少需要 6 位"}, status=400), request)

    User = get_user_model()
    if User.objects.filter(username=username).exists():
        return with_cors(JsonResponse({"error": "账号已存在"}, status=409), request)

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
    user = authenticate(request, username=username, password=password)
    if not user:
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
    old_names = author_names_for(request.user, profile)
    profile.nickname = nickname
    profile.save(update_fields=["nickname", "updated_at"])
    request.user.first_name = nickname
    request.user.save(update_fields=["first_name"])
    Post.objects.filter(author__in=old_names).update(author=nickname)

    return with_cors(JsonResponse({"user": user_payload(request.user)}, json_dumps_params={"ensure_ascii": False}), request)


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
    if avatar.content_type and not avatar.content_type.startswith("image/"):
        return with_cors(JsonResponse({"error": "头像必须是图片文件"}, status=400), request)

    profile, _ = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={"nickname": request.user.first_name or request.user.username},
    )
    profile.avatar = avatar
    profile.save(update_fields=["avatar", "updated_at"])
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
        "target_user": user_payload(target),
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
    messages = PrivateMessage.objects.filter(receiver=request.user).select_related("sender", "receiver")[:50]
    return with_cors(JsonResponse({"messages": [message_payload(item) for item in messages]}, json_dumps_params={"ensure_ascii": False}), request)


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

    User = get_user_model()
    try:
        receiver = User.objects.get(id=user_id, is_active=True)
    except User.DoesNotExist:
        return with_cors(JsonResponse({"error": "用户不存在"}, status=404), request)

    message = PrivateMessage.objects.create(sender=request.user, receiver=receiver, body=body)
    return with_cors(JsonResponse({"message": message_payload(message)}, json_dumps_params={"ensure_ascii": False}), request)


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

    try:
        data = read_json(request)
    except json.JSONDecodeError:
        return with_cors(JsonResponse({"error": "请求格式不正确"}, status=400), request)

    title = (data.get("title") or "").strip()
    body = (data.get("body") or "").strip()
    post_type = (data.get("type") or "改装进度").strip()
    car_value = (data.get("car") or "").strip()
    if not title or not body:
        return with_cors(JsonResponse({"error": "标题和正文不能为空"}, status=400), request)

    tone_map = {"改装进度": "blue", "聚会": "purple", "店家施工": "green", "二手市场": "orange"}
    car = None
    if car_value:
        car = Car.objects.filter(name=car_value).first() or Car.objects.filter(slug=car_value).first()
    post = Post.objects.create(
        title=title,
        body=body,
        post_type=post_type if post_type in tone_map else "改装进度",
        tone=tone_map.get(post_type, "blue"),
        image=data.get("image") or "/assets/supra-garage.png",
        author=request.user.first_name or request.user.username,
        time_label="刚刚",
        car=car,
        likes=0,
        comments=0,
        progress=0,
        specs=[],
        state=PublishState.PUBLISHED,
    )
    record_active_action(request.user)
    return with_cors(JsonResponse({"post": post_payload(post)}, json_dumps_params={"ensure_ascii": False}), request)


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
