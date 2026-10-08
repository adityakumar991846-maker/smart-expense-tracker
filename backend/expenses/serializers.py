from rest_framework import serializers
from decimal import Decimal
from .models import Expense
from categories.models import Category
from categories.serializers import CategorySerializer

class ExpenseSerializer(serializers.ModelSerializer):
    category_detail = CategorySerializer(source='category', read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        required=False,
        allow_null=True
    )

    class Meta:
        model = Expense
        fields = [
            'id',
            'amount',
            'merchant_name',
            'category',
            'category_id',
            'category_name',
            'category_detail',
            'expense_date',
            'expense_time',
            'payment_method',
            'description',
            'source',
            'status',
            'upi_transaction_id',
            'google_transaction_id',
            'bank_name',
            'upi_id',
            'receipt_image',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_amount(self, value):
        if value is None or Decimal(str(value)) <= Decimal('0'):
            raise serializers.ValidationError("Expense amount must be greater than zero.")
        return value

    def validate_merchant_name(self, value):
        val = value.strip()
        if not val:
            raise serializers.ValidationError("Merchant or product name cannot be blank.")
        return val

    def validate(self, attrs):
        request = self.context.get('request')
        user = request.user if request else None

        # Ensure selected category belongs to this user or is a system default
        category = attrs.get('category')
        if category and category.user is not None and category.user != user:
            raise serializers.ValidationError({"category": "Invalid category selection."})

        return attrs

    def create(self, validated_data):
        # Category name sync
        category = validated_data.get('category')
        if category:
            validated_data['category_name'] = category.name
        elif not validated_data.get('category_name'):
            validated_data['category_name'] = 'Other'
        return super().create(validated_data)

    def update(self, instance, validated_data):
        category = validated_data.get('category', instance.category)
        if category:
            validated_data['category_name'] = category.name
        return super().update(instance, validated_data)

class DuplicateCheckSerializer(serializers.Serializer):
    """Checks for existing potential duplicate expenses."""
    upi_transaction_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    google_transaction_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    merchant_name = serializers.CharField(required=False, allow_blank=True)
    expense_date = serializers.DateField(required=False)
    expense_time = serializers.TimeField(required=False, allow_null=True)
