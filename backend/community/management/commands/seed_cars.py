from django.core.management.base import BaseCommand

from community.models import Car, CarTrim


CAR_DATA = [
    ("GR86 / BRZ", "gr86-brz", "入门后驱", "轻量化改装热度 98", "/static/assets/cars/gr86-brz-media.jpg"),
    ("A90 Supra", "a90-supra", "性能旗舰", "动力升级热度 96", "/static/assets/cars/a90-supra-media.jpg"),
    ("WRX STI", "wrx-sti", "四驱平台", "拉力风格热度 91", "/static/assets/cars/wrx-sti-media.jpg"),
    ("R32 GT-R", "r32-gtr", "经典项目车", "JDM 经典热度 99", "/static/assets/cars/r32-gtr-media.jpg"),
    ("BMW M2", "bmw-m2", "M 系入门性能", "短轴后驱热度 95", "/static/assets/cars/bmw-m2-media.jpg"),
    ("BMW M3", "bmw-m3", "M 系标杆", "四门性能热度 98", "/static/assets/cars/bmw-m3-media.jpg"),
    ("BMW M4", "bmw-m4", "M 系轿跑", "双门赛道热度 97", "/static/assets/cars/bmw-m4-media.jpg"),
    ("BMW M5", "bmw-m5", "M 系旗舰", "高性能行政热度 92", "/static/assets/cars/bmw-m5-media.jpg"),
    ("Mercedes-AMG A 45", "mercedes-amg-a45", "AMG 钢炮", "钢炮改装热度 94", "/static/assets/cars/mercedes-amg-a45-media.jpg"),
    ("Mercedes-AMG C 63", "mercedes-amg-c63", "AMG 中坚", "C 级性能热度 93", "/static/assets/cars/mercedes-amg-c63-media.jpg"),
    ("Mercedes-AMG GT", "mercedes-amg-gt", "AMG 跑车", "GT 跑车热度 96", "/static/assets/cars/mercedes-amg-gt-media.jpg"),
    ("Audi S3", "audi-s3", "S 系入门", "四驱钢炮热度 93", "/static/assets/cars/audi-s3-media.jpg"),
    ("Audi S4", "audi-s4", "S 系性能", "旅行/轿车热度 90", "/static/assets/cars/audi-s4-media.jpg"),
    ("Audi RS 3", "audi-rs3", "RS 钢炮", "五缸钢炮热度 98", "/static/assets/cars/audi-rs3-media.jpg"),
    ("Audi RS 5", "audi-rs5", "RS 轿跑", "双门四驱热度 94", "/static/assets/cars/audi-rs5-media.jpg"),
    ("Audi RS 6 Avant", "audi-rs6-avant", "RS 旅行车", "性能旅行热度 99", "/static/assets/cars/audi-rs6-avant-media.jpg"),
    ("Audi RS e-tron GT", "audi-rs-e-tron-gt", "RS 纯电", "纯电性能热度 91", "/static/assets/cars/audi-rs-e-tron-gt-media.jpg"),
]

TRIM_DATA = [
    ("GR86 / BRZ", "2.4L 手动基础版", "2.4L H4 自然吸气", "234 马力", "前置后驱", "6MT", "6.5 秒", "汽油"),
    ("A90 Supra", "3.0T 标准型", "3.0T 直列六缸", "387 马力", "前置后驱", "8AT", "4.1 秒", "汽油"),
    ("WRX STI", "2.5T 手动四驱", "2.5T H4 涡轮增压", "300 马力", "全时四驱", "6MT", "5.2 秒", "汽油"),
    ("BMW M2", "M2 Coupe", "3.0T 直列六缸双涡轮", "460 马力", "前置后驱", "8AT", "4.1 秒", "汽油"),
    ("BMW M3", "M3 Competition", "3.0T 直列六缸双涡轮", "510 马力", "前置后驱", "8AT", "3.9 秒", "汽油"),
    ("BMW M3", "M3 xDrive", "3.0T 直列六缸双涡轮", "510 马力", "全时四驱", "8AT", "3.5 秒", "汽油"),
    ("BMW M4", "M4 Coupe", "3.0T 直列六缸双涡轮", "510 马力", "前置后驱", "8AT", "3.9 秒", "汽油"),
    ("BMW M5", "M5 Competition", "4.4T V8 双涡轮", "625 马力", "全时四驱", "8AT", "3.3 秒", "汽油"),
    ("Mercedes-AMG A 45", "A 45 S 4MATIC+", "2.0T 直列四缸涡轮", "421 马力", "全时四驱", "8DCT", "3.9 秒", "汽油"),
    ("Mercedes-AMG C 63", "C 63 S E Performance", "2.0T 插混", "680 马力", "全时四驱", "9AT", "3.4 秒", "插电混动"),
    ("Mercedes-AMG GT", "AMG GT 53", "3.0T 直列六缸", "435 马力", "全时四驱", "9AT", "4.5 秒", "汽油"),
    ("Audi S3", "S3 Limousine", "2.0T 直列四缸", "290 马力", "全时四驱", "7DCT", "4.8 秒", "汽油"),
    ("Audi S4", "S4 Sedan", "3.0T V6", "354 马力", "全时四驱", "8AT", "4.7 秒", "汽油"),
    ("Audi RS 3", "RS 3 Limousine", "2.5T 直列五缸", "400 马力", "全时四驱", "7DCT", "3.8 秒", "汽油"),
    ("Audi RS 5", "RS 5 Coupe", "2.9T V6 双涡轮", "450 马力", "全时四驱", "8AT", "3.9 秒", "汽油"),
    ("Audi RS 6 Avant", "RS 6 Avant", "4.0T V8 双涡轮", "600 马力", "全时四驱", "8AT", "3.6 秒", "汽油"),
    ("Audi RS e-tron GT", "RS e-tron GT", "前后双电机", "646 马力", "全时四驱", "2AT", "3.3 秒", "纯电"),
]


class Command(BaseCommand):
    help = "Seed the public car library without creating fake posts or articles."

    def handle(self, *args, **options):
        cars = {}
        for name, slug, tag, heat, image in CAR_DATA:
            car, _ = Car.objects.update_or_create(
                name=name,
                defaults={"slug": slug, "tag": tag, "heat": heat, "image": image, "state": "published"},
            )
            cars[name] = car

        for car_name, trim_name, engine, horsepower, drivetrain, gearbox, acceleration, fuel in TRIM_DATA:
            CarTrim.objects.update_or_create(
                car=cars[car_name],
                name=trim_name,
                defaults={
                    "engine": engine,
                    "horsepower": horsepower,
                    "drivetrain": drivetrain,
                    "gearbox": gearbox,
                    "acceleration": acceleration,
                    "fuel": fuel,
                    "featured": True,
                    "state": "published",
                },
            )

        self.stdout.write(self.style.SUCCESS(f"车型库已更新：{Car.objects.count()} 个车型，{CarTrim.objects.count()} 个车款。"))
