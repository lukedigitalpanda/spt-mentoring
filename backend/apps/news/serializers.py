from rest_framework import serializers
from .models import NewsItem, PromotionalBanner


class NewsItemSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.full_name', read_only=True)

    class Meta:
        model = NewsItem
        fields = '__all__'
        read_only_fields = ['author', 'created_at', 'updated_at']


class PromotionalBannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromotionalBanner
        fields = '__all__'
