from rest_framework import serializers
from django.db.models import Q
from .models import Category

class CategorySerializer(serializers.ModelSerializer):
    is_custom = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'icon', 'color', 'is_default', 'is_custom', 'created_at']
        read_only_fields = ['id', 'is_default', 'is_custom', 'created_at']

    def get_is_custom(self, obj):
        return obj.user is not None

    def validate_name(self, value):
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Category name cannot be empty.")

        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None

        # Check duplicate category name for this user or default system categories
        query = Q(name__iexact=name) & (Q(user=None) | Q(user=user))
        instance_id = self.instance.id if self.instance else None
        if instance_id:
            query = query & ~Q(id=instance_id)

        if Category.objects.filter(query).exists():
            raise serializers.ValidationError(f"Category '{name}' already exists.")
        return name
