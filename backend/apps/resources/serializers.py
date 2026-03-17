from rest_framework import serializers
from .models import ResourceCategory, Resource, SharedDocument


class ResourceCategorySerializer(serializers.ModelSerializer):
    resource_count = serializers.SerializerMethodField()
    children_count = serializers.SerializerMethodField()

    def get_resource_count(self, obj):
        return obj.resources.filter(is_active=True).count()

    def get_children_count(self, obj):
        return obj.children.count()

    class Meta:
        model = ResourceCategory
        fields = ['id', 'name', 'description', 'order', 'parent', 'resource_count', 'children_count']


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
