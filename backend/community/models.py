from django.db import models
from django.conf import settings


class PublishState(models.TextChoices):
    DRAFT = "draft", "草稿"
    PUBLISHED = "published", "已发布"
    HIDDEN = "hidden", "已隐藏"


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        abstract = True


class UserProfile(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, verbose_name="用户", related_name="profile", on_delete=models.CASCADE)
    nickname = models.CharField("昵称", max_length=80, blank=True)
    avatar = models.FileField("头像", upload_to="avatars/", blank=True)
    signature = models.CharField("个人签名", max_length=160, blank=True)
    is_banned = models.BooleanField("已封禁", default=False)
    banned_reason = models.CharField("封禁原因", max_length=200, blank=True)
    banned_at = models.DateTimeField("封禁时间", null=True, blank=True)

    class Meta:
        verbose_name = "用户资料"
        verbose_name_plural = "用户资料"
        ordering = ["user__username"]

    def __str__(self):
        return self.nickname or self.user.get_username()


class UserDailyActivity(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="用户", related_name="daily_activities", on_delete=models.CASCADE)
    date = models.DateField("日期")
    visit_count = models.PositiveIntegerField("访问记录", default=0)
    active_actions = models.PositiveIntegerField("主动行为", default=0)

    class Meta:
        verbose_name = "用户每日活跃"
        verbose_name_plural = "用户每日活跃"
        unique_together = ("user", "date")
        ordering = ["-date", "user__username"]

    def __str__(self):
        return f"{self.user} {self.date}"


class UserGarageVehicle(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="用户", related_name="garage_vehicles", on_delete=models.CASCADE)
    car = models.ForeignKey("Car", verbose_name="车型", related_name="garage_vehicles", on_delete=models.SET_NULL, null=True, blank=True)
    custom_name = models.CharField("车辆名称", max_length=120, blank=True)
    year = models.CharField("年份", max_length=20, blank=True)
    color = models.CharField("颜色", max_length=40, blank=True)
    mods = models.TextField("改装清单", blank=True)

    class Meta:
        verbose_name = "车库车辆"
        verbose_name_plural = "车库车辆"
        ordering = ["-created_at"]

    def __str__(self):
        return self.custom_name or (self.car.name if self.car else self.user.get_username())


class ProjectCarRecord(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="用户", related_name="project_records", on_delete=models.CASCADE)
    vehicle = models.ForeignKey(UserGarageVehicle, verbose_name="车库车辆", related_name="project_records", on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField("记录标题", max_length=160)
    stage = models.CharField("阶段", max_length=80, blank=True)
    content = models.TextField("记录内容", blank=True)

    class Meta:
        verbose_name = "项目车记录"
        verbose_name_plural = "项目车记录"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class UserFollow(TimeStampedModel):
    follower = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="关注者", related_name="following_relations", on_delete=models.CASCADE)
    following = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="被关注者", related_name="follower_relations", on_delete=models.CASCADE)

    class Meta:
        verbose_name = "用户关注"
        verbose_name_plural = "用户关注"
        unique_together = ("follower", "following")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.follower} -> {self.following}"


class PrivateMessage(TimeStampedModel):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="发送者", related_name="sent_private_messages", on_delete=models.CASCADE)
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="接收者", related_name="received_private_messages", on_delete=models.CASCADE)
    body = models.TextField("私信内容")
    is_read = models.BooleanField("已读", default=False)

    class Meta:
        verbose_name = "私信"
        verbose_name_plural = "私信"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.sender} -> {self.receiver}: {self.body[:24]}"


class Car(TimeStampedModel):
    name = models.CharField("车型名称", max_length=120, unique=True)
    slug = models.SlugField("路由标识", max_length=140, unique=True)
    price = models.CharField("价格区间", max_length=120, blank=True)
    tag = models.CharField("车型标签", max_length=80, blank=True)
    heat = models.CharField("改装热度", max_length=120, blank=True)
    image = models.CharField("图片地址", max_length=300, blank=True)
    image_upload = models.FileField("上传图片", upload_to="cars/", blank=True)
    state = models.CharField("发布状态", max_length=20, choices=PublishState.choices, default=PublishState.PUBLISHED)

    class Meta:
        verbose_name = "车型"
        verbose_name_plural = "车型"
        ordering = ["name"]

    def __str__(self):
        return self.name


