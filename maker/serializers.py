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
        read_only_fields = ("created_at",) # created_at 설정 추가

    # type 검증 로직
    def validate(self, data):
        checks = {"knot": "knot", "tassel": "tassel", "decoration": "decoration"}
        for field, expected_type in checks.items():
            component = data.get(field)
            if component and component.type != expected_type:
                raise serializers.ValidationError(
                    {field: f"'{field}' 자리에는 type='{expected_type}'인 컴포넌트만 넣을 수 있습니다."}
                )
        return data


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"