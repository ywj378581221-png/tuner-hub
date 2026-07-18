<script setup>
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  PhBell as Bell,
  PhArrowDown as ArrowDown,
  PhArrowUp as ArrowUp,
  PhBookmarkSimple as BookmarkSimple,
  PhCalendarBlank as CalendarBlank,
  PhChatCircle as ChatCircle,
  PhCheckCircle as CheckCircle,
  PhCompass as Compass,
  PhFunnel as Funnel,
  PhFlag as Flag,
  PhGauge as Gauge,
  PhHouse as House,
  PhImage as ImageIcon,
  PhList as List,
  PhMagnifyingGlass as MagnifyingGlass,
  PhMapPin as MapPin,
  PhPaperPlaneTilt as PaperPlaneTilt,
  PhPlus as Plus,
  PhSlidersHorizontal as SlidersHorizontal,
  PhSparkle as Sparkle,
  PhStar as Star,
  PhTrash as Trash,
  PhUsersThree as UsersThree,
  PhWrench as Wrench,
  PhX as X,
} from "@phosphor-icons/vue";

const assetPath = (file) => `${import.meta.env.BASE_URL}assets/${file}`;

const assets = {
  hero: assetPath("hero-night-runners.png"),
  engine: assetPath("engine-rb26.png"),
  meet: assetPath("night-meet.png"),
  shop: assetPath("shop-install.png"),
  exhaust: assetPath("exhaust.png"),
  supra: assetPath("supra-garage.png"),
  wrx: assetPath("wrx-garage.png"),
  bmwM: assetPath("car-bmw-m.jpg"),
  amg: assetPath("car-amg.jpg"),
  audiRs: assetPath("car-audi-rs.jpg"),
  jdm: assetPath("car-jdm.jpg"),
};

const defaultAvatar = `data:image/svg+xml;charset=UTF-8,${encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120" viewBox="0 0 120 120"><rect width="120" height="120" fill="#eeeeee"/><text x="60" y="69" text-anchor="middle" font-family="Arial,sans-serif" font-size="34" font-weight="700" fill="#333333">TH</text></svg>')}`;
const fallbackImage = assetPath("car-jdm.jpg");
const navItems = ["首页", "选车", "文章", "车友圈", "配件专区", "排行榜"];
const navIcons = [House, Compass, Gauge, ChatCircle, Wrench, Star];
const routePaths = ["/", "/cars", "/reviews", "/community", "/market", "/rankings"];
const feedFilters = ["全部", "聊车", "改装进度", "聚会", "店家施工", "二手市场"];
const driveFilters = ["全部驱动", "前置后驱", "全时四驱", "ATTESA 四驱"];
const quickLinks = [
  ["我的车库", "/garage"],
  ["项目车记录", "/projects"],
  ["收藏内容", "/saved"],
  ["活动日历", "/events"],
];

const publicInfoPages = {
  "/terms": {
    title: "用户协议",
    intro: "注册或使用 Tuner Hub，即表示你同意遵守以下基本规则。",
    sections: [
      ["真实使用", "请使用真实、合法的信息参与交流，不冒充他人，不批量注册或滥用账号。"],
      ["内容责任", "发布者应确保文字、图片和改装信息拥有合法来源，不侵犯他人的隐私、肖像、商标或著作权。"],
      ["安全边界", "禁止发布危险驾驶教学、违法改装交易、诈骗、骚扰及其他违反法律法规的内容。"],
      ["社区管理", "平台可以对违规内容采取隐藏、删除、限制发布或封禁账号等措施，并保留必要的操作记录。"],
    ],
  },
  "/privacy": {
    title: "隐私政策",
    intro: "Tuner Hub 只收集提供账号和社区功能所必需的信息。",
    sections: [
      ["账号信息", "注册时保存账号、昵称、邮箱和加密后的密码；邮箱仅用于账号识别和密码找回。"],
      ["用户内容", "你主动发布的文章、动态、图片、评论、车库和项目记录会按照对应页面的可见范围保存。"],
      ["安全记录", "为防止暴力登录和滥用，服务器会保留必要的会话、访问和安全日志。"],
      ["账号权利", "你可以在个人设置中修改头像、昵称、邮箱和密码，也可以联系管理员处理账号和已发布内容。"],
    ],
  },
  "/community-rules": {
    title: "社区规范",
    intro: "这里欢迎真实的长期用车、改装过程和经验交流。",
    sections: [
      ["值得分享", "真实车况、维护记录、改装理由、安装过程、使用感受和踩坑经验。"],
      ["需要说明", "涉及道路测试、性能数据和改装建议时，请交代车辆状态、测试条件和安全边界。"],
      ["不应发布", "人身攻击、引战、广告刷屏、虚假交易、盗图洗稿、泄露隐私及鼓励危险驾驶的内容。"],
      ["发现问题", "可以在文章或动态详情页点击举报，管理员会在后台查看并处理。"],
    ],
  },
  "/contact": {
    title: "联系平台",
    intro: "账号、内容和安全问题可以通过站内方式联系 Tuner Hub。",
    sections: [
      ["站内联系", "登录后向管理员账号 THhub 发送私信，并说明问题页面和处理诉求。"],
      ["内容举报", "文章或动态详情页提供举报入口，请选择原因并补充必要说明。"],
      ["紧急安全问题", "涉及账号被盗或个人信息泄露时，请立即修改密码并联系管理员。"],
    ],
  },
};

const posts = ref([]);

const carCards = ref([]);

const carImageThemes = {
  BMW: assets.bmwM,
  AMG: assets.amg,
  Audi: assets.audiRs,
  JDM: assets.jdm,
};

function carDisplayImage(car) {
  if (!car) return assets.hero;
  if (car.detailImg) return car.detailImg;
  if (car.img?.startsWith("/media/") || car.img?.startsWith("/static/")) return mediaUrl(car.img);
  if (car.img?.startsWith("http")) return car.img;
  if (car.name?.startsWith("BMW")) return carImageThemes.BMW;
  if (car.name?.startsWith("Mercedes-AMG")) return carImageThemes.AMG;
  if (car.name?.startsWith("Audi")) return carImageThemes.Audi;
  if (["GR86 / BRZ", "WRX STI", "R32 GT-R", "A90 Supra"].includes(car.name)) return car.img || carImageThemes.JDM;
  return car.img || assets.hero;
}

function useFallbackImage(event) {
  if (event?.target && event.target.src !== fallbackImage) {
    event.target.src = fallbackImage;
  }
}

const carTrims = ref([]);

const buyingGuides = ref([]);
const clubs = ref([]);
const events = ref([]);
const shops = ref([]);
const market = ref([]);
const topicCards = ref([]);
const articles = ref([]);
const garageVehicles = ref([]);
const projectRecords = ref([]);
const route = useRoute();
const router = useRouter();
const query = ref("");
const activeFilter = ref(0);
const saved = ref(new Set());
const showComposer = ref(false);
const composerMode = ref("post");
const showAuthModal = ref(false);
const showMessageModal = ref(false);
const showGarageModal = ref(false);
const showProjectModal = ref(false);
const showReportModal = ref(false);
const authMode = ref("login");
const authMessage = ref("");
const authForm = ref({ username: "", password: "", email: "", nickname: "", accepted_terms: false });
const reportTarget = ref(null);
const reportForm = ref({ reason: "不实或误导", detail: "" });
const reportSubmitting = ref(false);
const resetForm = ref({ email: "", uid: "", token: "", new_password: "", confirm_password: "" });
const currentUser = ref(null);
const nicknameDraft = ref("");
const nicknameSaving = ref(false);
const emailForm = ref({ email: "", current_password: "" });
const emailSaving = ref(false);
const passwordForm = ref({ current_password: "", new_password: "", confirm_password: "" });
const passwordSaving = ref(false);
const userCards = ref([]);
const inboxMessages = ref([]);
const unreadMessageCount = ref(0);
const postComments = ref([]);
const commentBody = ref("");
const commentSubmitting = ref(false);
const messageTarget = ref(null);
const messageBody = ref("");
const menuOpen = ref(false);
const toast = ref("");
const draftTitle = ref("");
const draft = ref("");
const draftType = ref("聊车");
const draftCar = ref("");
const draftImage = ref(null);
const draftImagePreview = ref("");
const draftImageCaption = ref("");
const postImageInput = ref(null);
const publishingPost = ref(false);
const publishingArticle = ref(false);
const articleComments = ref([]);
const articleCommentBody = ref("");
const articleCommentSubmitting = ref(false);
const articleCoverInput = ref(null);
const articleBulkImageInput = ref(null);
const selectedArticleBlockIndex = ref(0);
const articleCoverFile = ref(null);
const articleCoverPreview = ref("");
const articleDraft = ref({ title: "", summary: "", category: "长期用车", car: "", image_caption: "" });
let articleBlockSequence = 1;
const articleDraftBlocks = ref([{ key: articleBlockSequence, type: "paragraph", text: "", caption: "", file: null, preview: "" }]);
const showSpecsPanel = ref(false);
const showLocationPanel = ref(false);
const draftSpecs = ref([{ label: "", value: "" }]);
const draftLocation = ref("");
const locationInput = ref(null);
const garageForm = ref({ car_id: "", custom_name: "", year: "", color: "", mods: "" });
const projectForm = ref({ vehicle_id: "", title: "", stage: "", content: "" });
const carKeyword = ref("");
const activeDriveFilter = ref(0);

const filteredPosts = computed(() => {
  const keyword = query.value.trim().toLowerCase();
  const filterLabel = feedFilters[activeFilter.value];
  return posts.value.filter((post) => {
    const matchesFilter = activeFilter.value === 0 || post.type === filterLabel;
    const matchesSearch = !keyword || [post.title, post.body, post.author, post.club, post.car].join(" ").toLowerCase().includes(keyword);
    return matchesFilter && matchesSearch;
  });
});

const savedPosts = computed(() => posts.value.filter((post) => post.is_saved));
const savedArticles = computed(() => articles.value.filter((article) => article.is_saved));

const unreadMessages = computed(() => inboxMessages.value.filter((message) => message.receiver.id === currentUser.value?.id && !message.is_read));

const isFunctionalListPage = computed(() => [
  "/garage", "/projects", "/profile", "/saved", "/notifications", "/search", "/topics", "/events", "/clubs", "/shops",
  "/terms", "/privacy", "/community-rules", "/contact",
].includes(route.path) || route.path.startsWith("/messages"));

const routeMessage = computed(() => {
  if (!route.path.startsWith("/messages/") || !route.params.id) return null;
  return inboxMessages.value.find((message) => String(message.id) === String(route.params.id)) || null;
});

const featuredPost = computed(() => posts.value.find((post) => post.featured) || null);
const reviewArticles = computed(() => articles.value.filter((article) => article.category !== "资讯"));
const hasRankingActivity = computed(() => posts.value.length > 0);
const displayUser = computed(() => currentUser.value || {
  username: "未登录",
  nickname: "游客",
  avatar: "",
  level_label: "Lv.0",
  activity_points: 0,
  followers_count: 0,
  following_count: 0,
  signature: "登录后查看真实账号数据",
});
const avatarSrc = computed(() => mediaUrl(displayUser.value.avatar) || defaultAvatar);
const displayLevelNumber = computed(() => String(displayUser.value.level_label || "0").replace(/^Lv\.?/i, "") || "0");
const publicInfoPage = computed(() => publicInfoPages[route.path] || null);
const authTitle = computed(() => ({
  login: "登录 Tuner Hub",
  register: "注册 Tuner Hub",
  forgot: "找回密码",
  reset: "设置新密码",
}[authMode.value]));

function applyCurrentUser(user) {
  currentUser.value = user;
  nicknameDraft.value = user?.nickname || "";
  emailForm.value = { email: user?.email || "", current_password: "" };
}

const enrichedCars = computed(() => carCards.value.map((car) => {
  const trims = [
    ...(Array.isArray(car.trims) ? car.trims : []),
    ...carTrims.value.filter((trim) => trim.car === car.name),
  ];
  const uniqueTrims = trims.filter((trim, index, list) => list.findIndex((item) => (item.id || `${item.car}-${item.name}`) === (trim.id || `${trim.car}-${trim.name}`)) === index);
  const drives = [...new Set(uniqueTrims.map((trim) => trim.drivetrain).filter(Boolean))];
  return { ...car, trims: uniqueTrims, drives, displayImg: carDisplayImage(car) };
}));

const searchResults = computed(() => {
  const keyword = query.value.trim().toLowerCase();
  if (!keyword) return { posts: [], cars: [], articles: [], clubs: [], shops: [], parts: [] };
  return {
    posts: posts.value.filter((post) => [post.title, post.body, post.author, post.car].join(" ").toLowerCase().includes(keyword)),
    cars: enrichedCars.value.filter((car) => [car.name, car.tag, car.heat].join(" ").toLowerCase().includes(keyword)),
    articles: articles.value.filter((article) => [article.title, article.summary, article.body, article.car].join(" ").toLowerCase().includes(keyword)),
    clubs: clubs.value.filter((club) => club.join(" ").toLowerCase().includes(keyword)),
    shops: shops.value.filter((shop) => shop.join(" ").toLowerCase().includes(keyword)),
    parts: market.value.filter((part) => [part.name, part.status].join(" ").toLowerCase().includes(keyword)),
  };
});

const searchResultCount = computed(() => Object.values(searchResults.value).reduce((total, items) => total + items.length, 0));

const filteredCars = computed(() => {
  const keyword = carKeyword.value.trim().toLowerCase();
  const driveLabel = driveFilters[activeDriveFilter.value];
  return enrichedCars.value.filter((car) => {
    const text = [car.name, car.tag, car.heat, ...car.drives, ...car.trims.map((trim) => `${trim.name} ${trim.engine} ${trim.gearbox}`)].join(" ").toLowerCase();
    const matchesKeyword = !keyword || text.includes(keyword);
    const matchesDrive = activeDriveFilter.value === 0 || car.drives.includes(driveLabel);
    return matchesKeyword && matchesDrive;
  });
});

const rankings = computed(() => enrichedCars.value
  .map((car) => {
    const relatedPosts = posts.value.filter((post) => post.car === car.name);
    const score = relatedPosts.reduce((sum, post) => sum + Number(post.likes || 0) + Number(post.comments || 0), relatedPosts.length);
    return { car, score, count: relatedPosts.length };
  })
  .sort((a, b) => b.score - a.score || b.count - a.count || a.car.name.localeCompare(b.car.name))
  .slice(0, 8)
  .map((item, index) => [
    String(index + 1).padStart(2, "0"),
    item.car.name,
    `${item.count} 条真实内容`,
    `${item.score} 热度`,
  ]));