class CarTrim(TimeStampedModel):
    car = models.ForeignKey(Car, verbose_name="所属车型", related_name="trims", on_delete=models.CASCADE)
    name = models.CharField("车款名称", max_length=160)
    official_price = models.CharField("指导价", max_length=80, blank=True)
    dealer_price = models.CharField("参考成交价", max_length=80, blank=True)
    engine = models.CharField("发动机/动力", max_length=120, blank=True)
    horsepower = models.CharField("最大功率", max_length=80, blank=True)
    drivetrain = models.CharField("驱动形式", max_length=80, blank=True)
    gearbox = models.CharField("变速箱", max_length=100, blank=True)
    acceleration = models.CharField("0-100km/h", max_length=80, blank=True)
    fuel = models.CharField("能源类型", max_length=80, default="汽油")
    featured = models.BooleanField("推荐车款", default=False)
    state = models.CharField("发布状态", max_length=20, choices=PublishState.choices, default=PublishState.PUBLISHED)

    class Meta:
        verbose_name = "车款配置"
        verbose_name_plural = "车款配置"
        ordering = ["car__name", "-featured", "official_price", "name"]
        unique_together = ("car", "name")

    def __str__(self):
        return f"{self.car.name} {self.name}"


class Club(TimeStampedModel):
    short_name = models.CharField("简称", max_length=20)
    name = models.CharField("车友会名称", max_length=120, unique=True)
    slug = models.SlugField("路由标识", max_length=140, unique=True)
    member_count = models.CharField("成员数量", max_length=80, blank=True)
    image = models.CharField("图片地址", max_length=300, blank=True)
    image_upload = models.FileField("上传图片", upload_to="clubs/", blank=True)
    state = models.CharField("发布状态", max_length=20, choices=PublishState.choices, default=PublishState.PUBLISHED)

    class Meta:
        verbose_name = "车友会"
        verbose_name_plural = "车友会"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Shop(TimeStampedModel):
    short_name = models.CharField("简称", max_length=20)
    name = models.CharField("店家名称", max_length=120, unique=True)
    slug = models.SlugField("路由标识", max_length=140, unique=True)
    rating = models.DecimalField("评分", max_digits=3, decimal_places=1, default=5.0)
    services = models.CharField("服务范围", max_length=180, blank=True)
    image = models.CharField("图片地址", max_length=300, blank=True)
    image_upload = models.FileField("上传图片", upload_to="shops/", blank=True)
    certified = models.BooleanField("TH 认证", default=True)
    state = models.CharField("发布状态", max_length=20, choices=PublishState.choices, default=PublishState.PUBLISHED)

    class Meta:
        verbose_name = "改装店"
        verbose_name_plural = "改装店"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Post(TimeStampedModel):
    TYPE_CHOICES = [
        ("聊车", "聊车"),
        ("改装进度", "改装进度"),
        ("聚会", "聚会"),
        ("店家施工", "店家施工"),
        ("二手市场", "二手市场"),
    ]

    title = models.CharField("标题", max_length=180)
    body = models.TextField("正文")
    post_type = models.CharField("内容类型", max_length=30, choices=TYPE_CHOICES, default="聊车")
    tone = models.CharField("颜色标识", max_length=20, default="gray")
    image = models.CharField("图片地址", max_length=300, blank=True)
    image_upload = models.FileField("上传图片", upload_to="posts/", blank=True)
    image_caption = models.CharField("图片说明", max_length=200, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="发布用户", related_name="community_posts", on_delete=models.SET_NULL, null=True, blank=True)
    author = models.CharField("作者", max_length=120, blank=True)
    time_label = models.CharField("时间显示", max_length=80, blank=True)
    car = models.ForeignKey(Car, verbose_name="关联车型", on_delete=models.SET_NULL, null=True, blank=True)
    club = models.ForeignKey(Club, verbose_name="关联车友会", on_delete=models.SET_NULL, null=True, blank=True)
    shop = models.ForeignKey(Shop, verbose_name="关联店家", on_delete=models.SET_NULL, null=True, blank=True)
    likes = models.PositiveIntegerField("点赞数", default=0)
    comments = models.PositiveIntegerField("评论数", default=0)
    progress = models.PositiveIntegerField("项目进度", default=0)
    specs = models.JSONField("配置参数", default=list, blank=True)
    location = models.CharField("位置", max_length=120, blank=True)
    is_pinned = models.BooleanField("置顶", default=False)
    featured = models.BooleanField("首页精选", default=False)
    state = models.CharField("发布状态", max_length=20, choices=PublishState.choices, default=PublishState.PUBLISHED)

    class Meta:
        verbose_name = "帖子"
        verbose_name_plural = "帖子"
        ordering = ["-is_pinned", "-created_at"]

    def __str__(self):
        return self.title


