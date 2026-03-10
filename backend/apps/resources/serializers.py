from rest_framework import serializers
from .models import ResourceCategory, Resource, SharedDocument


class ResourceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceCategory
        fields = '__all__'


class ResourceSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    uploaded_by_name = serializers.CharField(source='uploaded_by.full_name', read_only=True)

    class Meta:
        model = Resource
        fields = '__all__'
        read_only_fields = ['uploaded_by', 'download_count', 'created_at', 'updated_at']


class SharedDocumentSerializer(serializers.ModelSerializer):
    shared_by_name = serializers.CharField(source='shared_by.full_name', read_only=True)
    shared_with_name = serializers.CharField(source='shared_with.full_name', read_only=True)

    class Meta:
        model = SharedDocument
        fields = '__all__'
        read_only_fields = ['shared_by', 'shared_at']
