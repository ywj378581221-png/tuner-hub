# Tuner Hub

Tuner Hub 是一个改装车分享社区，包含 Vue 前台、Django 后台、用户系统、发帖、车型库、车友圈、关注、私信、等级、车库和项目车记录。

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/ywj378581221-png/tuner-hub)

## 上线说明

点击上方按钮后，Render 会根据 `render.yaml` 自动创建网站服务和数据库。

部署完成后，如果 Render 分配的网址不是 `https://tuner-hub.onrender.com`，请在 Render 的环境变量里更新：

- `TUNERHUB_ALLOWED_HOSTS`
- `TUNERHUB_CSRF_TRUSTED_ORIGINS`

## 密码重置邮件

生产服务器需要配置 SMTP 环境变量。使用 QQ 邮箱时，密码必须填写邮箱设置中生成的 SMTP 授权码，不能填写 QQ 登录密码。

```text
TUNERHUB_PUBLIC_URL=http://8.210.35.92
TUNERHUB_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
TUNERHUB_EMAIL_HOST=smtp.qq.com
TUNERHUB_EMAIL_PORT=465
TUNERHUB_EMAIL_HOST_USER=你的发件邮箱@qq.com
TUNERHUB_EMAIL_HOST_PASSWORD=你的SMTP授权码
TUNERHUB_EMAIL_USE_SSL=1
TUNERHUB_EMAIL_USE_TLS=0
TUNERHUB_DEFAULT_FROM_EMAIL=你的发件邮箱@qq.com
```
