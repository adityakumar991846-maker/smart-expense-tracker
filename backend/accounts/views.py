from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    UserSerializer,
    UserProfileUpdateSerializer,
    ChangePasswordSerializer,
)

class RegisterView(APIView):
    """
    POST /api/auth/register/
    Registers a new user and returns authentication token + user info.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            "success": True,
            "message": "Registration successful.",
            "token": token.key,
            "user": UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)

class LoginView(APIView):
    """
    POST /api/auth/login/
    Logs in user with email and password, returning authentication token.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = serializer.validated_data['user']
        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            "success": True,
            "message": "Login successful.",
            "token": token.key,
            "user": UserSerializer(user).data
        }, status=status.HTTP_200_OK)

class LogoutView(APIView):
    """
    POST /api/auth/logout/
    Revokes the current authentication token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # Delete token if exists
            Token.objects.filter(user=request.user).delete()
        except Exception:
            pass

        return Response({
            "success": True,
            "message": "Successfully logged out."
        }, status=status.HTTP_200_OK)

class UserProfileView(APIView):
    """
    GET /api/auth/profile/
    PUT /api/auth/profile/
    Retrieve and update user profile & budget settings.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response({"success": True, "user": serializer.data}, status=status.HTTP_200_OK)

    def put(self, request):
        serializer = UserProfileUpdateSerializer(request.user, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer.save()
        return Response({
            "success": True,
            "message": "Profile updated successfully.",
            "user": UserSerializer(request.user).data
        }, status=status.HTTP_200_OK)

class ChangePasswordView(APIView):
    """
    POST /api/auth/change-password/
    Allows authenticated users to change their password safely.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {"success": False, "errors": {"old_password": ["Incorrect existing password."]}},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(serializer.validated_data['new_password'])
        user.save()

        # Refresh token to maintain active session
        Token.objects.filter(user=user).delete()
        new_token = Token.objects.create(user=user)

        return Response({
            "success": True,
            "message": "Password changed successfully.",
            "token": new_token.key
        }, status=status.HTTP_200_OK)
