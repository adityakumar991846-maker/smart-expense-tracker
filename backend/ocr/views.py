from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Q
from decimal import Decimal
from expenses.models import Expense
from expenses.serializers import ExpenseSerializer
from categories.models import Category
from .ocr_service import OcrService

class OcrAnalyzeView(APIView):
    """
    POST /api/ocr/analyze/
    Analyzes an uploaded Google Pay / UPI payment screenshot using local OCR.
    Extracts transaction fields, suggests category, and checks for potential duplicates.
    DOES NOT automatically save the expense.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        image_file = request.FILES.get('image') or request.FILES.get('screenshot')
        if not image_file:
            return Response(
                {"success": False, "error": "Please provide an image file to analyze."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate file
        is_valid, validation_error = OcrService.validate_image_file(image_file)
        if not is_valid:
            return Response(
                {"success": False, "error": validation_error},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Execute OCR
        raw_text, ocr_error = OcrService.extract_text_from_image(image_file)
        if ocr_error:
            return Response(
                {"success": False, "error": ocr_error},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR if "installed" in ocr_error else status.HTTP_422_UNPROCESSABLE_ENTITY
            )

        # Parse text into structured fields
        extracted = OcrService.parse_transaction_data(raw_text)

        # Look up category ID matching the suggested category
        suggested_category_name = extracted.get('suggested_category', 'Other')
        category_obj = Category.objects.filter(
            Q(user=request.user) | Q(is_default=True),
            name__iexact=suggested_category_name
        ).first()

        category_id = category_obj.id if category_obj else None

        # Check for potential duplicates
        duplicate_info = self._check_duplicate(request.user, extracted)

        return Response({
            "success": True,
            "message": "Payment screenshot analyzed successfully.",
            "extracted_data": {
                **extracted,
                "category_id": category_id,
            },
            "duplicate_warning": duplicate_info,
        }, status=status.HTTP_200_OK)

    def _check_duplicate(self, user, data):
        upi_id = data.get('upi_transaction_id')
        google_id = data.get('google_transaction_id')
        amount = data.get('amount')
        merchant = data.get('merchant_name')
        date = data.get('transaction_date')

        match_conditions = []
        if upi_id:
            match_conditions.append(Q(upi_transaction_id__iexact=upi_id))
        if google_id:
            match_conditions.append(Q(google_transaction_id__iexact=google_id))

        if amount and merchant and date:
            match_conditions.append(
                Q(amount=Decimal(str(amount)), merchant_name__iexact=merchant, expense_date=date)
            )

        if not match_conditions:
            return {"is_duplicate": False, "message": "No matching duplicate transaction found."}

        combined = match_conditions[0]
        for cond in match_conditions[1:]:
            combined |= cond

        existing = Expense.objects.filter(Q(user=user) & combined).first()
        if existing:
            return {
                "is_duplicate": True,
                "message": "This transaction may already exist.",
                "existing_id": existing.id,
                "existing_amount": float(existing.amount),
                "existing_merchant": existing.merchant_name,
                "existing_date": str(existing.expense_date),
            }

        return {"is_duplicate": False, "message": "No matching duplicate transaction found."}


class OcrConfirmView(APIView):
    """
    POST /api/ocr/confirm/
    Receives user-confirmed (and possibly edited) OCR transaction data and saves it.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def post(self, request):
        data = request.data.copy()

        # Validate amount
        amount_raw = data.get('amount')
        if amount_raw is None or str(amount_raw).strip() == '':
            return Response(
                {"success": False, "error": "We couldn't detect the payment amount. Please enter it manually."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            amount = Decimal(str(amount_raw))
            if amount <= Decimal('0'):
                return Response(
                    {"success": False, "error": "Amount must be greater than zero."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception:
            return Response(
                {"success": False, "error": "Invalid amount format."},
                status=status.HTTP_400_BAD_REQUEST
            )

        merchant = (data.get('merchant_name') or '').strip()
        if not merchant:
            return Response(
                {"success": False, "error": "Merchant or receiver name cannot be empty."},
                status=status.HTTP_400_BAD_REQUEST
            )

        expense_date = data.get('transaction_date') or data.get('expense_date')
        if not expense_date:
            return Response(
                {"success": False, "error": "Transaction date is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Duplicate check unless force_save is True
        force_save = str(data.get('force_save', 'false')).lower() in ('true', '1')
        if not force_save:
            upi_id = data.get('upi_transaction_id')
            google_id = data.get('google_transaction_id')

            conditions = []
            if upi_id:
                conditions.append(Q(upi_transaction_id__iexact=upi_id))
            if google_id:
                conditions.append(Q(google_transaction_id__iexact=google_id))
            if merchant and expense_date:
                conditions.append(Q(amount=amount, merchant_name__iexact=merchant, expense_date=expense_date))

            if conditions:
                comb = conditions[0]
                for c in conditions[1:]:
                    comb |= c
                if Expense.objects.filter(Q(user=request.user) & comb).exists():
                    return Response({
                        "success": False,
                        "is_duplicate": True,
                        "error": "This transaction may already exist.",
                        "message": "This transaction may already exist. You can choose to Save Anyway."
                    }, status=status.HTTP_409_CONFLICT)

        # Resolve category
        category = None
        category_name = data.get('category_name') or 'Other'
        category_id = data.get('category_id') or data.get('category')

        if category_id:
            category = Category.objects.filter(
                Q(id=category_id) & (Q(user=request.user) | Q(is_default=True))
            ).first()
            if category:
                category_name = category.name
        elif category_name:
            cat_obj = Category.objects.filter(
                Q(name__iexact=category_name) & (Q(user=request.user) | Q(is_default=True))
            ).first()
            if cat_obj:
                category = cat_obj
                category_name = cat_obj.name

        # Create expense
        expense = Expense.objects.create(
            user=request.user,
            amount=amount,
            merchant_name=merchant,
            category=category,
            category_name=category_name,
            expense_date=expense_date,
            expense_time=data.get('transaction_time') or data.get('expense_time'),
            payment_method=data.get('payment_method') or 'Google Pay / UPI',
            description=data.get('description', ''),
            source='Screenshot OCR',
            status=data.get('payment_status') or 'Completed',
            upi_transaction_id=data.get('upi_transaction_id'),
            google_transaction_id=data.get('google_transaction_id'),
            bank_name=data.get('bank_name'),
            upi_id=data.get('upi_id'),
        )

        return Response({
            "success": True,
            "message": "Expense added successfully from payment screenshot.",
            "expense": ExpenseSerializer(expense, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)
