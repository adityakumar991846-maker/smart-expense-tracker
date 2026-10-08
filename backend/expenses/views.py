from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from decimal import Decimal
from .models import Expense
from .serializers import ExpenseSerializer, DuplicateCheckSerializer

class ExpensePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class ExpenseListCreateView(APIView):
    """
    GET /api/expenses/ - Filtered, searched, sorted, and paginated expense list.
    POST /api/expenses/ - Create a new expense for the authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Expense.objects.filter(user=request.user).select_related('category')

        # Search filter
        search = request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(merchant_name__icontains=search) |
                Q(description__icontains=search) |
                Q(category_name__icontains=search) |
                Q(upi_transaction_id__icontains=search) |
                Q(google_transaction_id__icontains=search)
            )

        # Category filter
        category_id = request.query_params.get('category')
        if category_id:
            if category_id.isdigit():
                queryset = queryset.filter(category_id=category_id)
            else:
                queryset = queryset.filter(category_name__iexact=category_id)

        # Payment method filter
        payment_method = request.query_params.get('payment_method')
        if payment_method:
            queryset = queryset.filter(payment_method__iexact=payment_method)

        # Source filter (Manual vs Screenshot OCR)
        source = request.query_params.get('source')
        if source:
            queryset = queryset.filter(source__iexact=source)

        # Date range filters
        date_from = request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(expense_date__gte=date_from)

        date_to = request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(expense_date__lte=date_to)

        # Sorting
        sort_by = request.query_params.get('sort_by', 'newest')
        if sort_by == 'oldest':
            queryset = queryset.order_by('expense_date', 'created_at')
        elif sort_by == 'amount_desc':
            queryset = queryset.order_by('-amount', '-expense_date')
        elif sort_by == 'amount_asc':
            queryset = queryset.order_by('amount', '-expense_date')
        else: # default 'newest'
            queryset = queryset.order_by('-expense_date', '-created_at')

        paginator = ExpensePagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = ExpenseSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = ExpenseSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        expense = serializer.save(user=request.user)
        return Response({
            "success": True,
            "message": "Expense created successfully.",
            "expense": ExpenseSerializer(expense, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)

class ExpenseDetailView(APIView):
    """
    GET, PUT, PATCH, DELETE for a specific expense.
    Enforces user isolation (IDOR protection).
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        try:
            return Expense.objects.get(pk=pk, user=user)
        except Expense.DoesNotExist:
            return None

    def get(self, request, pk):
        expense = self.get_object(pk, request.user)
        if not expense:
            return Response(
                {"success": False, "error": "Expense record not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = ExpenseSerializer(expense, context={'request': request})
        return Response({"success": True, "expense": serializer.data}, status=status.HTTP_200_OK)

    def put(self, request, pk):
        expense = self.get_object(pk, request.user)
        if not expense:
            return Response(
                {"success": False, "error": "Expense record not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ExpenseSerializer(expense, data=request.data, partial=True, context={'request': request})
        if not serializer.is_valid():
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        updated_expense = serializer.save()
        return Response({
            "success": True,
            "message": "Expense updated successfully.",
            "expense": ExpenseSerializer(updated_expense, context={'request': request}).data
        }, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        expense = self.get_object(pk, request.user)
        if not expense:
            return Response(
                {"success": False, "error": "Expense record not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        expense.delete()
        return Response({
            "success": True,
            "message": "Expense deleted successfully."
        }, status=status.HTTP_200_OK)

class DuplicateCheckView(APIView):
    """
    POST /api/expenses/check-duplicate/
    Identifies if a proposed transaction already exists for the user.
    Uses UPI ID, Google ID, or composite tuple (amount, merchant, date).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DuplicateCheckSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data
        upi_id = data.get('upi_transaction_id')
        google_id = data.get('google_transaction_id')
        amount = data.get('amount')
        merchant = data.get('merchant_name')
        date = data.get('expense_date')

        query = Q(user=request.user)
        match_conditions = []

        if upi_id:
            match_conditions.append(Q(upi_transaction_id__iexact=upi_id))
        if google_id:
            match_conditions.append(Q(google_transaction_id__iexact=google_id))

        # Composite check
        if amount and merchant and date:
            match_conditions.append(
                Q(amount=Decimal(str(amount)), merchant_name__iexact=merchant, expense_date=date)
            )

        if not match_conditions:
            return Response({
                "is_duplicate": False,
                "message": "Insufficient parameters to check duplicates."
            }, status=status.HTTP_200_OK)

        combined_condition = match_conditions[0]
        for cond in match_conditions[1:]:
            combined_condition |= cond

        existing = Expense.objects.filter(query & combined_condition).first()

        if existing:
            return Response({
                "is_duplicate": True,
                "message": "This transaction may already exist.",
                "existing_expense": ExpenseSerializer(existing, context={'request': request}).data
            }, status=status.HTTP_200_OK)

        return Response({
            "is_duplicate": False,
            "message": "No matching duplicate transaction found."
        }, status=status.HTTP_200_OK)
