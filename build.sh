#!/usr/bin/env bash
set -o errexit

python -m pip install --upgrade pip
pip install -r requirements.txt
corepack enable
corepack prepare pnpm@latest --activate
pnpm install --frozen-lockfile
pnpm build
cd backend
python manage.py migrate
python manage.py collectstatic --noinput
