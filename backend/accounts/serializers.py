from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User

class UserSerializer(serializers.ModelSerializer):
    """Serializer for user profile representation."""
    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'full_name',
            'display_name',
            'monthly_budget',
            'currency',
            'date_joined',
        ]
        read_only_fields = ['id', 'email', 'date_joined']

class RegisterSerializer(serializers.Serializer):
    """Serializer for user registration with field validation."""
    full_name = serializers.CharField(max_length=150, required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, min_length=6)
    confirm_password = serializers.CharField(write_only=True, min_length=6)

    def validate_email(self, value):
        normalized = value.strip().lower()
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return normalized

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        user = User.objects.create_user(
            email=validated_data['email'],
            full_name=validated_data['full_name'],
            password=password
        )
        return user

class LoginSerializer(serializers.Serializer):
    """Serializer for authenticating users via email & password."""
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        email = attrs.get('email', '').strip().lower()
        password = attrs.get('password')

        user = authenticate(username=email, password=password)
        if not user:
            # Also fallback test with direct check if email/username differs
            try:
                candidate = User.objects.get(email__iexact=email)
                if candidate.check_password(password):
                    user = candidate
            except User.DoesNotExist:
                user = None

        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_active:
            raise serializers.ValidationError("This account has been deactivated.")

        attrs['user'] = user
        return attrs

class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for updating user password."""
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=6)
    confirm_new_password = serializers.CharField(required=True, write_only=True, min_length=6)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_new_password']:
            raise serializers.ValidationError({"confirm_new_password": "New passwords do not match."})
        return attrs

class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating profile details."""
    class Meta:
        model = User
        fields = ['full_name', 'monthly_budget', 'currency']

    def validate_monthly_budget(self, value):
        if value < 0:
            raise serializers.ValidationError("Monthly budget cannot be negative.")
        return value
