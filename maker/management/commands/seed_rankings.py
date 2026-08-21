from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from maker.models import Item

User = get_user_model()

# (닉네임, 매듭id, 장식id, 술개수, 색상, 제목, 설명, 저장횟수)
SEED_DATA = [
    ("ARTISAN_LEE", 4, 9, 1, "#17216E", "미드나잇 앰버 앙상블", "호박 펜던트가 돋보이는 네이비 비단의 노리개.", 3),
    ("SEOUL_CRAFTS", 3, 11, 1, "#FFC95F", "미니멀리스트 나비", "순백의 나비를 돋보이게 하는 골드 노리개", 2),
    ("HERITAGE_WEAVER", 2, 7, 1, "#F37E7E", "핑크러버 노리개", "무궁화가 돋보이는 핑크 노리개.", 1),
]


class Command(BaseCommand):
    help = "인기 조합 랭킹 데모용 시드 데이터를 생성합니다."

    def handle(self, *args, **options):
        for nickname, knot_id, decoration_id, tassel_count, color, title, desc, times in SEED_DATA:
            user, _ = User.objects.get_or_create(
                email=f"{nickname.lower()}@demo.com",
                defaults={"nickname": nickname, "is_active": True},
            )
            if not user.has_usable_password():
                user.set_password("demo1234!")
                user.save()

            for _ in range(times):
                Item.objects.create(
                    user=user,
                    wish_keyword="데모",
                    symbol_reason="데모용 시드 데이터",
                    knot_id=knot_id,
                    decoration_id=decoration_id,
                    tassel_count=tassel_count,
                    color=color,
                    title=title,
                    description=desc,
                )
            self.stdout.write(self.style.SUCCESS(f"{nickname}: {title} x{times}개 저장 완료"))

        self.stdout.write(self.style.SUCCESS("시드 데이터 생성 완료!"))