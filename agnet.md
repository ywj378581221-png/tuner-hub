# Tuner Hub 项目说明

## 项目概览

Tuner Hub，缩写为 TH，是一个面向改装车玩家的分享社区网站。

当前产品方向是：以中文为默认语言，参考懂车帝一类内容平台的布局方式，但内容核心聚焦于改装车文化、项目车进度、车友会、认证改装店、线下聚会和二手改装件关注列表。

项目目前分为两部分：

- 前台：Vue 3 + Vite
- 后台：Django + SQLite

前台负责用户可见的网站页面和互动体验。Django 后台目前主要用于后台管理系统，后续可以继续扩展数据库、接口和内容管理能力。

## 主项目路径

优先使用 D 盘项目：

```text
D:\Tuner Hub\tuner-hub
```

如果后续继续开发，默认都应该在这个目录里操作。

## 前台说明

前台已经切换为 Vue 3 + Vite。

重要文件：

```text
src/main.js
src/App.vue
src/styles.css
vite.config.js
package.json
public/assets/
dist/
```

当前前台功能：

- 默认中文显示
- 中英文切换
- 发帖弹窗
- 动态筛选
- 收藏/取消收藏
- 帖子详情抽屉
- 精选车友会展示
- 我的车库展示
- 右侧车友会、聚会、店家、二手件模块

常用命令：

```powershell
pnpm dev
pnpm build
pnpm preview
```

当前前台访问地址：

```text
http://127.0.0.1:5174/
```

## 后台说明

后台是 Django 项目。

重要文件：

```text
backend/manage.py
backend/tunerhub/settings.py
backend/community/
backend/db.sqlite3
requirements.txt
```

Python 虚拟环境：

```text
.venv
```

Django 后台已经安装 SimpleUI，并且后台默认语言设置为中文。

常用命令：

```powershell
.\.venv\Scripts\python.exe backend\manage.py check
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
```

后台管理地址：

```text
http://127.0.0.1:8000/admin/
```

## 开发注意事项

- 前台网站继续使用 Vue，不再使用 Django 原生模板作为前台。
- 用户可见内容默认使用中文。
- 修改页面时不要破坏现有互动功能。
- 优先编辑 D 盘主项目。
- 网站风格应保持内容平台和改装车社区的方向，不做成单纯的宣传落地页。
- Django 继续用于后台管理、数据库和未来接口能力。
- 后续如果要前后端联动，建议先在 Django 增加 API 接口，再让 Vue 调用接口。

## 验证清单

前台修改完成前，建议确认：

- `pnpm build` 可以成功。
- `http://127.0.0.1:5174/` 可以正常打开。
- 中文显示正常，没有乱码。
- 中英文切换正常。
- 发帖弹窗可以打开。
- 动态筛选、收藏、详情抽屉等互动仍然可用。

后台修改完成前，建议确认：

- Django 系统检查通过。
- 后台管理页面可以打开。
- SimpleUI 正常加载。
- 后台语言仍然是中文。
