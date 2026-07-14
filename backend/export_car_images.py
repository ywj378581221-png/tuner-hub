import os
import shutil
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tunerhub.settings")

import django
from django.conf import settings

django.setup()

from community.models import Car


PROJECT_ROOT = Path(settings.BASE_DIR).parent
OUT_DIR = PROJECT_ROOT / "车型库图片"
BAD_CHARS = '<>:"/\\|?*'


def safe_name(value):
    cleaned = "".join("-" if char in BAD_CHARS else char for char in value).strip()
    return " ".join(cleaned.split()) or "car"


def resolve_image(car):
    if car.image_upload:
        return Path(car.image_upload.path)
    image = car.image or ""
    if image.startswith("/static/assets/"):
        return Path(settings.BASE_DIR) / image.replace("/static/", "static/")
    if image.startswith("/assets/"):
        return PROJECT_ROOT / "public" / image.lstrip("/")
    if image.startswith("static/assets/"):
        return Path(settings.BASE_DIR) / image
    return None


def main():
    OUT_DIR.mkdir(exist_ok=True)
    for child in OUT_DIR.iterdir():
        if child.is_file():
            child.unlink()

    lines = []
    for car in Car.objects.order_by("name"):
        source = resolve_image(car)
        if source and source.exists():
            target = OUT_DIR / f"{safe_name(car.name)}{source.suffix or '.jpg'}"
            shutil.copyfile(source, target)
            lines.append(f"{car.name}\t{target.name}\t{source}")
        else:
            lines.append(f"{car.name}\tMISSING\t{source or 'no image'}")

    (OUT_DIR / "图片清单.txt").write_text("\n".join(lines), encoding="utf-8")
    print(OUT_DIR)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
