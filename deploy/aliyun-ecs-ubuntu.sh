#!/usr/bin/env bash
set -euo pipefail

APP_NAME="tunerhub"
APP_DIR="/opt/tunerhub"
REPO_URL="https://github.com/ywj378581221-png/tuner-hub.git"
SERVER_IP="${SERVER_IP:-8.210.35.92}"
DOMAIN="${DOMAIN:-}"
DB_NAME="tunerhub"
DB_USER="tunerhub"
DB_PASSWORD="$(openssl rand -hex 24 | tr -d '\n')"
SECRET_KEY="$(openssl rand -base64 48 | tr -d '\n')"

if [ "$(id -u)" -ne 0 ]; then
  echo "请用 root 用户执行这个脚本。"
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

echo "1/8 安装系统依赖..."
apt-get update
apt-get install -y software-properties-common curl git nginx postgresql postgresql-contrib openssl ca-certificates sudo

if ! command -v python3.12 >/dev/null 2>&1; then
  add-apt-repository -y ppa:deadsnakes/ppa
  apt-get update
  apt-get install -y python3.12 python3.12-venv python3.12-dev
fi

if ! command -v node >/dev/null 2>&1 || [ "$(node -v | sed 's/v//' | cut -d. -f1)" -lt 20 ]; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -y nodejs
fi

corepack enable
corepack prepare pnpm@latest --activate

echo "2/8 准备数据库..."
systemctl enable --now postgresql
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1 || sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 || sudo -u postgres createdb -O "${DB_USER}" "${DB_NAME}"

echo "3/8 拉取网站代码..."
if [ -d "${APP_DIR}/.git" ]; then
  git -C "${APP_DIR}" fetch origin main
  git -C "${APP_DIR}" reset --hard origin/main
else
  rm -rf "${APP_DIR}"
  git clone "${REPO_URL}" "${APP_DIR}"
fi

echo "4/8 安装网站依赖并构建前台..."
cd "${APP_DIR}"
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pnpm install --frozen-lockfile
pnpm build

echo "5/8 写入服务器配置..."
ALLOWED_HOSTS="${SERVER_IP},127.0.0.1,localhost"
CSRF_ORIGINS="http://${SERVER_IP}"
if [ -n "${DOMAIN}" ]; then
  ALLOWED_HOSTS="${DOMAIN},${ALLOWED_HOSTS}"
  CSRF_ORIGINS="https://${DOMAIN},http://${DOMAIN},${CSRF_ORIGINS}"
fi

cat > /etc/tunerhub.env <<EOF
TUNERHUB_SECRET_KEY=${SECRET_KEY}
TUNERHUB_DEBUG=0
TUNERHUB_ALLOWED_HOSTS=${ALLOWED_HOSTS}
TUNERHUB_CSRF_TRUSTED_ORIGINS=${CSRF_ORIGINS}
TUNERHUB_SECURE_SSL_REDIRECT=0
TUNERHUB_HSTS_SECONDS=0
TUNERHUB_SESSION_COOKIE_SECURE=0
TUNERHUB_CSRF_COOKIE_SECURE=0
DATABASE_URL=postgres://${DB_USER}:${DB_PASSWORD}@127.0.0.1:5432/${DB_NAME}
EOF
chmod 600 /etc/tunerhub.env

echo "6/8 初始化数据库和静态文件..."
set -a
. /etc/tunerhub.env
set +a
cd "${APP_DIR}/backend"
python manage.py migrate
python manage.py collectstatic --noinput
mkdir -p "${APP_DIR}/backend/media"

echo "7/8 创建网站服务..."
cat > /etc/systemd/system/tunerhub.service <<EOF
[Unit]
Description=Tuner Hub Django service
After=network.target postgresql.service

[Service]
Type=simple
WorkingDirectory=${APP_DIR}/backend
EnvironmentFile=/etc/tunerhub.env
ExecStart=${APP_DIR}/.venv/bin/gunicorn tunerhub.wsgi:application --bind 127.0.0.1:8000 --workers 3
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/nginx/sites-available/tunerhub <<EOF
server {
    listen 80;
    server_name ${SERVER_IP} ${DOMAIN};

    client_max_body_size 20M;

    location /static/ {
        alias ${APP_DIR}/backend/staticfiles/;
        expires 30d;
        add_header Cache-Control "public";
    }

    location /media/ {
        alias ${APP_DIR}/backend/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

ln -sf /etc/nginx/sites-available/tunerhub /etc/nginx/sites-enabled/tunerhub
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl daemon-reload
systemctl enable --now tunerhub
systemctl restart tunerhub
systemctl restart nginx

echo "8/8 创建后台管理员..."
echo "请输入后台管理员 THhub 的密码；输入时不会显示字符。"
cd "${APP_DIR}/backend"
python manage.py shell <<'PY'
from getpass import getpass
from django.contrib.auth import get_user_model
from community.models import UserProfile

User = get_user_model()
password = getpass("后台管理员密码: ")
user, created = User.objects.get_or_create(
    username="THhub",
    defaults={"email": "378581221@qq.com", "is_staff": True, "is_superuser": True},
)
user.email = "378581221@qq.com"
user.is_staff = True
user.is_superuser = True
user.set_password(password)
user.save()
profile, _ = UserProfile.objects.get_or_create(user=user)
profile.nickname = "Tuner hub"
profile.save()
print("后台管理员已创建/更新。")
PY

echo
echo "部署完成："
echo "网站地址：http://${SERVER_IP}/"
echo "后台地址：http://${SERVER_IP}/admin/"
echo "后台账号：THhub"