const activePage = computed(() => {
  if (route.path.startsWith("/cars")) return 1;
  if (route.path.startsWith("/reviews")) return 2;
  if (route.path.startsWith("/community") || route.path.startsWith("/messages") || route.path.startsWith("/notifications")) return 3;
  if (route.path.startsWith("/market")) return 4;
  if (route.path.startsWith("/rankings")) return 5;
  return 0;
});

const routePost = computed(() => {
  if (!route.path.startsWith("/post/")) return null;
  return posts.value.find((post) => String(post.id) === String(route.params.id)) || null;
});

const routeArticle = computed(() => articles.value.find((article) => (
  route.path === `/articles/${article.id}`
  || route.path === pathFor("articles", article.slug || article.title)
)) || null);

function normalizeArticleText(value) {
  return String(value || "").replace(/\s+/g, "").trim();
}

const visibleArticleSummary = computed(() => {
  const article = routeArticle.value;
  const summary = String(article?.summary || "").trim();
  if (!summary) return "";

  const firstParagraph = article.blocks?.find((block) => block.type === "paragraph" && block.text?.trim())?.text
    || String(article.body || "").split(/\n\s*\n/)[0];
  return normalizeArticleText(summary) === normalizeArticleText(firstParagraph) ? "" : summary;
});

const routeCar = computed(() => {
  if (!route.path.startsWith("/cars/")) return null;
  const currentPath = route.path.replace(/\/community\/?$/, "");
  return carCards.value.find((car) => currentPath === pathFor("cars", car.name) || (car.slug && currentPath === `/cars/${encodeURIComponent(car.slug)}`)) || null;
});

const isCarCommunityPage = computed(() => Boolean(routeCar.value && /\/community\/?$/.test(route.path)));