class PostSave(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="用户", related_name="saved_posts", on_delete=models.CASCADE)
    post = models.ForeignKey(Post, verbose_name="帖子", related_name="saves", on_delete=models.CASCADE)

    class Meta:
        verbose_name = "帖子收藏"
        verbose_name_plural = "帖子收藏"
        constraints = [models.UniqueConstraint(fields=("user", "post"), name="unique_user_post_save")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} 收藏 {self.post}"


class PostLike(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="用户", related_name="liked_posts", on_delete=models.CASCADE)
    post = models.ForeignKey(Post, verbose_name="帖子", related_name="like_relations", on_delete=models.CASCADE)

    class Meta:
        verbose_name = "帖子点赞"
        verbose_name_plural = "帖子点赞"
        constraints = [models.UniqueConstraint(fields=("user", "post"), name="unique_user_post_like")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} 点赞 {self.post}"


class PostComment(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="用户", related_name="post_comments", on_delete=models.CASCADE)
    post = models.ForeignKey(Post, verbose_name="帖子", related_name="comment_records", on_delete=models.CASCADE)
    body = models.TextField("评论内容")

    class Meta:
        verbose_name = "帖子评论"
        verbose_name_plural = "帖子评论"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.user}: {self.body[:24]}"


class Event(TimeStampedModel):
    name = models.CharField("活动名称", max_length=140, unique=True)
    slug = models.SlugField("路由标识", max_length=160, unique=True)
    image = models.CharField("图片地址", max_length=300, blank=True)
    image_upload = models.FileField("上传图片", upload_to="events/", blank=True)
    meta = models.CharField("时间地点", max_length=120, blank=True)
    count = models.CharField("报名人数", max_length=80, blank=True)
    state = models.CharField("发布状态", max_length=20, choices=PublishState.choices, default=PublishState.PUBLISHED)

    class Meta:
        verbose_name = "活动"
        verbose_name_plural = "活动"
        ordering = ["name"]

    def __str__(self):
        return self.name


class MarketItem(TimeStampedModel):
    name = models.CharField("商品名称", max_length=140, unique=True)
    slug = models.SlugField("路由标识", max_length=160, unique=True)
    image = models.CharField("图片地址", max_length=300, blank=True)
    image_upload = models.FileField("上传图片", upload_to="market/", blank=True)
    price = models.CharField("价格", max_length=80, blank=True)
    state = models.CharField("发布状态", max_length=20, choices=PublishState.choices, default=PublishState.PUBLISHED)

    class Meta:
        verbose_name = "二手件"
        verbose_name_plural = "二手件"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Topic(TimeStampedModel):
    title = models.CharField("专题标题", max_length=140, unique=True)
    slug = models.SlugField("路由标识", max_length=160, unique=True)
    count = models.CharField("内容数量", max_length=80, blank=True)
    desc = models.TextField("专题简介", blank=True)
    state = models.CharField("发布状态", max_length=20, choices=PublishState.choices, default=PublishState.PUBLISHED)

    class Meta:
        verbose_name = "专题"
        verbose_name_plural = "专题"
        ordering = ["title"]

    def __str__(self):
        return self.title


class Guide(TimeStampedModel):
    title = models.CharField("导购标题", max_length=180, unique=True)
    body = models.TextField("正文", blank=True)
    state = models.CharField("发布状态", max_length=20, choices=PublishState.choices, default=PublishState.PUBLISHED)

    class Meta:
        verbose_name = "导购文章"
        verbose_name_plural = "导购文章"
        ordering = ["title"]

    def __str__(self):
        return self.title


class Article(TimeStampedModel):
    CATEGORY_CHOICES = [
        ("车主故事", "车主故事"),
        ("长期用车", "长期用车"),
        ("改装案例", "改装案例"),
        ("资讯", "资讯"),
        ("评测", "评测"),
        ("导购", "导购"),
        ("视频", "视频"),
    ]

    title = models.CharField("文章标题", max_length=180)
    slug = models.SlugField("路由标识", max_length=200, unique=True)
    category = models.CharField("栏目", max_length=30, choices=CATEGORY_CHOICES, default="车主故事")
    summary = models.TextField("摘要", blank=True)
    body = models.TextField("正文", blank=True)
    image = models.CharField("封面图", max_length=300, blank=True)
    image_upload = models.FileField("上传封面图", upload_to="articles/", blank=True)
    image_caption = models.CharField("图片说明", max_length=200, blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="发布用户", related_name="community_articles", on_delete=models.SET_NULL, null=True, blank=True)
    author = models.CharField("作者", max_length=120, blank=True, default="")
    car = models.ForeignKey(Car, verbose_name="关联车型", on_delete=models.SET_NULL, null=True, blank=True)
    views = models.PositiveIntegerField("阅读数", default=0)
    likes = models.PositiveIntegerField("点赞数", default=0)
    comments = models.PositiveIntegerField("评论数", default=0)
    is_pinned = models.BooleanField("置顶", default=False)
    featured = models.BooleanField("首页推荐", default=False)
    state = models.CharField("发布状态", max_length=20, choices=PublishState.choices, default=PublishState.PUBLISHED)

    class Meta:
        verbose_name = "资讯文章"
        verbose_name_plural = "资讯文章"
        ordering = ["-is_pinned", "-created_at"]

    def __str__(self):
        return self.title


