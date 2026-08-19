from rest_framework import serializers

from .models import Component, Item, Product, Season


# models.py에 정의한 필드 모두 읽어오기
class SeasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Season
        fields = "__all__" # Season의 모든 컬럼 읽어오기


class ComponentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Component
        fields = "__all__"


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = "__all__"
        read_only_fields = ("created_at", "description")

    # type 검증 로직
    def validate(self, data):
        checks = {"knot": "knot", "decoration": "decoration"}  # tassel 빠짐
        for field, expected_type in checks.items():
            component = data.get(field)
            if component and component.type != expected_type:
                raise serializers.ValidationError(
                    {field: f"'{field}' 자리에는 type='{expected_type}'인 컴포넌트만 넣을 수 있습니다."}
                )

        # 완성 조건: 소망/AI추천/색상/술개수/제목까지 다 채워져야 저장 가능
        if not data.get("symbol_reason"):
            raise serializers.ValidationError({"symbol_reason": "AI 추천을 받아야 저장할 수 있습니다."})
        if not data.get("color"):
            raise serializers.ValidationError({"color": "색상을 선택해야 저장할 수 있습니다."})
        if not data.get("tassel_count"):
            raise serializers.ValidationError({"tassel_count": "술 개수를 선택해야 저장할 수 있습니다."})
        if not data.get("title"):
            raise serializers.ValidationError({"title": "제목을 입력해야 저장할 수 있습니다."})

        return data


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"