const selectedCarTrims = computed(() => {
  if (!routeCar.value) return [];
  const embedded = Array.isArray(routeCar.value.trims) ? routeCar.value.trims : [];
  const standalone = carTrims.value.filter((trim) => trim.car === routeCar.value.name);
  const seen = new Set();
  return [...embedded, ...standalone].filter((trim) => {
    const key = trim.id || `${trim.car}-${trim.name}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
});

const selectedCarArticles = computed(() => {
  if (!routeCar.value) return [];
  return articles.value.filter((article) => article.car === routeCar.value.name);
});

const selectedCarPosts = computed(() => {
  if (!routeCar.value) return [];
  return posts.value.filter((post) => post.car === routeCar.value.name).slice(0, 3);
});

const selectedCarCommunityPosts = computed(() => {
  if (!routeCar.value) return [];
  return posts.value.filter((post) => post.car === routeCar.value.name);
});

const routeDetail = computed(() => {
  if (routePost.value) {
    const post = routePost.value;
    return {
      type: "帖子详情",
      title: post.title,
      image: post.image,
      imageCaption: post.image_caption || "",
      body: post.body,
      meta: `${post.author} · ${post.time}`,
      isPinned: post.is_pinned,
      rows: [
        ["分类", post.type],
        ["车辆", post.car],
        ["车友会", post.club],
        ["点赞", post.likes],
        ["评论", post.comments],
        ["进度", `${post.progress}%`],
        ...(post.location ? [["位置", post.location]] : []),
        ...(post.specs || []).map((spec) => ["配置", spec]),
      ],
    };
  }

  const article = routeArticle.value;
  if (article) {
    return {
      type: `${article.category}文章`,
      title: article.title,
      image: article.image || "",
      imageCaption: article.image_caption || "",
      body: article.body || article.summary,
      meta: `${article.author} · ${article.time || "刚刚"}`,
      isPinned: article.is_pinned,
      rows: [["栏目", article.category], ["车型", article.car || "不限"], ["阅读", article.views || 0], ["点赞", article.likes || 0], ["评论", article.comments || 0]],
    };
  }

  const shop = shops.value.find((item) => route.path === pathFor("shops", item[1]));
  if (shop) {
    return {
      type: "认证改装店",
      title: shop[1],
      image: shop[5] || "",
      body: shop[3] || "暂无服务范围说明。",
      meta: `评分 ${shop[2]} · ${shop[3]}`,
      rows: [["评分", shop[2]], ["服务", shop[3] || "待补充"], ["认证", "TH 认证"]],
    };
  }

  const club = clubs.value.find((item) => route.path === pathFor("clubs", item[1]));
  if (club) {
    return {
      type: "车友会主页",
      title: club[1],
      image: club[4] || "",
      body: `${club[1]} 当前登记成员信息：${club[2] || "待补充"}。`,
      meta: club[2],
      rows: [["成员", club[2] || "待补充"]],
    };
  }

  const event = events.value.find((item) => route.path === pathFor("events", item.name));
  if (event) {
    return {
      type: "活动详情",
      title: event.name,
      image: event.img,
      body: event.meta || "暂无活动时间与地点说明。",
      meta: `${event.meta} · ${event.count}`,
      rows: [["时间地点", event.meta || "待补充"], ["报名", event.count || "待补充"]],
    };
  }

  const part = market.value.find((item) => route.path === pathFor("market", item.name));
  if (part) {
    return {
      type: "二手件详情",
      title: part.name,
      image: part.img,
      body: part.status || "暂无配件说明。",
      meta: part.status || "配件动态",
      rows: [["状态", part.status || "配件动态"]],
    };
  }

  const topic = topicCards.value.find((item) => route.path === pathFor("topics", item.title));
  if (topic) {
    return {
      type: "专题页",
      title: topic.title,
      image: "",
      body: topic.desc,
      meta: topic.count,
      rows: [["内容量", topic.count || "待补充"], ["方向", topic.desc || "待补充"]],
    };
  }

  const guide = buyingGuides.value.find((item) => String(item.id) === String(route.params.id));
  if (route.path.startsWith("/guides/") && guide) {
    return {
      type: "导购文章",
      title: guide.title,
      image: "",
      body: guide.body || "暂无正文内容。",
      meta: "真实导购",
      rows: [["栏目", "改装导购"], ["来源", "用户发布"], ["状态", "已发布"]],
    };
  }

  const genericPages = {
    "/garage": ["我的车库", "管理你的项目车、车辆照片、改装清单和进度记录。"],
    "/projects": ["项目车记录", "集中展示你的施工记录、零件清单、调校数据和下一步计划。"],
    "/saved": ["收藏内容", "这里显示当前账号保存的帖子。"],
    "/calendar": ["活动日历", "查看线下聚会、店家开放日、赛道日和报名提醒。"],
    "/shops": ["店家目录", "按城市、评分、服务范围筛选 TH 认证改装店。"],
    "/messages": ["消息中心", "查看当前账号发送和收到的私信。"],
    "/notifications": ["新消息", "这里只显示尚未阅读的私信提醒。"],
    "/topics": ["专题中心", "浏览合法改装、赛道日、姿态车、二手件避雷等专题。"],
    "/events": ["活动中心", "聚合车友会聚会、店家开放日、赛道日和报名信息。"],
    "/clubs": ["车友会广场", "浏览活跃车友会、成员项目车、活动和热门帖子。"],
    "/profile": ["个人中心", "管理账号资料、头像、车库、收藏和发布内容。"],
    "/admin-guide": ["内容管理说明", "管理员可以维护社区内容，普通用户看到的都是已发布内容。"],
    "/terms": ["用户协议", "使用 Tuner Hub 前请了解账号、内容和社区管理规则。"],
    "/privacy": ["隐私政策", "了解账号信息、用户内容和安全记录的使用方式。"],
    "/community-rules": ["社区规范", "真实分享、理性交流，并尊重安全与他人权利。"],
    "/contact": ["联系平台", "通过站内私信和内容举报联系 Tuner Hub 管理员。"],
    "/create": ["发布内容", "选择内容类型，分享聊车动态、改装记录、聚会活动或二手件信息。"],
    "/messages/sent": ["消息已发送", "对方收到后会出现在私信记录中。"],
    "/notifications/clear": ["清空通知", "通知清空后将不再显示在列表中。"],
    "/post/submitted": ["发布成功", "内容提交后可进入审核、草稿或已发布状态。"],
  };

  if (genericPages[route.path]) {
    return {
      type: "功能页面",
      title: genericPages[route.path][0],
      image: assets.hero,
      body: genericPages[route.path][1],
      meta: "Tuner Hub 功能入口",
      rows: [["页面", genericPages[route.path][0]], ["内容", "来自当前数据库"]],
    };
  }

  if (route.path.startsWith("/messages/")) {
    return {
      type: "私信详情",
      title: routeMessage.value ? `与 ${messageCounterparty(routeMessage.value).nickname || messageCounterparty(routeMessage.value).username} 的私信` : "私信不存在",
      image: assets.hero,
      body: routeMessage.value?.body || "这条私信不存在或当前账号无权查看。",
      meta: routeMessage.value?.time || "消息中心",
      rows: routeMessage.value ? [["发送者", routeMessage.value.sender.nickname || routeMessage.value.sender.username], ["接收者", routeMessage.value.receiver.nickname || routeMessage.value.receiver.username], ["状态", routeMessage.value.is_read ? "已读" : "未读"]] : [],
    };
  }

  if (route.path.startsWith("/channels/")) {
    const title = decodeURIComponent(route.path.replace("/channels/", "")).replace(/-/g, " ");
    return {
      type: "频道页",
      title,
      image: assets.meet,
      body: `${title} 频道会聚合相关帖子、车型、店家、活动和二手件内容。`,
      meta: "内容频道",
      rows: [["频道", title], ["内容", "帖子 / 车型 / 店家 / 活动"]],
    };
  }

  if (route.path.startsWith("/feed/")) {
    const title = decodeURIComponent(route.path.replace("/feed/", "")).replace(/-/g, " ");
    return {
      type: "筛选结果",
      title,
      image: assets.engine,
      body: `${title} 会展示符合条件的社区内容。`,
      meta: "信息流筛选",
      rows: [["筛选", title], ["内容", "社区动态"]],
    };
  }

  if (route.path.startsWith("/tasks/")) {
    return {
      type: "待办详情",
      title: "暂无待办",
      image: assets.shop,
      body: "这里会显示由互动、活动报名或账号提醒产生的待办事项。",
      meta: "个人待办",
      rows: [["页面", "待办详情"], ["状态", "暂无数据"], ["来源", "账号提醒"]],
    };
  }

  if (route.path.startsWith("/notifications/")) {
    return {
      type: "通知详情",
      title: "暂无通知",
      image: assets.meet,
      body: "这里会显示真实评论、关注、私信或系统通知。",
      meta: "通知中心",
      rows: [["页面", "通知详情"], ["状态", "暂无数据"], ["来源", "互动消息"]],
    };
  }

  if (route.path.startsWith("/create/")) {
    const title = decodeURIComponent(route.path.replace("/create/", "")).replace(/-/g, " ");
    return {
      type: "发布工具",
      title: `发布${title}`,
      image: assets.supra,
      body: "在这里发布改装进度、聚会活动或配件内容。",
      meta: "发布内容",
      rows: [["类型", title], ["状态", "准备发布"], ["内容", "社区动态"]],
    };
  }

  if (route.path.startsWith("/search")) {
    return {
      type: "搜索结果",
      title: query.value ? `搜索：${query.value}` : "搜索",
      image: assets.hero,
      body: "搜索车型、改装方案、车友会、店家和二手件。",
      meta: "站内搜索",
      rows: [["关键词", query.value || "未输入"], ["范围", "全站内容"]],
    };
  }

  return null;
});

function apiBase() {
  const host = window.location.hostname;
  if (host === "localhost" || host === "127.0.0.1") return "http://127.0.0.1:8000";
  return "";
}

function mediaUrl(value) {
  if (!value) return value;
  if (value.startsWith("http")) return value;
  if (value.startsWith("/media/") || value.startsWith("/static/")) return `${apiBase()}${value}`;
  if (value.startsWith("/assets/")) return `${apiBase()}${value.replace("/assets/", "/static/assets/")}`;
  return value;
}

function normalizeImages(items, keys) {
  return items.map((item) => {
    const next = { ...item };
    keys.forEach((key) => {
      if (next[key]) next[key] = mediaUrl(next[key]);
    });
    if (Array.isArray(next.trims)) next.trims = next.trims.map((trim) => ({ ...trim }));
    return next;
  });
}

function normalizeArticles(items) {
  return normalizeImages(items, ["image", "author_avatar"]).map((article) => ({
    ...article,
    blocks: (article.blocks || []).map((block) => ({ ...block, image: mediaUrl(block.image) })),
  }));
}

async function apiFetch(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.body && !(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
  const response = await fetch(`${apiBase()}${path}`, {
    credentials: "include",
    headers,
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || "请求失败");
  return data;
}

async function loadSiteData() {
  try {
    const data = await apiFetch("/api/site-data/");
    if (Array.isArray(data.posts)) {
      posts.value = normalizeImages(data.posts, ["image"]);
      saved.value = new Set(posts.value.filter((post) => post.is_saved).map((post) => post.id));
    }
    if (Array.isArray(data.cars)) carCards.value = normalizeImages(data.cars, ["img"]);
    if (Array.isArray(data.trims)) carTrims.value = data.trims;
    if (Array.isArray(data.clubs)) clubs.value = data.clubs.map((club) => club.map((value, index) => index === 4 ? mediaUrl(value) : value));
    if (Array.isArray(data.events)) events.value = normalizeImages(data.events, ["img"]);
    if (Array.isArray(data.shops)) shops.value = data.shops.map((shop) => shop.map((value, index) => index === 5 ? mediaUrl(value) : value));
    if (Array.isArray(data.market)) market.value = normalizeImages(data.market, ["img"]);
    if (Array.isArray(data.topics)) topicCards.value = data.topics;
    if (Array.isArray(data.guides)) buyingGuides.value = data.guides;
    if (Array.isArray(data.articles)) articles.value = normalizeArticles(data.articles);
    if (Array.isArray(data.users)) userCards.value = normalizeImages(data.users, ["avatar"]);
    if (Array.isArray(data.garage)) garageVehicles.value = data.garage;
    if (Array.isArray(data.projects)) projectRecords.value = data.projects;
  } catch {
    // 连接异常时保留当前页面数据，避免影响浏览。
  }
}

async function checkCurrentUser() {
  try {
    const data = await apiFetch("/api/auth/me/");
    applyCurrentUser(data.user);
  } catch {
    applyCurrentUser(null);
  }
}

async function loadMessages() {
  if (!currentUser.value) {
    inboxMessages.value = [];
    unreadMessageCount.value = 0;
    return;
  }
  try {
    const data = await apiFetch("/api/messages/");
    inboxMessages.value = data.messages || [];
    unreadMessageCount.value = Number(data.unread_count || 0);
  } catch {
    inboxMessages.value = [];
    unreadMessageCount.value = 0;
  }
}

onMounted(async () => {
  if (route.path.startsWith("/reset-password/")) {
    resetForm.value.uid = String(route.params.uid || "");
    resetForm.value.token = String(route.params.token || "");
    openAuth("reset");
  }
  await checkCurrentUser();
  await loadSiteData();
  await loadMessages();
  if (route.path === "/create" || route.path.startsWith("/create/")) {
    composerMode.value = route.path === "/create/article" ? "article" : "post";
    showComposer.value = true;
    showSpecsPanel.value = route.path === "/create/specs";
    showLocationPanel.value = route.path === "/create/location";
  }
  window.setInterval(loadSiteData, 15000);
  window.setInterval(loadMessages, 15000);
});

watch(routePost, (post) => {
  commentBody.value = "";
  loadPostComments(post?.id);
});

watch(() => routeArticle.value?.id, (articleId) => {
  articleCommentBody.value = "";
  if (articleId) loadArticleDetail(articleId);
  else articleComments.value = [];
});

function switchPage(index) {
  router.push(routePaths[index]);
  menuOpen.value = false;
}

function pathFor(section, value) {
  return `/${section}/${encodeURIComponent(String(value).replace(/\s+/g, "-").replace(/\//g, "-"))}`;
}

function carRoute(car) {
  return `/cars/${encodeURIComponent(car.slug || String(car.name).replace(/\s+/g, "-").replace(/\//g, "-"))}`;
}

function goTo(path) {
  router.push(path);
  menuOpen.value = false;
}

function submitSearch() {
  if (!query.value.trim()) return;
  goTo("/search");
}

async function openPost(post) {
  if (!post) return;
  goTo(`/post/${post.id}`);
  await loadPostComments(post.id);
}

function openComposer(mode = "post") {
  composerMode.value = mode;
  goTo("/create");
  showComposer.value = true;
}

function openPostComposerForType(type) {
  draftType.value = type;
  openComposer("post");
}

function openArticleComposer(car = null) {
  composerMode.value = "article";
  articleDraft.value.car = car?.name || "";
  goTo("/create/article");
  showComposer.value = true;
}

async function openComposerForCar(car, path = "/create") {
  composerMode.value = "post";
  draftCar.value = car?.name || "";
  goTo(path);
  showComposer.value = true;
  if (path === "/create/specs") showSpecsPanel.value = true;
  if (path === "/create/location") showLocationPanel.value = true;
  await nextTick();
  if (path === "/create/photos") choosePostImage();
  if (path === "/create/location") locationInput.value?.focus();
}

function choosePostImage() {
  postImageInput.value?.click();
}

async function openPhotoComposer() {
  await openComposerForCar(null, "/create/photos");
}

async function openSpecsComposer(car = null) {
  await openComposerForCar(car, "/create/specs");
}

function addDraftSpec() {
  if (draftSpecs.value.length >= 8) {
    showToast("最多添加 8 项参数");
    return;
  }
  draftSpecs.value.push({ label: "", value: "" });
}

function removeDraftSpec(index) {
  draftSpecs.value.splice(index, 1);
  if (!draftSpecs.value.length) draftSpecs.value.push({ label: "", value: "" });
}

function clearPostExtras() {
  showSpecsPanel.value = false;
  showLocationPanel.value = false;
  draftSpecs.value = [{ label: "", value: "" }];
  draftLocation.value = "";
}

function revealSpecsPanel() {
  showSpecsPanel.value = true;
}

async function revealLocationPanel() {
  showLocationPanel.value = true;
  await nextTick();
  locationInput.value?.focus();
}

function clearDraftImage() {
  draftImage.value = null;
  draftImagePreview.value = "";
  draftImageCaption.value = "";
  if (postImageInput.value) postImageInput.value.value = "";
}

function handlePostImage(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  const extension = file.name.split(".").pop()?.toLowerCase();
  if (!["jpg", "jpeg", "png", "webp"].includes(extension)) {
    clearDraftImage();
    showToast("帖子图片仅支持 JPG、PNG 或 WebP");
    return;
  }
  if (file.size > 10 * 1024 * 1024) {
    clearDraftImage();
    showToast("帖子图片不能超过 10MB");
    return;
  }
  draftImage.value = file;
  const reader = new FileReader();
  reader.onload = () => {
    draftImagePreview.value = String(reader.result || "");
  };
  reader.readAsDataURL(file);
}

function articleBlock(type) {
  articleBlockSequence += 1;
  return { key: articleBlockSequence, type, text: "", caption: "", file: null, preview: "" };
}

function addArticleBlock(type) {
  if (articleDraftBlocks.value.length >= 40) {
    showToast("文章最多添加 40 个内容段落");
    return;
  }
  articleDraftBlocks.value.push(articleBlock(type));
}

function removeArticleBlock(index) {
  const block = articleDraftBlocks.value[index];
  if (block?.preview?.startsWith("blob:")) URL.revokeObjectURL(block.preview);
  articleDraftBlocks.value.splice(index, 1);
  if (!articleDraftBlocks.value.length) articleDraftBlocks.value.push(articleBlock("paragraph"));
  selectedArticleBlockIndex.value = Math.min(selectedArticleBlockIndex.value, articleDraftBlocks.value.length - 1);
}

function moveArticleBlock(index, offset) {
  const target = index + offset;
  if (target < 0 || target >= articleDraftBlocks.value.length) return;
  const [block] = articleDraftBlocks.value.splice(index, 1);
  articleDraftBlocks.value.splice(target, 0, block);
  selectedArticleBlockIndex.value = target;
}

function validComposerImage(file, label) {
  const extension = file.name.split(".").pop()?.toLowerCase();
  if (!["jpg", "jpeg", "png", "webp"].includes(extension)) {
    showToast(`${label}仅支持 JPG、PNG 或 WebP`);
    return false;
  }
  if (file.size > 10 * 1024 * 1024) {
    showToast(`${label}不能超过 10MB`);
    return false;
  }
  return true;
}

function handleArticleCover(event) {
  const file = event.target.files?.[0];
  if (!file || !validComposerImage(file, "文章封面")) return;
  articleCoverFile.value = file;
  articleCoverPreview.value = URL.createObjectURL(file);
}

function clearArticleCover() {
  if (articleCoverPreview.value.startsWith("blob:")) URL.revokeObjectURL(articleCoverPreview.value);
  articleCoverFile.value = null;
  articleCoverPreview.value = "";
  articleDraft.value.image_caption = "";
  if (articleCoverInput.value) articleCoverInput.value.value = "";
}

function handleArticleBlockImage(event, block) {
  const file = event.target.files?.[0];
  if (!file || !validComposerImage(file, "正文图片")) return;
  if (block.preview?.startsWith("blob:")) URL.revokeObjectURL(block.preview);
  block.file = file;
  block.preview = URL.createObjectURL(file);
}

function chooseArticleImagesAfter(index) {
  selectedArticleBlockIndex.value = Math.max(0, Math.min(index, articleDraftBlocks.value.length - 1));
  articleBulkImageInput.value?.click();
}

function handleArticleBulkImages(event) {
  const files = Array.from(event.target.files || []);
  if (!files.length) return;
  const existingImages = articleDraftBlocks.value.filter((block) => block.type === "image").length;
  const available = Math.max(0, Math.min(20 - existingImages, 40 - articleDraftBlocks.value.length));
  if (!available) {
    showToast(existingImages >= 20 ? "文章最多添加 20 张正文图片" : "文章最多添加 40 个内容段落");
    event.target.value = "";
    return;
  }
  const accepted = [];
  for (const file of files) {
    if (accepted.length >= available) break;
    if (validComposerImage(file, "正文图片")) accepted.push(file);
  }
  if (files.length > available) showToast(`本次已添加前 ${available} 张图片`);
  if (!accepted.length) {
    event.target.value = "";
    return;
  }
  const imageBlocks = accepted.map((file) => ({
    ...articleBlock("image"),
    file,
    preview: URL.createObjectURL(file),
  }));
  const insertAt = selectedArticleBlockIndex.value + 1;
  articleDraftBlocks.value.splice(insertAt, 0, ...imageBlocks);
  selectedArticleBlockIndex.value = insertAt + imageBlocks.length - 1;
  event.target.value = "";
}

function resetArticleDraft() {
  clearArticleCover();
  articleDraftBlocks.value.forEach((block) => {
    if (block.preview?.startsWith("blob:")) URL.revokeObjectURL(block.preview);
  });
  articleDraft.value = { title: "", summary: "", category: "长期用车", car: "", image_caption: "" };
  articleDraftBlocks.value = [articleBlock("paragraph")];
  selectedArticleBlockIndex.value = 0;
}

function openAuth(mode = "login") {
  authMode.value = mode;
  authMessage.value = "";
  showAuthModal.value = true;
}

async function submitAuth() {
  authMessage.value = "";
  if (authMode.value === "forgot") {
    try {
      const data = await apiFetch("/api/auth/password-reset/request/", {
        method: "POST",
        body: JSON.stringify({ email: resetForm.value.email }),
      });
      authMessage.value = data.message;
    } catch (error) {
      authMessage.value = error.message;
    }
    return;
  }
  if (authMode.value === "reset") {
    if (resetForm.value.new_password !== resetForm.value.confirm_password) {
      authMessage.value = "两次输入的新密码不一致";
      return;
    }
    try {
      await apiFetch("/api/auth/password-reset/confirm/", {
        method: "POST",
        body: JSON.stringify(resetForm.value),
      });
      authMode.value = "login";
      authMessage.value = "密码已重置，请使用新密码登录";
      resetForm.value = { email: "", uid: "", token: "", new_password: "", confirm_password: "" };
      router.replace("/");
    } catch (error) {
      authMessage.value = error.message;
    }
    return;
  }
  if (authMode.value === "register" && !authForm.value.accepted_terms) {
    authMessage.value = "请先阅读并同意用户协议和隐私政策";
    return;
  }
  try {
    const endpoint = authMode.value === "login" ? "/api/auth/login/" : "/api/auth/register/";
    const data = await apiFetch(endpoint, {
      method: "POST",
      body: JSON.stringify(authForm.value),
    });
    applyCurrentUser(data.user);
    showAuthModal.value = false;
    showToast(authMode.value === "login" ? "登录成功" : "注册成功");
  } catch (error) {
    authMessage.value = error.message;
  }
}

async function logoutAccount() {
  try {
    await apiFetch("/api/auth/logout/", { method: "POST", body: "{}" });
  } finally {
    applyCurrentUser(null);
    showToast("已退出登录");
  }
}

function showToast(message) {
  toast.value = message;
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => {
    toast.value = "";
  }, 1800);
}

function replacePost(updatedPost) {
  const normalized = normalizeImages([updatedPost], ["image"])[0];
  posts.value = posts.value.map((post) => post.id === normalized.id ? { ...post, ...normalized } : post);
  const next = new Set(saved.value);
  if (normalized.is_saved) next.add(normalized.id);
  else next.delete(normalized.id);
  saved.value = next;
}

function replaceArticle(updatedArticle) {
  const normalized = normalizeArticles([updatedArticle])[0];
  articles.value = articles.value.map((article) => article.id === normalized.id ? { ...article, ...normalized } : article);
}

async function loadArticleDetail(articleId) {
  if (!articleId) return;
  try {
    const data = await apiFetch(`/api/articles/${articleId}/`);
    replaceArticle(data.article);
    articleComments.value = normalizeImages(data.comments || [], ["avatar"]);
  } catch {
    articleComments.value = [];
  }
}

async function toggleArticleSave(article) {
  if (!currentUser.value) {
    openAuth("login");
    authMessage.value = "请先登录再收藏文章";
    return;
  }
  try {
    const data = await apiFetch(`/api/articles/${article.id}/save/`, { method: "POST", body: "{}" });
    replaceArticle(data.article);
    showToast(data.saved ? "已收藏" : "已取消收藏");
  } catch (error) {
    showToast(error.message);
  }
}

async function toggleArticleLike(article) {
  if (!currentUser.value) {
    openAuth("login");
    authMessage.value = "请先登录再点赞";
    return;
  }
  try {
    const data = await apiFetch(`/api/articles/${article.id}/like/`, { method: "POST", body: "{}" });
    replaceArticle(data.article);
    showToast(data.liked ? "已点赞" : "已取消点赞");
  } catch (error) {
    showToast(error.message);
  }
}

async function submitArticleComment() {
  if (!routeArticle.value || articleCommentSubmitting.value) return;
  if (!currentUser.value) {
    openAuth("login");
    authMessage.value = "请先登录再评论";
    return;
  }
  articleCommentSubmitting.value = true;
  try {
    const data = await apiFetch(`/api/articles/${routeArticle.value.id}/comments/`, {
      method: "POST",
      body: JSON.stringify({ body: articleCommentBody.value }),
    });
    articleComments.value = [...articleComments.value, normalizeImages([data.comment], ["avatar"])[0]];
    replaceArticle(data.article);
    articleCommentBody.value = "";
    showToast("评论已发布");
  } catch (error) {
    showToast(error.message);
  } finally {
    articleCommentSubmitting.value = false;
  }
}

async function toggleSave(id) {
  if (!currentUser.value) {
    openAuth("login");
    authMessage.value = "请先登录再收藏帖子";
    return;
  }
  try {
    const data = await apiFetch(`/api/posts/${id}/save/`, { method: "POST", body: "{}" });
    replacePost(data.post);
    showToast(data.saved ? "已收藏" : "已取消收藏");
  } catch (error) {
    showToast(error.message);
  }
}

async function toggleLike(post) {
  if (!currentUser.value) {
    openAuth("login");
    authMessage.value = "请先登录再点赞";
    return;
  }
  try {
    const data = await apiFetch(`/api/posts/${post.id}/like/`, { method: "POST", body: "{}" });
    replacePost(data.post);
    showToast(data.liked ? "已点赞" : "已取消点赞");
  } catch (error) {
    showToast(error.message);
  }
}

async function loadPostComments(postId) {
  if (!postId) {
    postComments.value = [];
    return;
  }
  try {
    const data = await apiFetch(`/api/posts/${postId}/comments/`);
    postComments.value = normalizeImages(data.comments || [], ["avatar"]);
  } catch {
    postComments.value = [];
  }
}

async function submitComment() {
  if (!routePost.value || commentSubmitting.value) return;
  if (!currentUser.value) {
    openAuth("login");
    authMessage.value = "请先登录再评论";
    return;
  }
  commentSubmitting.value = true;
  try {
    const data = await apiFetch(`/api/posts/${routePost.value.id}/comments/`, {
      method: "POST",
      body: JSON.stringify({ body: commentBody.value }),
    });
    postComments.value = [...postComments.value, normalizeImages([data.comment], ["avatar"])[0]];
    replacePost(data.post);
    commentBody.value = "";
    showToast("评论已发布");
  } catch (error) {
    showToast(error.message);
  } finally {
    commentSubmitting.value = false;
  }
}

function canManageCommunity() {
  return Boolean(currentUser.value?.is_staff || currentUser.value?.is_superuser);
}

async function uploadAvatar(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  const formData = new FormData();
  formData.append("avatar", file);
  try {
    const data = await apiFetch("/api/auth/avatar/", {
      method: "POST",
      body: formData,
    });
    applyCurrentUser(data.user);
    showToast("头像已更新");
  } catch (error) {
    showToast(error.message);
  } finally {
    event.target.value = "";
  }
}

async function saveNickname() {
  if (!currentUser.value || nicknameSaving.value) return;
  nicknameSaving.value = true;
  try {
    const data = await apiFetch("/api/auth/profile/", {
      method: "POST",
      body: JSON.stringify({ nickname: nicknameDraft.value }),
    });
    applyCurrentUser(data.user);
    await loadSiteData();
    showToast("昵称已更新");
  } catch (error) {
    showToast(error.message);
  } finally {
    nicknameSaving.value = false;
  }
}

async function saveEmail() {
  if (!currentUser.value || emailSaving.value) return;
  emailSaving.value = true;
  try {
    const data = await apiFetch("/api/auth/email/", {
      method: "POST",
      body: JSON.stringify(emailForm.value),
    });
    applyCurrentUser(data.user);
    showToast("找回邮箱已更新");
  } catch (error) {
    showToast(error.message);
  } finally {
    emailSaving.value = false;
  }
}

async function savePassword() {
  if (!currentUser.value || passwordSaving.value) return;
  if (passwordForm.value.new_password !== passwordForm.value.confirm_password) {
    showToast("两次输入的新密码不一致");
    return;
  }
  passwordSaving.value = true;
  try {
    await apiFetch("/api/auth/password/", {
      method: "POST",
      body: JSON.stringify(passwordForm.value),
    });
    passwordForm.value = { current_password: "", new_password: "", confirm_password: "" };
    showToast("密码已更新");
  } catch (error) {
    showToast(error.message);
  } finally {
    passwordSaving.value = false;
  }
}

async function toggleFollow(user) {
  if (!currentUser.value) {
    openAuth("login");
    authMessage.value = "请先登录再关注用户";
    return;
  }
  try {
    const data = await apiFetch(`/api/users/${user.id}/follow/`, {
      method: "POST",
      body: "{}",
    });
    userCards.value = userCards.value.map((item) => {
      if (item.id === data.target_user.id) return { ...item, ...data.target_user, is_following: data.following };
      if (item.id === data.current_user.id) return { ...item, ...data.current_user };
      return item;
    });
    if (currentUser.value?.id === data.current_user.id) applyCurrentUser(data.current_user);
    showToast(data.following ? "已关注" : "已取消关注");
    await loadSiteData();
  } catch (error) {
    showToast(error.message);
  }
}

function openMessage(user) {
  if (!currentUser.value) {
    openAuth("login");
    authMessage.value = "请先登录再发送私信";
    return;
  }
  messageTarget.value = user;
  messageBody.value = "";
  showMessageModal.value = true;
}

function messageCounterparty(message) {
  if (!message) return {};
  return message.sender.id === currentUser.value?.id ? message.receiver : message.sender;
}

async function openInboxMessage(message) {
  if (!message) return;
  if (message.receiver.id === currentUser.value?.id && !message.is_read) {
    try {
      const data = await apiFetch(`/api/messages/${message.id}/read/`, { method: "POST", body: "{}" });
      inboxMessages.value = inboxMessages.value.map((item) => item.id === message.id ? data.message : item);
      unreadMessageCount.value = Number(data.unread_count || 0);
      message = data.message;
    } catch (error) {
      showToast(error.message);
      return;
    }
  }
  goTo(`/messages/${message.id}`);
}

async function sendMessage() {
  if (!messageTarget.value) return;
  try {
    const data = await apiFetch(`/api/users/${messageTarget.value.id}/message/`, {
      method: "POST",
      body: JSON.stringify({ body: messageBody.value }),
    });
    inboxMessages.value = [data.message, ...inboxMessages.value];
    showMessageModal.value = false;
    messageBody.value = "";
    showToast("私信已发送");
    await loadMessages();
  } catch (error) {
    showToast(error.message);
  }
}

async function deleteCommunityPost(post) {
  if (!post || !canManageCommunity()) return;
  if (!window.confirm(`确定删除“${post.title}”吗？此操作无法撤销。`)) return;
  try {
    await apiFetch(`/api/posts/${post.id}/delete/`, {
      method: "POST",
      body: "{}",
    });
    posts.value = posts.value.filter((item) => item.id !== post.id);
    showToast("社区内容已删除");
    if (route.path === `/post/${post.id}`) goTo("/community");
  } catch (error) {
    showToast(error.message);
  }
}

async function deleteCommunityArticle(article) {
  if (!article || !canManageCommunity()) return;
  if (!window.confirm(`确定删除文章“${article.title}”吗？此操作无法撤销。`)) return;
  try {
    await apiFetch(`/api/articles/${article.id}/delete/`, { method: "POST", body: "{}" });
    articles.value = articles.value.filter((item) => item.id !== article.id);
    showToast("文章已删除");
    if (route.path === `/articles/${article.id}`) goTo("/");
  } catch (error) {
    showToast(error.message);
  }
}

function openContentReport(targetType, target) {
  if (!currentUser.value) {
    openAuth("login");
    authMessage.value = "请先登录再提交举报";
    return;
  }
  reportTarget.value = { type: targetType, id: target.id, title: target.title };
  reportForm.value = { reason: "不实或误导", detail: "" };
  showReportModal.value = true;
}

async function submitContentReport() {
  if (!reportTarget.value || reportSubmitting.value) return;
  reportSubmitting.value = true;
  try {
    await apiFetch("/api/reports/create/", {
      method: "POST",
      body: JSON.stringify({
        target_type: reportTarget.value.type,
        target_id: reportTarget.value.id,
        reason: reportForm.value.reason,
        detail: reportForm.value.detail.trim(),
      }),
    });
    showReportModal.value = false;
    showToast("举报已提交，管理员会尽快处理");
  } catch (error) {
    showToast(error.message);
  } finally {
    reportSubmitting.value = false;
  }
}

async function submitGarageVehicle() {
  if (!currentUser.value) {
    showGarageModal.value = false;
    openAuth("login");
    authMessage.value = "请先登录再添加车辆";
    return;
  }
  try {
    const data = await apiFetch("/api/garage/create/", {
      method: "POST",
      body: JSON.stringify(garageForm.value),
    });
    garageVehicles.value = [data.vehicle, ...garageVehicles.value];
    garageForm.value = { car_id: "", custom_name: "", year: "", color: "", mods: "" };
    showGarageModal.value = false;
    showToast("车辆已添加");
  } catch (error) {
    showToast(error.message);
  }
}

async function submitProjectRecord() {
  if (!currentUser.value) {
    showProjectModal.value = false;
    openAuth("login");
    authMessage.value = "请先登录再添加项目记录";
    return;
  }
  try {
    const data = await apiFetch("/api/projects/create/", {
      method: "POST",
      body: JSON.stringify(projectForm.value),
    });
    projectRecords.value = [data.record, ...projectRecords.value];
    projectForm.value = { vehicle_id: "", title: "", stage: "", content: "" };
    showProjectModal.value = false;
    showToast("项目记录已添加");
  } catch (error) {
    showToast(error.message);
  }
}

async function publishPost() {
  if (!currentUser.value) {
    showComposer.value = false;
    openAuth("login");
    authMessage.value = "请先登录再发布帖子";
    return;
  }
  if (publishingPost.value) return;

  publishingPost.value = true;
  try {
    const formData = new FormData();
    formData.append("title", draftTitle.value);
    formData.append("body", draft.value);
    formData.append("type", draftType.value);
    formData.append("car", draftCar.value);
    const specs = draftSpecs.value
      .map((spec) => [spec.label.trim(), spec.value.trim()].filter(Boolean).join(": "))
      .filter(Boolean);
    formData.append("specs", JSON.stringify(specs));
    formData.append("location", draftLocation.value.trim());
    formData.append("image_caption", draftImageCaption.value.trim());
    if (draftImage.value) formData.append("image", draftImage.value);
    const data = await apiFetch("/api/posts/create/", {
      method: "POST",
      body: formData,
    });
    posts.value = [
      ...posts.value.filter((post) => post.is_pinned),
      data.post,
      ...posts.value.filter((post) => !post.is_pinned),
    ];
    showComposer.value = false;
    draftTitle.value = "";
    draft.value = "";
    draftCar.value = "";
    clearDraftImage();
    clearPostExtras();
    showToast("帖子已发布");
    goTo(`/post/${data.post.id}`);
  } catch (error) {
    showToast(error.message);
  } finally {
    publishingPost.value = false;
  }
}

async function publishArticle() {
  if (!currentUser.value) {
    showComposer.value = false;
    openAuth("login");
    authMessage.value = "请先登录再发布文章";
    return;
  }
  if (publishingArticle.value) return;

  publishingArticle.value = true;
  try {
    const formData = new FormData();
    formData.append("title", articleDraft.value.title.trim());
    formData.append("summary", articleDraft.value.summary.trim());
    formData.append("category", articleDraft.value.category);
    formData.append("car", articleDraft.value.car);
    formData.append("image_caption", articleDraft.value.image_caption.trim());
    if (articleCoverFile.value) formData.append("cover_image", articleCoverFile.value);

    const blocks = articleDraftBlocks.value.map((block, index) => {
      const payload = { type: block.type, text: block.text?.trim() || "", caption: block.caption?.trim() || "" };
      if (block.type === "image" && block.file) {
        payload.image_key = `block_image_${index}`;
        formData.append(payload.image_key, block.file);
      }
      return payload;
    });
    formData.append("blocks", JSON.stringify(blocks));

    const data = await apiFetch("/api/articles/create/", { method: "POST", body: formData });
    const article = normalizeArticles([data.article])[0];
    articles.value = [
      ...articles.value.filter((item) => item.is_pinned),
      article,
      ...articles.value.filter((item) => !item.is_pinned),
    ];
    showComposer.value = false;
    resetArticleDraft();
    showToast("文章已发布并显示在首页");
    goTo(`/articles/${article.id}`);
  } catch (error) {
    showToast(error.message);
  } finally {
    publishingArticle.value = false;
  }
}

</script>

<template>
  <div class="app">
    <header class="topbar">
      <button class="menu-button" aria-label="打开菜单" @click="menuOpen = true"><List :size="22" /></button>
      <button class="brand" @click="switchPage(0)">
        <span class="brand-mark">TH</span>
        <span class="brand-name">Tuner Hub</span>
      </button>

      <form class="search" role="search" @submit.prevent="submitSearch">
        <input v-model="query" aria-label="站内搜索" placeholder="搜索车型、改装方案、车友会、店家" />
        <button type="submit" aria-label="搜索"><MagnifyingGlass :size="18" /></button>
      </form>

      <nav class="tabs">
        <button v-for="(item, index) in navItems" :key="item" :class="{ active: activePage === index }" @click="switchPage(index)">
          {{ item }}
        </button>
      </nav>

      <div class="top-actions">
        <button class="icon-button" aria-label="消息" @click="goTo('/messages')"><ChatCircle :size="21" /></button>
        <button class="icon-button with-dot" aria-label="通知" @click="goTo('/notifications')"><Bell :size="21" /><span v-if="unreadMessageCount">{{ unreadMessageCount }}</span></button>
        <button class="create-button" @click="openComposer"><Plus :size="18" />发布</button>
        <button v-if="!currentUser" class="auth-button" @click="openAuth('login')">登录/注册</button>
        <button v-else class="auth-button" @click="goTo('/profile')">{{ currentUser.nickname || currentUser.username }}</button>
        <button v-if="currentUser" class="auth-button ghost" @click="logoutAccount">退出</button>
        <button class="avatar-button" @click="goTo('/profile')"><img :src="avatarSrc" alt="Tuner hub" /></button>
      </div>
    </header>

    <main class="shell" :class="{ 'article-shell': routeArticle }">
      <aside class="sidebar" :class="{ 'mobile-open': menuOpen }">
        <button class="close-menu" aria-label="关闭菜单" @click="menuOpen = false"><X :size="20" /></button>
        <div class="profile">
          <img :src="avatarSrc" alt="Tuner hub" />
          <strong>{{ displayUser.nickname || displayUser.username }}</strong>
          <span>@{{ displayUser.username }}</span>
          <small>{{ displayLevelNumber }}</small>
        </div>
        <div class="stats">
          <div><strong>{{ displayUser.followers_count }}</strong><span>粉丝</span></div>
          <div><strong>{{ displayUser.following_count }}</strong><span>关注</span></div>
        </div>
        <nav class="side-nav">
          <button v-for="(item, index) in navItems" :key="item" :class="{ selected: activePage === index }" @click="switchPage(index)">
            <component :is="navIcons[index]" :size="18" />
            {{ item }}
            <b v-if="index === 3 && filteredPosts.length">{{ filteredPosts.length }}</b>
          </button>
        </nav>
        <section class="shortcut-section">
          <div class="section-label"><span>常用功能</span></div>
          <button v-for="(item, index) in quickLinks" :key="item[0]" class="shortcut" @click="goTo(item[1])">
            <span class="shortcut-icon">{{ index + 1 }}</span>{{ item[0] }}
          </button>
        </section>
      </aside>

      <section class="content">
        <template v-if="routeCar">
          <section v-if="isCarCommunityPage" class="car-detail-page">
            <button class="back-link" @click="goTo(carRoute(routeCar))">返回车型页</button>
            <section class="page-head">
              <h1>{{ routeCar.name }} 车友圈</h1>
              <p>这里只展示 {{ routeCar.name }} 相关的车主动态、项目记录、聚会和配件讨论。</p>
            </section>
            <section class="composer-bar">
              <img :src="avatarSrc" alt="Tuner hub" />
              <button @click="openComposerForCar(routeCar)">发布 {{ routeCar.name }} 相关动态</button>
              <div>
                <button @click="openComposerForCar(routeCar, '/create/photos')"><ImageIcon :size="18" />图片</button>
                <button @click="openSpecsComposer(routeCar)"><SlidersHorizontal :size="18" />参数</button>
              </div>
            </section>
            <section class="feed">
              <article v-for="post in selectedCarCommunityPosts" :key="post.id" class="feed-item" :class="{ 'without-image': !post.image }">
                <button v-if="post.image" class="feed-image" @click="openPost(post)"><img :src="post.image" :alt="post.title" /></button>
                <div class="feed-copy">
                  <div class="feed-meta"><span class="pill" :class="post.tone">{{ post.type }}</span><b v-if="post.is_pinned" class="pin-badge">置顶</b><span>{{ post.author }} · {{ post.time }}</span></div>
                  <button class="feed-title" @click="openPost(post)">{{ post.title }}</button>
                  <div v-if="canManageCommunity()" class="admin-actions">
                    <button @click.stop="deleteCommunityPost(post)">删除社区内容</button>
                  </div>
                </div>
                <button class="mini-card" @click="goTo(carRoute(routeCar))">
                  <img :src="carDisplayImage(routeCar)" alt="" @error="useFallbackImage" />
                  <strong>{{ routeCar.name }}</strong>
                  <span>车型主页</span>
                </button>
              </article>
              <p v-if="!selectedCarCommunityPosts.length" class="empty-note">暂无 {{ routeCar.name }} 车友内容，登录后可以发布第一条动态。</p>
            </section>
          </section>

          <section v-else class="car-detail-page">
            <button class="back-link" @click="router.back()">返回上一页</button>
            <article class="car-hero-card">
              <img :src="carDisplayImage(routeCar)" :alt="routeCar.name" @error="useFallbackImage" />
              <div>
                <span>{{ routeCar.tag }}</span>
                <h1>{{ routeCar.name }}</h1>
                <p>{{ routeCar.heat }}。这里聚合车款参数、评测资讯、车主动态和改装案例。</p>
                <div class="car-action-line">
                  <strong>{{ routeCar.tag }}</strong>
                  <button class="ghost" @click="goTo('/reviews')">看评测</button>
                  <button class="ghost" @click="goTo(`${carRoute(routeCar)}/community`)">进入车友圈</button>
                </div>
              </div>
            </article>

            <section class="car-summary-grid">
              <div><span>车款配置</span><strong>{{ selectedCarTrims.length }}</strong></div>
              <div><span>驱动形式</span><strong>{{ routeCar.drives?.join(' / ') || selectedCarTrims[0]?.drivetrain || '待补充' }}</strong></div>
              <div><span>相关内容</span><strong>{{ selectedCarArticles.length + selectedCarPosts.length }}</strong></div>
              <div><span>平台热度</span><strong>{{ routeCar.heat.replace('热度 ', '') }}</strong></div>
            </section>

            <section class="trim-section">
              <div class="module-head"><h2>车款参数</h2><button @click="goTo('/reviews')">查看评测</button></div>
              <article v-for="trim in selectedCarTrims" :key="trim.id || `${trim.car}-${trim.name}`" class="trim-row">
                <div>
                  <strong>{{ trim.name }}</strong>
                  <span>{{ trim.engine }} · {{ trim.drivetrain }} · {{ trim.gearbox }}</span>
                </div>
                <div><small>最大功率</small><b>{{ trim.horsepower }}</b></div>
                <div><small>0-100km/h</small><b>{{ trim.acceleration }}</b></div>
                <div><small>能源类型</small><b>{{ trim.fuel || '汽油' }}</b></div>
              </article>
            </section>

            <section class="two-column">
              <div class="article-section">
                <div class="module-head"><h2>评测与导购</h2><button @click="goTo('/reviews')">更多</button></div>
                <article v-for="article in selectedCarArticles" :key="article.id" class="article-row compact" @click="goTo(`/articles/${article.id}`)">
                  <img :src="article.image || assets.hero" :alt="article.title" />
                  <div><span>{{ article.category }}</span><b v-if="article.is_pinned" class="pin-badge">置顶</b><h2>{{ article.title }}</h2></div>
                </article>
                <p v-if="!selectedCarArticles.length" class="empty-note">暂无关联文章。</p>
              </div>
              <div class="data-panel">
                <div class="module-head"><h2>车主动态</h2><button @click="goTo(`${carRoute(routeCar)}/community`)">车友圈</button></div>
                <button v-for="post in selectedCarPosts" :key="post.id" class="topic-row" @click="openPost(post)">
                  <strong>{{ post.title }}</strong>
                  <span>{{ post.author }} · {{ post.time }}</span>
                </button>
                <p v-if="!selectedCarPosts.length" class="empty-note">暂无车主动态。</p>
              </div>
            </section>
          </section>
        </template>

        <template v-else-if="routeDetail">
          <section class="detail-page">
            <button class="back-link" @click="router.back()">返回上一页</button>
            <article v-if="publicInfoPage" class="public-info-page">
              <header>
                <span>Tuner Hub</span>
                <h1>{{ publicInfoPage.title }}</h1>
                <p>{{ publicInfoPage.intro }}</p>
              </header>
              <section v-for="section in publicInfoPage.sections" :key="section[0]">
                <h2>{{ section[0] }}</h2>
                <p>{{ section[1] }}</p>
              </section>
            </article>
            <section v-if="route.path === '/garage'" class="data-panel">
              <div class="module-head"><h2>我的车库</h2><button @click="showGarageModal = true">添加车辆</button></div>
              <article v-for="vehicle in garageVehicles" :key="vehicle.id" class="topic-row">
                <strong>{{ vehicle.name }}</strong>
                <span>{{ vehicle.car || '自定义车辆' }} · {{ vehicle.year || '年份待补充' }} · {{ vehicle.color || '颜色待补充' }}</span>
                <p>{{ vehicle.mods || '暂无改装清单' }}</p>
              </article>
              <p v-if="!garageVehicles.length" class="empty-note">车库还是空的，添加第一辆车吧。</p>
            </section>
            <section v-if="route.path === '/projects'" class="data-panel">
              <div class="module-head"><h2>项目车记录</h2><button @click="showProjectModal = true">添加记录</button></div>
              <article v-for="record in projectRecords" :key="record.id" class="topic-row">
                <strong>{{ record.title }}</strong>
                <span>{{ record.vehicle?.name || '未关联车辆' }} · {{ record.stage || '阶段待补充' }} · {{ record.created_at }}</span>
                <p>{{ record.content || '暂无记录内容' }}</p>
              </article>
              <p v-if="!projectRecords.length" class="empty-note">暂无项目记录，可以添加第一条施工或改装记录。</p>
            </section>
            <section v-if="route.path === '/profile'" class="settings-panel">
              <div class="settings-avatar">
                <img :src="avatarSrc" alt="个人头像" />
                <div>
                  <h2>个人设置</h2>
                  <p>管理头像、昵称和账号展示信息。</p>
                  <label v-if="currentUser" class="avatar-upload">上传新头像<input type="file" accept="image/jpeg,image/png,image/webp" @change="uploadAvatar" /></label>
                  <button v-else class="post-button" @click="openAuth('login')">登录后设置头像</button>
                </div>
              </div>
              <form v-if="currentUser" class="settings-form" @submit.prevent="saveNickname">
                <label for="profile-nickname">昵称</label>
                <div>
                  <input id="profile-nickname" v-model="nicknameDraft" maxlength="20" autocomplete="nickname" />
                  <button type="submit" :disabled="nicknameSaving || !nicknameDraft.trim()">
                    <CheckCircle :size="18" />
                    {{ nicknameSaving ? '保存中' : '保存昵称' }}
                  </button>
                </div>
              </form>
              <form v-if="currentUser" class="settings-form" @submit.prevent="saveEmail">
                <label for="profile-email">找回邮箱</label>
                <div class="email-fields">
                  <input id="profile-email" v-model="emailForm.email" type="email" autocomplete="email" placeholder="邮箱地址" />
                  <input v-model="emailForm.current_password" type="password" autocomplete="current-password" placeholder="当前密码" />
                  <button type="submit" :disabled="emailSaving || !emailForm.email || !emailForm.current_password">
                    <CheckCircle :size="18" />
                    {{ emailSaving ? '保存中' : '保存邮箱' }}
                  </button>
                </div>
              </form>
              <form v-if="currentUser" class="settings-form password-form" @submit.prevent="savePassword">
                <label for="current-password">修改密码</label>
                <div class="password-fields">
                  <input id="current-password" v-model="passwordForm.current_password" type="password" autocomplete="current-password" placeholder="当前密码" />
                  <input v-model="passwordForm.new_password" type="password" autocomplete="new-password" placeholder="新密码" />
                  <input v-model="passwordForm.confirm_password" type="password" autocomplete="new-password" placeholder="确认新密码" />
                  <button type="submit" :disabled="passwordSaving || !passwordForm.current_password || !passwordForm.new_password || !passwordForm.confirm_password">
                    <CheckCircle :size="18" />
                    {{ passwordSaving ? '保存中' : '修改密码' }}
                  </button>
                </div>
              </form>
              <div class="level-rules">
                <div>
                  <h2>等级规则</h2>
                  <p>真实活跃越多，等级越高，最高 Lv.30。</p>
                </div>
                <div class="level-status">
                  <strong>{{ displayUser.level_label || 'Lv.0' }}</strong>
                  <span>{{ displayUser.activity_points || 0 }} 活跃积分</span>
                </div>
                <div class="level-rule-grid">
                  <span><b>在线活跃</b>每日最高 5 分</span>
                  <span><b>参与讨论</b>每日最高 5 分</span>
                  <span><b>优质内容</b>每日最高 1000 分</span>
                  <span><b>粉丝与关注</b>每日最高 2 分</span>
                  <span><b>升级条件</b>每 100 积分升 1 级</span>
                  <span><b>等级上限</b>Lv.30</span>
                </div>
              </div>
            </section>
            <section v-if="route.path === '/saved'" class="data-panel">
              <div class="module-head"><h2>收藏内容</h2><span>{{ savedPosts.length + savedArticles.length }} 条</span></div>
              <button v-for="article in savedArticles" :key="`saved-article-${article.id}`" class="topic-row" @click="goTo(`/articles/${article.id}`)">
                <strong>{{ article.title }}</strong>
                <span>文章 · {{ article.author }} · {{ article.time }}</span>
              </button>
              <button v-for="post in savedPosts" :key="post.id" class="topic-row" @click="openPost(post)">
                <strong>{{ post.title }}</strong>
                <span>帖子 · {{ post.author }} · {{ post.time }}</span>
              </button>
              <p v-if="!currentUser" class="empty-note">登录后查看当前账号的收藏。</p>
              <p v-else-if="!savedPosts.length && !savedArticles.length" class="empty-note">还没有收藏内容。</p>
            </section>
            <section v-if="route.path.startsWith('/messages')" class="data-panel">
              <div class="module-head"><h2>全部私信</h2><button @click="loadMessages">刷新</button></div>
              <button v-for="message in inboxMessages" :key="message.id" class="message-row" :class="{ unread: message.receiver.id === currentUser?.id && !message.is_read, selected: routeMessage?.id === message.id }" @click="openInboxMessage(message)">
                <strong>{{ messageCounterparty(message).nickname || messageCounterparty(message).username }}</strong>
                <span>{{ message.sender.id === currentUser?.id ? '我：' : '' }}{{ message.body }}</span>
                <small>{{ message.time }} · {{ message.receiver.id === currentUser?.id && !message.is_read ? '未读' : '已读' }}</small>
              </button>
              <p v-if="!currentUser" class="empty-note">登录后查看私信。</p>
              <p v-else-if="!inboxMessages.length" class="empty-note">暂无私信。</p>
            </section>
            <section v-if="route.path === '/notifications'" class="data-panel">
              <div class="module-head"><h2>未读消息</h2><span>{{ unreadMessageCount }} 条</span></div>
              <button v-for="message in unreadMessages" :key="message.id" class="message-row unread" @click="openInboxMessage(message)">
                <strong>{{ message.sender.nickname || message.sender.username }}</strong>
                <span>{{ message.body }}</span>
                <small>{{ message.time }}</small>
              </button>
              <p v-if="!currentUser" class="empty-note">登录后查看新消息。</p>
              <p v-else-if="!unreadMessages.length" class="empty-note">暂无未读消息。</p>
            </section>
            <section v-if="route.path === '/topics'" class="data-panel">
              <div class="module-head"><h2>全部专题</h2><span>{{ topicCards.length }} 个</span></div>
              <button v-for="topic in topicCards" :key="topic.title" class="topic-row" @click="goTo(pathFor('topics', topic.title))"><strong>{{ topic.title }}</strong><span>{{ topic.count }}</span><p>{{ topic.desc }}</p></button>
              <p v-if="!topicCards.length" class="empty-note">暂无专题。</p>
            </section>
            <section v-if="route.path === '/events'" class="data-panel">
              <div class="module-head"><h2>全部活动</h2><span>{{ events.length }} 场</span></div>
              <button v-for="event in events" :key="event.name" class="topic-row" @click="goTo(pathFor('events', event.name))"><strong>{{ event.name }}</strong><span>{{ event.meta || '时间地点待补充' }}</span><p>{{ event.count || '报名信息待补充' }}</p></button>
              <p v-if="!events.length" class="empty-note">暂无活动。</p>
            </section>
            <section v-if="route.path === '/clubs'" class="data-panel">
              <div class="module-head"><h2>全部车友会</h2><span>{{ clubs.length }} 个</span></div>
              <button v-for="club in clubs" :key="club[1]" class="topic-row" @click="goTo(pathFor('clubs', club[1]))"><strong>{{ club[1] }}</strong><span>{{ club[0] }}</span><p>{{ club[2] || '成员信息待补充' }}</p></button>
              <p v-if="!clubs.length" class="empty-note">暂无车友会。</p>
            </section>
            <section v-if="route.path === '/shops'" class="data-panel">
              <div class="module-head"><h2>全部认证店家</h2><span>{{ shops.length }} 家</span></div>
              <button v-for="shop in shops" :key="shop[1]" class="topic-row" @click="goTo(pathFor('shops', shop[1]))"><strong>{{ shop[1] }}</strong><span>评分 {{ shop[2] }}</span><p>{{ shop[3] || '服务范围待补充' }}</p></button>
              <p v-if="!shops.length" class="empty-note">暂无认证店家。</p>
            </section>
            <section v-if="route.path === '/search'" class="data-panel search-results">
              <div class="module-head"><h2>搜索结果</h2><span>{{ searchResultCount }} 条</span></div>
              <button v-for="post in searchResults.posts" :key="`post-${post.id}`" class="topic-row" @click="openPost(post)"><strong>{{ post.title }}</strong><span>帖子 · {{ post.author }}</span></button>
              <button v-for="car in searchResults.cars" :key="`car-${car.id}`" class="topic-row" @click="goTo(carRoute(car))"><strong>{{ car.name }}</strong><span>车型 · {{ car.tag }}</span><p>{{ car.heat }}</p></button>
              <button v-for="article in searchResults.articles" :key="`article-${article.id}`" class="topic-row" @click="goTo(`/articles/${article.id}`)"><strong>{{ article.title }}</strong><span>文章 · {{ article.author }}</span></button>
              <button v-for="club in searchResults.clubs" :key="`club-${club[1]}`" class="topic-row" @click="goTo(pathFor('clubs', club[1]))"><strong>{{ club[1] }}</strong><span>车友会 · {{ club[0] }}</span><p>{{ club[2] }}</p></button>
              <button v-for="shop in searchResults.shops" :key="`shop-${shop[1]}`" class="topic-row" @click="goTo(pathFor('shops', shop[1]))"><strong>{{ shop[1] }}</strong><span>店家 · 评分 {{ shop[2] }}</span><p>{{ shop[3] }}</p></button>
              <button v-for="part in searchResults.parts" :key="`part-${part.name}`" class="topic-row" @click="goTo(pathFor('market', part.name))"><strong>{{ part.name }}</strong><span>配件</span><p>{{ part.status }}</p></button>
              <p v-if="!query.trim()" class="empty-note">请输入关键词后按回车搜索。</p>
              <p v-else-if="!searchResultCount" class="empty-note">没有找到相关内容。</p>
            </section>
            <article v-if="routeArticle && !isFunctionalListPage" class="article-detail">
              <header>
                <div class="article-detail-labels">
                  <div>
                    <span>{{ routeArticle.category }}文章</span>
                    <b v-if="routeArticle.is_pinned" class="pin-badge">置顶</b>
                  </div>
                  <button v-if="canManageCommunity()" class="danger-button article-delete-button" @click="deleteCommunityArticle(routeArticle)"><Trash :size="16" />删除文章</button>
                </div>
                <div class="article-author-line">
                  <img :src="routeArticle.author_avatar || defaultAvatar" :alt="routeArticle.author" />
                  <div>
                    <strong>{{ routeArticle.author || '用户投稿' }}</strong>
                    <small>{{ routeArticle.time }} · {{ routeArticle.car || '综合内容' }} · {{ routeArticle.views || 0 }} 阅读</small>
                  </div>
                </div>
                <h1>{{ routeArticle.title }}</h1>
                <p v-if="visibleArticleSummary" class="article-summary">{{ visibleArticleSummary }}</p>
              </header>
              <figure v-if="routeArticle.has_cover && routeArticle.image" class="article-cover">
                <img :src="routeArticle.image" :alt="routeArticle.title" />
                <figcaption v-if="routeArticle.image_caption">{{ routeArticle.image_caption }}</figcaption>
              </figure>
              <div v-if="routeArticle.blocks?.length" class="article-body article-blocks">
                <template v-for="block in routeArticle.blocks" :key="block.id || block.position">
                  <h2 v-if='block.type === "heading"'>{{ block.text }}</h2>
                  <p v-else-if='block.type === "paragraph"'>{{ block.text }}</p>
                  <figure v-else-if='block.type === "image"' class="article-inline-image">
                    <img :src="block.image" :alt="block.caption || routeArticle.title" />
                    <figcaption v-if="block.caption">{{ block.caption }}</figcaption>
                  </figure>
                </template>
              </div>
              <div v-else class="article-body">{{ routeArticle.body || routeArticle.summary }}</div>
            </article>
            <section v-if="routeArticle" class="post-interaction-panel article-interaction-panel">
              <div class="post-primary-actions">
                <button :class="{ liked: routeArticle.is_liked }" @click="toggleArticleLike(routeArticle)"><Sparkle :weight="routeArticle.is_liked ? 'fill' : 'regular'" :size="18" />{{ routeArticle.likes || 0 }} 点赞</button>
                <button :class="{ saved: routeArticle.is_saved }" @click="toggleArticleSave(routeArticle)"><BookmarkSimple :weight="routeArticle.is_saved ? 'fill' : 'regular'" :size="18" />{{ routeArticle.is_saved ? '已收藏' : '收藏' }}</button>
                <button @click="openContentReport('article', routeArticle)"><Flag :size="18" />举报</button>
              </div>
              <form class="comment-form" @submit.prevent="submitArticleComment">
                <textarea v-model="articleCommentBody" maxlength="1000" placeholder="说说这篇案例对你的帮助或疑问"></textarea>
                <button type="submit" :disabled="articleCommentSubmitting || !articleCommentBody.trim()">{{ articleCommentSubmitting ? '发布中' : '发表评论' }}</button>
              </form>
              <div class="comment-list">
                <article v-for="comment in articleComments" :key="comment.id">
                  <img :src="comment.avatar || defaultAvatar" :alt="comment.author" />
                  <div><strong>{{ comment.author }}</strong><small>{{ comment.time }}</small><p>{{ comment.body }}</p></div>
                </article>
                <p v-if="!articleComments.length" class="empty-note">暂无评论。</p>
              </div>
            </section>
            <article v-else-if="!isFunctionalListPage" class="detail-hero-card">
              <figure v-if="routeDetail.image" class="detail-media">
                <img :src="routeDetail.image" :alt="routeDetail.title" />
                <figcaption v-if="routeDetail.imageCaption">{{ routeDetail.imageCaption }}</figcaption>
              </figure>
              <div>
                <div class="detail-labels">
                  <span>{{ routeDetail.type }}</span>
                  <b v-if="routeDetail.isPinned" class="pin-badge">置顶</b>
                </div>
                <h1>{{ routeDetail.title }}</h1>
                <p>{{ routeDetail.body }}</p>
                <small>{{ routeDetail.meta }}</small>
                <button v-if="routePost && canManageCommunity()" class="danger-button" @click="deleteCommunityPost(routePost)">删除社区内容</button>
              </div>
            </article>
            <section v-if="routePost" class="post-interaction-panel">
              <div class="post-primary-actions">
                <button :class="{ liked: routePost.is_liked }" @click="toggleLike(routePost)"><Sparkle :weight="routePost.is_liked ? 'fill' : 'regular'" :size="18" />{{ routePost.likes }} 点赞</button>
                <button :class="{ saved: routePost.is_saved }" @click="toggleSave(routePost.id)"><BookmarkSimple :weight="routePost.is_saved ? 'fill' : 'regular'" :size="18" />{{ routePost.is_saved ? '已收藏' : '收藏' }}</button>
                <button @click="openContentReport('post', routePost)"><Flag :size="18" />举报</button>
              </div>
              <form class="comment-form" @submit.prevent="submitComment">
                <textarea v-model="commentBody" maxlength="1000" placeholder="写下真实的用车或改装交流内容"></textarea>
                <button type="submit" :disabled="commentSubmitting || !commentBody.trim()">{{ commentSubmitting ? '发布中' : '发表评论' }}</button>
              </form>
              <div class="comment-list">
                <article v-for="comment in postComments" :key="comment.id">
                  <img :src="comment.avatar || defaultAvatar" :alt="comment.author" />
                  <div><strong>{{ comment.author }}</strong><small>{{ comment.time }}</small><p>{{ comment.body }}</p></div>
                </article>
                <p v-if="!postComments.length" class="empty-note">暂无评论。</p>
              </div>
            </section>
            <section v-if="!isFunctionalListPage" class="data-panel">
              <div class="module-head"><h2>详细信息</h2><button @click="goTo('/admin-guide')">内容说明</button></div>
              <div class="detail-info-grid">
                <span v-for="row in routeDetail.rows" :key="`${row[0]}-${row[1]}`"><b>{{ row[0] }}</b>{{ row[1] }}</span>
              </div>
            </section>
            <section v-if="!isFunctionalListPage" class="feed">
              <article v-for="post in posts.slice(0, 3)" :key="post.id" class="feed-item" :class="{ 'without-image': !post.image }">
                <button v-if="post.image" class="feed-image" @click="openPost(post)"><img :src="post.image" :alt="post.title" /></button>
                <div class="feed-copy">
                  <div class="feed-meta"><span class="pill" :class="post.tone">{{ post.type }}</span><b v-if="post.is_pinned" class="pin-badge">置顶</b><span>{{ post.author }} · {{ post.time }}</span></div>
                  <button class="feed-title" @click="openPost(post)">{{ post.title }}</button>
                </div>
                <button class="mini-card" @click="openPost(post)">
                  <img v-if="post.image" :src="post.image" alt="" />
                  <strong>{{ post.car }}</strong>
                  <span>相关内容</span>
                </button>
              </article>
            </section>
          </section>
        </template>

        <template v-else-if="activePage === 0">
          <section class="portal-hero" :class="{ 'single-story': articles.length === 1, 'empty-story': !articles.length }">
            <article v-if="articles[0]" class="portal-main-story" role="button" tabindex="0" @click="goTo(`/articles/${articles[0].id}`)" @keydown.enter.prevent="goTo(`/articles/${articles[0].id}`)" @keydown.space.prevent="goTo(`/articles/${articles[0].id}`)">
              <img :src="articles[0].image || assets.hero" :alt="articles[0].title" />
              <div>
                <span>{{ articles[0].category }}</span>
                <b v-if="articles[0].is_pinned" class="pin-badge">置顶</b>
                <h1>{{ articles[0].title }}</h1>
              </div>
            </article>
            <div v-if="articles.length > 1" class="portal-news-list">
              <button v-for="article in articles.slice(1, 5)" :key="article.id" @click="goTo(`/articles/${article.id}`)">
                <span>{{ article.is_pinned ? '置顶 · ' : '' }}{{ article.category }}</span>
                <strong>{{ article.title }}</strong>
                <small>{{ article.author }} · {{ article.car || '综合' }}</small>
              </button>
            </div>
            <div v-else-if="!articles.length" class="portal-empty-story">
              <strong>分享第一篇真实车主文章</strong>
              <p>记录选车、长期使用、维护和改装过程。</p>
              <button @click="openArticleComposer()">发布文章</button>
            </div>
          </section>

          <section class="portal-tools">
            <button @click="goTo('/cars')"><Compass :size="20" />选车</button>
            <button @click="goTo('/reviews')"><Gauge :size="20" />看文章</button>
            <button @click="goTo('/community')"><ChatCircle :size="20" />车友圈</button>
            <button @click="goTo('/market')"><Wrench :size="20" />配件专区</button>
            <button @click="goTo('/rankings')"><Star :size="20" />排行榜</button>
          </section>

          <section v-if="featuredPost || buyingGuides.length" class="home-lead" :class="{ 'without-featured': !featuredPost }">
            <article v-if="featuredPost" class="lead-story" role="button" tabindex="0" @click="openPost(featuredPost)">
              <img :src="featuredPost.image || assets.supra" :alt="featuredPost.title" />
              <div>
                <span>编辑精选</span>
                <h1>{{ featuredPost.title }}</h1>
              </div>
            </article>
            <div class="lead-list">
              <button v-for="item in buyingGuides" :key="item.id" @click="goTo(`/guides/${item.id}`)">{{ item.title }}</button>
              <p v-if="!buyingGuides.length" class="empty-note">暂无导购内容。</p>
            </div>
          </section>

          <section class="composer-bar">
            <img :src="avatarSrc" alt="Tuner hub" />
            <button @click="openComposer">分享聊车动态、改装记录或车友聚会</button>
            <div>
              <button @click="openPhotoComposer"><ImageIcon :size="18" />图片</button>
              <button @click="openSpecsComposer()"><SlidersHorizontal :size="18" />参数</button>
              <button @click="openArticleComposer()"><PaperPlaneTilt :size="18" />文章</button>
            </div>
          </section>

          <section class="activity-tabs">
            <div>
              <button v-for="(item, index) in feedFilters" :key="item" :class="{ active: activeFilter === index }" @click="activeFilter = index">{{ item }}</button>
            </div>
            <span class="sort-button static"><Funnel :size="17" />最新发布</span>
          </section>

          <section class="feed">
            <article v-for="post in filteredPosts" :key="post.id" class="feed-item home-feed-item" :class="{ 'without-image': !post.image }">
              <button v-if="post.image" class="feed-image" @click="openPost(post)"><img :src="post.image" :alt="post.title" /></button>
              <div class="feed-copy">
                <div class="feed-meta"><span class="pill" :class="post.tone">{{ post.type }}</span><b v-if="post.is_pinned" class="pin-badge">置顶</b><span>{{ post.author }} · {{ post.time }}</span></div>
                <button class="feed-title" @click="openPost(post)">{{ post.title }}</button>
                <div class="feed-actions">
                  <button @click="toggleSave(post.id)" :class="{ saved: post.is_saved }"><BookmarkSimple :weight="post.is_saved ? 'fill' : 'regular'" :size="17" />{{ post.is_saved ? '已收藏' : '收藏' }}</button>
                  <button @click="openPost(post)"><ChatCircle :size="17" />{{ post.comments }}</button>
                  <button :class="{ liked: post.is_liked }" @click="toggleLike(post)"><Sparkle :weight="post.is_liked ? 'fill' : 'regular'" :size="17" />{{ post.likes }}</button>
                </div>
              </div>
            </article>
            <div v-if="!filteredPosts.length" class="empty-state-block">
              <strong>还没有车友动态</strong>
              <p>从真实用车感受、维护记录或改装进度开始。</p>
              <button @click="openComposer">发布第一条动态</button>
            </div>
          </section>
        </template>

        <template v-else-if="activePage === 1">
          <section class="page-head">
            <h1>选车</h1>
            <p>按驱动形式和车型关键词筛选性能车，再进入车型页查看车款参数、评测和车主内容。</p>
          </section>

          <section class="car-filter-panel">
            <label class="car-filter-search">
              <MagnifyingGlass :size="18" />
              <input v-model="carKeyword" placeholder="搜索车型、动力、变速箱" />
            </label>
            <div class="filter-row">
              <span>驱动</span>
              <button v-for="(item, index) in driveFilters" :key="item" :class="{ active: activeDriveFilter === index }" @click="activeDriveFilter = index">{{ item }}</button>
            </div>
          </section>

          <section class="car-grid">
            <article v-for="car in filteredCars" :key="car.name" class="car-card" role="button" tabindex="0" @click="goTo(carRoute(car))" @keydown.enter.prevent="goTo(carRoute(car))" @keydown.space.prevent="goTo(carRoute(car))">
                <img :src="car.displayImg" :alt="car.name" @error="useFallbackImage" />
                <div>
                  <span>{{ car.tag }}</span>
                  <h2>{{ car.name }}</h2>
                  <p>{{ car.drives.join(' / ') || '待补充驱动' }}</p>
                  <small>{{ car.trims.length }} 个车款 · {{ car.drives.join(' / ') || '待补充驱动' }}</small>
                </div>
            </article>
          </section>
          <section v-if="!filteredCars.length" class="data-panel">
            <p class="empty-note">没有找到符合条件的车型，可以放宽驱动筛选或调整关键词。</p>
          </section>

          <section class="two-column">
            <div class="data-panel">
              <div class="module-head"><h2>{{ hasRankingActivity ? '改装热榜' : '新收录车型' }}</h2><button @click="goTo('/rankings')">查看全部</button></div>
              <template v-if="hasRankingActivity">
                <button v-for="row in rankings" :key="row[0]" class="rank-row" @click="goTo(pathFor('cars', row[1]))">
                  <b>{{ row[0] }}</b><strong>{{ row[1] }}</strong><span>{{ row[2] }}</span><i>{{ row[3] }}</i>
                </button>
              </template>
              <template v-else>
                <button v-for="car in enrichedCars.slice(0, 8)" :key="car.id" class="topic-row" @click="goTo(carRoute(car))">
                  <strong>{{ car.name }}</strong><span>{{ car.tag }}</span>
                </button>
              </template>
            </div>
            <div class="data-panel">
              <div class="module-head"><h2>热门专题</h2><button @click="goTo('/topics')">更多专题</button></div>
              <button v-for="topic in topicCards" :key="topic.title" class="topic-row" @click="goTo(pathFor('topics', topic.title))">
                <strong>{{ topic.title }}</strong>
                <span>{{ topic.count }}</span>
                <p>{{ topic.desc }}</p>
              </button>
              <p v-if="!topicCards.length" class="empty-note">暂无专题。</p>
            </div>
          </section>

          <section class="data-panel">
            <div class="module-head"><h2>认证改装店</h2><button @click="goTo('/cars')">返回选车</button></div>
            <div class="shop-grid">
              <button v-for="shop in shops" :key="shop[0]" class="shop-card" @click="goTo(pathFor('shops', shop[1]))">
                <span>{{ shop[0] }}</span>
                <div><strong>{{ shop[1] }}</strong><small><Star :size="13" weight="fill" /> {{ shop[2] }} · {{ shop[3] }}</small></div>
                <b>TH 认证</b>
              </button>
              <p v-if="!shops.length" class="empty-note">暂无改装店。</p>
            </div>
          </section>
        </template>

        <template v-else-if="activePage === 2">
          <section class="page-head">
            <h1>文章</h1>
            <p>真实车主故事、长期用车、试驾评测和改装案例。</p>
          </section>
          <section class="article-section">
            <article v-for="article in reviewArticles" :key="article.id" class="article-row" role="button" tabindex="0" @click="goTo(`/articles/${article.id}`)" @keydown.enter.prevent="goTo(`/articles/${article.id}`)" @keydown.space.prevent="goTo(`/articles/${article.id}`)">
              <img :src="article.image || assets.hero" :alt="article.title" />
              <div><span>{{ article.category }}</span><b v-if="article.is_pinned" class="pin-badge">置顶</b><h2>{{ article.title }}</h2><small>{{ article.author }} · {{ article.car || '综合' }}</small></div>
            </article>
            <div v-if="!reviewArticles.length" class="empty-state-block">
              <strong>还没有车主文章</strong><p>长期用车、改装案例和真实体验都值得记录。</p><button @click="openArticleComposer()">发布文章</button>
            </div>
          </section>
        </template>

        <template v-else-if="activePage === 3">
          <section class="page-head">
            <h1>车友圈</h1>
            <p>真实车主动态、项目车记录、车友会活动和用车讨论。</p>
          </section>
          <section class="composer-bar">
            <img :src="avatarSrc" alt="Tuner hub" />
            <button @click="openComposer">发布动态</button>
            <div>
              <button @click="openPhotoComposer"><ImageIcon :size="18" />图片</button>
              <button @click="openSpecsComposer()"><SlidersHorizontal :size="18" />参数</button>
              <button @click="openArticleComposer()"><PaperPlaneTilt :size="18" />文章</button>
            </div>
          </section>
          <section class="activity-tabs">
            <div>
              <button v-for="(item, index) in feedFilters" :key="item" :class="{ active: activeFilter === index }" @click="activeFilter = index">{{ item }}</button>
            </div>
            <span class="sort-button static"><Funnel :size="17" />最新发布</span>
          </section>
          <section class="feed">
            <article v-for="post in filteredPosts" :key="post.id" class="feed-item" :class="{ 'without-image': !post.image }">
              <button v-if="post.image" class="feed-image" @click="openPost(post)"><img :src="post.image" :alt="post.title" /></button>
              <div class="feed-copy">
                <div class="feed-meta"><span class="pill" :class="post.tone">{{ post.type }}</span><b v-if="post.is_pinned" class="pin-badge">置顶</b><span>{{ post.author }} · {{ post.time }}</span></div>
                <button class="feed-title" @click="openPost(post)">{{ post.title }}</button>
                <div v-if="canManageCommunity()" class="admin-actions">
                  <button @click.stop="deleteCommunityPost(post)">删除社区内容</button>
                </div>
              </div>
              <button class="mini-card" @click="openPost(post)">
                <img v-if="post.image" :src="post.image" alt="" />
                <strong>{{ post.car }}</strong>
                <span>车主动态</span>
              </button>
            </article>
            <div v-if="!filteredPosts.length" class="empty-state-block">
              <strong>车友圈正在等待第一条动态</strong><p>可以分享用车问题、维护记录或改装进度。</p><button @click="openComposer">发布动态</button>
            </div>
          </section>
        </template>

        <template v-else-if="activePage === 4">
          <section class="page-head">
            <h1>配件专区</h1>
            <p>改装件、二手件、安装案例和适配车型集中展示。</p>
          </section>
          <section class="car-grid">
            <article v-for="item in market" :key="item.name" class="car-card" role="button" tabindex="0" @click="goTo(pathFor('market', item.name))">
              <img :src="item.img" :alt="item.name" @error="useFallbackImage" />
              <div>
                <span>{{ item.status || '配件动态' }}</span>
                <h2>{{ item.name }}</h2>
                <p>成色说明 / 安装案例 / 适配车型</p>
                <small>进入详情查看配件动态</small>
              </div>
            </article>
            <div v-if="!market.length" class="empty-state-block">
              <strong>还没有配件内容</strong><p>发布配件安装案例、适配经验或真实二手件信息。</p><button @click="openPostComposerForType('二手市场')">发布配件内容</button>
            </div>
          </section>
          <section class="two-column">
            <div class="data-panel">
              <div class="module-head"><h2>热门配件讨论</h2><button @click="goTo('/community')">车友圈</button></div>
              <button v-for="post in posts.filter((item) => item.type === '二手市场').slice(0, 4)" :key="post.id" class="topic-row" @click="openPost(post)">
                <strong>{{ post.title }}</strong>
                <span>{{ post.author }} · {{ post.time }}</span>
              </button>
              <p v-if="!posts.filter((item) => item.type === '二手市场').length" class="empty-note">暂无配件讨论。</p>
            </div>
            <div class="data-panel">
              <div class="module-head"><h2>适配车型</h2><button @click="goTo('/cars')">选车</button></div>
              <button v-for="car in enrichedCars.slice(0, 6)" :key="car.name" class="topic-row" @click="goTo(carRoute(car))">
                <strong>{{ car.name }}</strong>
                <span>{{ car.tag }}</span>
                <p>{{ car.trims.length }} 个车款 · {{ car.drives.join(' / ') || '待补充驱动' }}</p>
              </button>
            </div>
          </section>
        </template>

        <template v-else>
          <section class="page-head">
            <h1>{{ hasRankingActivity ? '排行榜' : '新收录车型' }}</h1>
            <p>{{ hasRankingActivity ? '按照真实内容、点赞和讨论量生成。' : '当前互动数据不足，暂不生成热度排名。' }}</p>
          </section>
          <section class="data-panel">
            <template v-if="hasRankingActivity">
              <button v-for="row in rankings" :key="row[0]" class="rank-row" @click="goTo(pathFor('cars', row[1]))">
                <b>{{ row[0] }}</b><strong>{{ row[1] }}</strong><span>{{ row[2] }}</span><i>{{ row[3] }}</i>
              </button>
            </template>
            <template v-else>
              <button v-for="car in enrichedCars" :key="car.id" class="topic-row" @click="goTo(carRoute(car))">
                <strong>{{ car.name }}</strong><span>{{ car.tag }} · {{ car.trims.length }} 个车款</span>
              </button>
            </template>
          </section>
        </template>
      </section>

      <aside class="right-rail">
        <section class="panel">
          <div class="panel-head"><h2>{{ hasRankingActivity ? '热榜' : '新收录车型' }}</h2><button @click="goTo('/rankings')">更多</button></div>
          <template v-if="hasRankingActivity">
            <button v-for="row in rankings.slice(0, 4)" :key="row[0]" class="rank-row compact" @click="goTo(pathFor('cars', row[1]))">
              <b>{{ row[0] }}</b><strong>{{ row[1] }}</strong><span>{{ row[3] }}</span>
            </button>
          </template>
          <template v-else>
            <button v-for="car in enrichedCars.slice(0, 4)" :key="car.id" class="topic-row compact-topic" @click="goTo(carRoute(car))">
              <strong>{{ car.name }}</strong><span>{{ car.tag }}</span>
            </button>
          </template>
        </section>

        <section v-if="clubs.length" class="panel">
          <div class="panel-head"><h2>推荐车友</h2><button @click="goTo('/profile')">我的</button></div>
          <article v-for="user in userCards.filter((item) => item.id !== currentUser?.id).slice(0, 5)" :key="user.id" class="user-row">
            <img :src="user.avatar || defaultAvatar" :alt="user.nickname || user.username" />
            <div>
              <strong>{{ user.nickname || user.username }}</strong>
              <small>{{ user.level_label }} · {{ user.followers_count }} 粉丝 · {{ user.following_count }} 关注</small>
              <span>{{ user.signature || '暂无签名' }}</span>
            </div>
            <div class="user-actions">
              <button @click="toggleFollow(user)">{{ user.is_following ? '已关注' : '关注' }}</button>
              <button @click="openMessage(user)">私信</button>
            </div>
          </article>
          <p v-if="!userCards.filter((item) => item.id !== currentUser?.id).length" class="empty-note">暂无其他真实用户。</p>
        </section>

        <section v-if="route.path.startsWith('/messages')" class="panel">
          <div class="panel-head"><h2>私信</h2><button @click="loadMessages">刷新</button></div>
          <button v-for="message in inboxMessages.slice(0, 5)" :key="message.id" class="message-row small" :class="{ unread: message.receiver.id === currentUser?.id && !message.is_read }" @click="openInboxMessage(message)">
            <strong>{{ messageCounterparty(message).nickname || messageCounterparty(message).username }}</strong>
            <span>{{ message.sender.id === currentUser?.id ? '我：' : '' }}{{ message.body }}</span>
            <small>{{ message.time }}</small>
          </button>
          <p v-if="!inboxMessages.length" class="empty-note">暂无私信。</p>
        </section>

        <section class="panel">
          <div class="panel-head"><h2>活跃车友会</h2><button @click="goTo('/clubs')">全部</button></div>
          <button v-for="club in clubs" :key="club[0]" class="club-row" @click="goTo(pathFor('clubs', club[1]))">
            <span>{{ club[0] }}</span><div><strong>{{ club[1] }}</strong><small>{{ club[2] }}</small></div><i>热</i>
          </button>
        </section>

        <section v-if="events.length" class="panel">
          <div class="panel-head"><h2>附近聚会</h2><button @click="goTo('/events')">全部</button></div>
          <button v-for="event in events" :key="event.name" class="event-row" @click="goTo(pathFor('events', event.name))">
            <img :src="event.img" alt="" @error="useFallbackImage" /><div><strong>{{ event.name }}</strong><small><CalendarBlank :size="13" /> {{ event.meta }}</small><span>{{ event.count }}</span></div>
          </button>
        </section>

        <section v-if="market.length" class="panel">
          <div class="panel-head"><h2>车友热议配件</h2><button @click="goTo('/market')">全部</button></div>
          <button v-for="item in market" :key="item.name" class="product-row" @click="goTo(pathFor('market', item.name))">
            <img :src="item.img" alt="" @error="useFallbackImage" /><div><strong>{{ item.name }}</strong><span>{{ item.status || '配件动态' }}</span></div>
          </button>
        </section>
      </aside>
    </main>

    <footer class="site-footer">
      <span>© 2026 Tuner Hub</span>
      <nav aria-label="站点信息">
        <button @click="goTo('/terms')">用户协议</button>
        <button @click="goTo('/privacy')">隐私政策</button>
        <button @click="goTo('/community-rules')">社区规范</button>
        <button @click="goTo('/contact')">联系平台</button>
      </nav>
    </footer>

    <div v-if="showComposer" class="modal-wrap">
      <button class="scrim" @click="showComposer = false"></button>
      <section class="composer-modal" :class="{ 'article-composer-modal': composerMode === 'article' }" role="dialog" aria-modal="true" aria-labelledby="composer-title">
        <div class="modal-head">
          <h2 id="composer-title">发布内容</h2>
          <button class="icon-button" aria-label="关闭发布窗口" @click="showComposer = false"><X :size="20" /></button>
        </div>
        <div class="composer-mode-tabs">
          <button :class="{ active: composerMode === 'post' }" @click="composerMode = 'post'">发布动态</button>
          <button :class="{ active: composerMode === 'article' }" @click="composerMode = 'article'">发布文章</button>
        </div>

        <template v-if="composerMode === 'post'">
          <div class="type-grid">
            <button v-for="label in feedFilters.slice(1)" :key="label" :class="{ active: draftType === label }" @click="draftType = label">{{ label }}</button>
          </div>
          <input v-model="draftTitle" class="composer-title" maxlength="180" placeholder="请输入帖子标题" />
          <select v-model="draftCar" class="composer-title">
            <option value="">选择关联车型（可选）</option>
            <option v-for="car in enrichedCars" :key="car.name" :value="car.name">{{ car.name }}</option>
          </select>
          <textarea v-model="draft" maxlength="20000" placeholder="聊聊用车感受、改装进度、施工记录或聚会信息"></textarea>
          <input ref="postImageInput" class="composer-image-input" type="file" accept="image/jpeg,image/png,image/webp" @change="handlePostImage" />
          <div v-if="draftImagePreview" class="composer-image-preview">
            <img :src="draftImagePreview" alt="帖子图片预览" />
            <button class="icon-button" title="移除图片" @click="clearDraftImage"><X :size="18" /></button>
          </div>
          <input v-if="draftImagePreview" v-model="draftImageCaption" class="composer-caption-input" maxlength="200" placeholder="添加图片说明（可选，最多200字）" />
          <section v-if="showSpecsPanel" class="composer-extra-panel">
            <div class="composer-extra-head">
              <strong>车辆参数</strong>
              <button class="icon-button" title="收起参数" @click="showSpecsPanel = false"><X :size="17" /></button>
            </div>
            <div v-for="(spec, index) in draftSpecs" :key="index" class="composer-spec-row">
              <input v-model="spec.label" maxlength="38" placeholder="参数名称，如轮毂" />
              <input v-model="spec.value" maxlength="80" placeholder="数值，如18×9.5J" />
              <button class="icon-button" title="删除此参数" @click="removeDraftSpec(index)"><X :size="17" /></button>
            </div>
            <button class="composer-add-row" @click="addDraftSpec"><Plus :size="17" />继续添加</button>
          </section>
          <section v-if="showLocationPanel" class="composer-extra-panel">
            <div class="composer-extra-head">
              <strong>所在位置</strong>
              <button class="icon-button" title="移除位置" @click="showLocationPanel = false; draftLocation = ''"><X :size="17" /></button>
            </div>
            <div class="composer-location-row">
              <MapPin :size="19" />
              <input ref="locationInput" v-model="draftLocation" maxlength="120" placeholder="城市或地点，如上海国际赛车场" />
            </div>
          </section>
          <div class="composer-tools">
            <button @click="choosePostImage"><ImageIcon :size="18" />{{ draftImage ? '更换图片' : '添加图片' }}</button>
            <button :class="{ active: showSpecsPanel }" @click="revealSpecsPanel"><Gauge :size="18" />添加参数</button>
            <button :class="{ active: showLocationPanel }" @click="revealLocationPanel"><MapPin :size="18" />添加位置</button>
          </div>
          <button class="post-button" :disabled="publishingPost" @click="publishPost"><PaperPlaneTilt :size="18" />{{ publishingPost ? '发布中' : '发布动态' }}</button>
        </template>

        <template v-else-if='composerMode === "article"'>
          <div class="type-grid article-category-grid">
            <button v-for="label in ['车主故事', '长期用车', '改装案例', '评测']" :key="label" :class="{ active: articleDraft.category === label }" @click="articleDraft.category = label">{{ label }}</button>
          </div>
          <input v-model="articleDraft.title" class="composer-title" maxlength="180" placeholder="文章标题，例如：21万公里的宝马 M2C" />
          <textarea v-model="articleDraft.summary" class="article-summary-input" maxlength="500" placeholder="用两三句话说明文章价值，不要重复正文第一段（可选）"></textarea>
          <select v-model="articleDraft.car" class="composer-title">
            <option value="">选择关联车型（可选）</option>
            <option v-for="car in enrichedCars" :key="car.name" :value="car.name">{{ car.name }}</option>
          </select>

          <section class="article-cover-editor">
            <div class="composer-extra-head"><strong>文章封面</strong></div>
            <input ref="articleCoverInput" class="composer-image-input" type="file" accept="image/jpeg,image/png,image/webp" @change="handleArticleCover" />
            <button v-if="!articleCoverPreview" class="article-image-picker" @click="articleCoverInput?.click()"><ImageIcon :size="20" />选择封面</button>
            <div v-else class="composer-image-preview article-cover-preview">
              <img :src="articleCoverPreview" alt="文章封面预览" />
              <button class="icon-button" title="移除封面" @click="clearArticleCover"><X :size="18" /></button>
            </div>
            <input v-if="articleCoverPreview" v-model="articleDraft.image_caption" class="composer-caption-input" maxlength="200" placeholder="封面图片说明（可选）" />
          </section>

          <section class="article-block-editor">
            <div class="composer-extra-head"><strong>文章正文</strong></div>
            <input ref="articleBulkImageInput" class="composer-image-input" type="file" accept="image/jpeg,image/png,image/webp" multiple @change="handleArticleBulkImages" />
            <article v-for="(block, index) in articleDraftBlocks" :key="block.key" class="article-draft-block" :class="{ selected: selectedArticleBlockIndex === index }" @click="selectedArticleBlockIndex = index">
              <div class="article-block-head">
                <span>{{ block.type === 'heading' ? '小标题' : block.type === 'image' ? '图片' : '正文段落' }}</span>
                <div>
                  <button class="icon-button" title="在此段后插入图片" @click.stop="chooseArticleImagesAfter(index)"><ImageIcon :size="17" /></button>
                  <button class="icon-button" title="上移" :disabled="index === 0" @click="moveArticleBlock(index, -1)"><ArrowUp :size="17" /></button>
                  <button class="icon-button" title="下移" :disabled="index === articleDraftBlocks.length - 1" @click="moveArticleBlock(index, 1)"><ArrowDown :size="17" /></button>
                  <button class="icon-button" title="删除" @click="removeArticleBlock(index)"><X :size="17" /></button>
                </div>
              </div>
              <input v-if="block.type === 'heading'" v-model="block.text" maxlength="120" placeholder="输入小标题" />
              <textarea v-else-if="block.type === 'paragraph'" v-model="block.text" maxlength="10000" placeholder="输入正文内容"></textarea>
              <div v-else class="article-block-image-editor">
                <input type="file" accept="image/jpeg,image/png,image/webp" @change="handleArticleBlockImage($event, block)" />
                <img v-if="block.preview" :src="block.preview" alt="正文图片预览" />
                <input v-if="block.preview" v-model="block.caption" maxlength="200" placeholder="图片说明（可选）" />
              </div>
            </article>
            <div class="article-block-tools">
              <button @click="addArticleBlock('paragraph')"><Plus :size="17" />正文段落</button>
              <button @click="addArticleBlock('heading')"><Plus :size="17" />小标题</button>
              <button @click="chooseArticleImagesAfter(selectedArticleBlockIndex)"><ImageIcon :size="17" />插入图片</button>
            </div>
          </section>
          <button class="post-button" :disabled="publishingArticle" @click="publishArticle"><PaperPlaneTilt :size="18" />{{ publishingArticle ? '发布中' : '发布文章' }}</button>
        </template>
      </section>
    </div>

    <div v-if="showAuthModal" class="modal-wrap">
      <button class="scrim" @click="showAuthModal = false"></button>
      <section class="auth-modal" role="dialog" aria-modal="true" aria-labelledby="auth-title">
        <div class="modal-head">
          <h2 id="auth-title">{{ authTitle }}</h2>
          <button class="icon-button" aria-label="关闭账号窗口" @click="showAuthModal = false"><X :size="20" /></button>
        </div>
        <div v-if="authMode === 'login' || authMode === 'register'" class="auth-tabs">
          <button :class="{ active: authMode === 'login' }" @click="authMode = 'login'; authMessage = ''">登录</button>
          <button :class="{ active: authMode === 'register' }" @click="authMode = 'register'; authMessage = ''">注册</button>
        </div>
        <input v-if="authMode === 'login' || authMode === 'register'" v-model="authForm.username" placeholder="账号" />
        <input v-if="authMode === 'register'" v-model="authForm.nickname" placeholder="昵称" />
        <input v-if="authMode === 'register'" v-model="authForm.email" placeholder="邮箱" />
        <input v-if="authMode === 'login' || authMode === 'register'" v-model="authForm.password" placeholder="密码" type="password" />
        <input v-if="authMode === 'forgot'" v-model="resetForm.email" placeholder="注册邮箱" type="email" autocomplete="email" />
        <input v-if="authMode === 'reset'" v-model="resetForm.new_password" placeholder="新密码" type="password" autocomplete="new-password" />
        <input v-if="authMode === 'reset'" v-model="resetForm.confirm_password" placeholder="确认新密码" type="password" autocomplete="new-password" />
        <div v-if="authMode === 'register'" class="terms-consent">
          <input id="accept-terms" v-model="authForm.accepted_terms" type="checkbox" aria-label="同意用户协议和隐私政策" />
          <span>我已阅读并同意 <button type="button" @click="showAuthModal = false; goTo('/terms')">用户协议</button> 和 <button type="button" @click="showAuthModal = false; goTo('/privacy')">隐私政策</button></span>
        </div>
        <button v-if="authMode === 'login'" class="forgot-password-button" @click="authMode = 'forgot'; authMessage = ''">忘记密码？</button>
        <p v-if="authMessage" class="form-message">{{ authMessage }}</p>
        <button class="post-button" @click="submitAuth">
          {{ authMode === 'login' ? '登录' : authMode === 'register' ? '注册并登录' : authMode === 'forgot' ? '发送重置邮件' : '重置密码' }}
        </button>
        <button v-if="authMode === 'forgot'" class="auth-back-button" @click="authMode = 'login'; authMessage = ''">返回登录</button>
      </section>
    </div>

    <div v-if="showReportModal" class="modal-wrap">
      <button class="scrim" @click="showReportModal = false"></button>
      <section class="auth-modal report-modal" role="dialog" aria-modal="true" aria-labelledby="report-title">
        <div class="modal-head">
          <h2 id="report-title">举报内容</h2>
          <button class="icon-button" aria-label="关闭举报窗口" @click="showReportModal = false"><X :size="20" /></button>
        </div>
        <p class="form-message">{{ reportTarget?.title }}</p>
        <select v-model="reportForm.reason" class="composer-title">
          <option>不实或误导</option>
          <option>广告或诈骗</option>
          <option>侵权或盗用</option>
          <option>辱骂或骚扰</option>
          <option>危险或违法内容</option>
          <option>其他</option>
        </select>
        <textarea v-model="reportForm.detail" class="message-textarea" maxlength="1000" placeholder="补充说明（可选）"></textarea>
        <button class="post-button" :disabled="reportSubmitting" @click="submitContentReport">{{ reportSubmitting ? '提交中' : '提交举报' }}</button>
      </section>
    </div>

    <div v-if="showMessageModal" class="modal-wrap">
      <button class="scrim" @click="showMessageModal = false"></button>
      <section class="auth-modal" role="dialog" aria-modal="true" aria-labelledby="message-title">
        <div class="modal-head">
          <h2 id="message-title">发送私信</h2>
          <button class="icon-button" aria-label="关闭私信窗口" @click="showMessageModal = false"><X :size="20" /></button>
        </div>
        <p class="form-message">发送给 {{ messageTarget?.nickname || messageTarget?.username }}</p>
        <textarea v-model="messageBody" class="message-textarea" maxlength="2000" placeholder="输入私信内容"></textarea>
        <button class="post-button" :disabled="!messageBody.trim()" @click="sendMessage">发送</button>
      </section>
    </div>

    <div v-if="showGarageModal" class="modal-wrap">
      <button class="scrim" @click="showGarageModal = false"></button>
      <section class="auth-modal" role="dialog" aria-modal="true" aria-labelledby="garage-title">
        <div class="modal-head">
          <h2 id="garage-title">添加车辆</h2>
          <button class="icon-button" aria-label="关闭添加车辆窗口" @click="showGarageModal = false"><X :size="20" /></button>
        </div>
        <select v-model="garageForm.car_id" class="composer-title">
          <option value="">选择车型（可选）</option>
          <option v-for="car in enrichedCars" :key="car.name" :value="car.id">{{ car.name }}</option>
        </select>
        <input v-model="garageForm.custom_name" maxlength="120" placeholder="车辆名称" />
        <input v-model="garageForm.year" maxlength="20" placeholder="年份" />
        <input v-model="garageForm.color" maxlength="40" placeholder="颜色" />
        <textarea v-model="garageForm.mods" class="message-textarea" maxlength="5000" placeholder="改装清单"></textarea>
        <button class="post-button" :disabled="!garageForm.car_id && !garageForm.custom_name.trim()" @click="submitGarageVehicle">保存车辆</button>
      </section>
    </div>

    <div v-if="showProjectModal" class="modal-wrap">
      <button class="scrim" @click="showProjectModal = false"></button>
      <section class="auth-modal" role="dialog" aria-modal="true" aria-labelledby="project-title">
        <div class="modal-head">
          <h2 id="project-title">添加项目记录</h2>
          <button class="icon-button" aria-label="关闭项目记录窗口" @click="showProjectModal = false"><X :size="20" /></button>
        </div>
        <select v-model="projectForm.vehicle_id" class="composer-title">
          <option value="">关联车辆（可选）</option>
          <option v-for="vehicle in garageVehicles" :key="vehicle.id" :value="vehicle.id">{{ vehicle.name }}</option>
        </select>
        <input v-model="projectForm.title" maxlength="160" placeholder="记录标题" />
        <input v-model="projectForm.stage" maxlength="80" placeholder="阶段，例如 进气 / 避震 / 刹车" />
        <textarea v-model="projectForm.content" class="message-textarea" maxlength="10000" placeholder="记录施工内容、零件、感受或下一步计划"></textarea>
        <button class="post-button" :disabled="!projectForm.title.trim()" @click="submitProjectRecord">保存记录</button>
      </section>
    </div>

    <div v-if="toast" class="toast">{{ toast }}</div>
  </div>
</template>

