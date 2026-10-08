from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from .models import Category
from .serializers import CategorySerializer

class CategoryListCreateView(APIView):
    """
    GET /api/categories/ - List system defaults + user's custom categories
    POST /api/categories/ - Create a new custom category for the user
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Auto-seed system defaults if empty
        if not Category.objects.filter(is_default=True).exists():
            Category.seed_defaults()

        categories = Category.objects.filter(
            Q(is_default=True) | Q(user=request.user)
        ).order_by('name')

        serializer = CategorySerializer(categories, many=True, context={'request': request})
        return Response({"success": True, "results": serializer.data}, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = CategorySerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        category = serializer.save(user=request.user, is_default=False)
        return Response(
            {"success": True, "message": "Category created successfully.", "category": CategorySerializer(category).data},
            status=status.HTTP_201_CREATED
        )

class CategoryDetailView(APIView):
    """
    GET, PUT, DELETE for custom categories.
    System categories cannot be edited or deleted.
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        try:
            return Category.objects.get(Q(id=pk) & (Q(is_default=True) | Q(user=user)))
        except Category.DoesNotExist:
            return None

    def get(self, request, pk):
        category = self.get_object(pk, request.user)
        if not category:
            return Response({"success": False, "error": "Category not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"success": True, "category": CategorySerializer(category).data}, status=status.HTTP_200_OK)

    def put(self, request, pk):
        try:
            category = Category.objects.get(id=pk, user=request.user)
        except Category.DoesNotExist:
            return Response(
                {"success": False, "error": "Custom category not found or cannot be modified."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = CategorySerializer(category, data=request.data, partial=True, context={'request': request})
        if not serializer.is_valid():
            return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response({"success": True, "category": serializer.data}, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        try:
            category = Category.objects.get(id=pk, user=request.user)
        except Category.DoesNotExist:
            return Response(
                {"success": False, "error": "Default categories cannot be deleted or category not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        category.delete()
        return Response({"success": True, "message": "Category deleted successfully."}, status=status.HTTP_200_OK)
