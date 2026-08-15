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


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"