class ArticleBlock(TimeStampedModel):
    TYPE_CHOICES = [
        ("paragraph", "正文段落"),
        ("heading", "小标题"),
        ("image", "正文图片"),
    ]

    article = models.ForeignKey(Article, verbose_name="文章", related_name="blocks", on_delete=models.CASCADE)
    block_type = models.CharField("内容类型", max_length=20, choices=TYPE_CHOICES)
    position = models.PositiveIntegerField("顺序", default=0)
    text = models.TextField("文字内容", blank=True)
    image_upload = models.FileField("正文图片", upload_to="article_blocks/", blank=True)
    caption = models.CharField("图片说明", max_length=200, blank=True)

    class Meta:
        verbose_name = "文章内容块"
        verbose_name_plural = "文章内容块"
        ordering = ["position", "id"]
        constraints = [models.UniqueConstraint(fields=("article", "position"), name="unique_article_block_position")]

    def __str__(self):
        return f"{self.article.title} #{self.position + 1}"


class ArticleSave(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="用户", related_name="saved_articles", on_delete=models.CASCADE)
    article = models.ForeignKey(Article, verbose_name="文章", related_name="saves", on_delete=models.CASCADE)

    class Meta:
        verbose_name = "文章收藏"
        verbose_name_plural = "文章收藏"
        constraints = [models.UniqueConstraint(fields=("user", "article"), name="unique_user_article_save")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} 收藏 {self.article}"


class ArticleLike(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="用户", related_name="liked_articles", on_delete=models.CASCADE)
    article = models.ForeignKey(Article, verbose_name="文章", related_name="like_relations", on_delete=models.CASCADE)

    class Meta:
        verbose_name = "文章点赞"
        verbose_name_plural = "文章点赞"
        constraints = [models.UniqueConstraint(fields=("user", "article"), name="unique_user_article_like")]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} 点赞 {self.article}"


class ArticleComment(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="用户", related_name="article_comments", on_delete=models.CASCADE)
    article = models.ForeignKey(Article, verbose_name="文章", related_name="comment_records", on_delete=models.CASCADE)
    body = models.TextField("评论内容")

    class Meta:
        verbose_name = "文章评论"
        verbose_name_plural = "文章评论"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.user}: {self.body[:24]}"


class DealerOffer(TimeStampedModel):
    dealer_name = models.CharField("经销商名称", max_length=140)
    city = models.CharField("城市", max_length=80, blank=True)
    car = models.ForeignKey(Car, verbose_name="报价车型", on_delete=models.CASCADE)
    guide_price = models.CharField("指导价", max_length=80, blank=True)
    dealer_price = models.CharField("经销商报价", max_length=80, blank=True)
    discount = models.CharField("优惠信息", max_length=120, blank=True)
    phone = models.CharField("联系电话", max_length=80, blank=True)
    state = models.CharField("发布状态", max_length=20, choices=PublishState.choices, default=PublishState.PUBLISHED)

    class Meta:
        verbose_name = "经销商报价"
        verbose_name_plural = "经销商报价"
        ordering = ["city", "dealer_name"]

    def __str__(self):
        return f"{self.dealer_name} - {self.car.name}"


class DealerLead(TimeStampedModel):
    STATUS_CHOICES = [
        ("new", "新线索"),
        ("contacted", "已联系"),
        ("closed", "已成交"),
        ("invalid", "无效"),
    ]

    name = models.CharField("姓名", max_length=80)
    phone = models.CharField("手机号", max_length=40)
    city = models.CharField("城市", max_length=80, blank=True)
    car = models.ForeignKey(Car, verbose_name="意向车型", on_delete=models.SET_NULL, null=True, blank=True)
    dealer_name = models.CharField("意向经销商", max_length=140, blank=True)
    source = models.CharField("来源页面", max_length=120, blank=True)
    note = models.TextField("备注", blank=True)
    status = models.CharField("跟进状态", max_length=20, choices=STATUS_CHOICES, default="new")

    class Meta:
        verbose_name = "询价线索"
        verbose_name_plural = "询价线索"
        ordering = ["-created_at"]

    def __str__(self):
        car_name = self.car.name if self.car else "未选车型"
        return f"{self.name} - {car_name}"
