import io
from decimal import Decimal
from unittest.mock import patch
from PIL import Image
from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from accounts.models import User
from expenses.models import Expense
from categories.models import Category
from .ocr_service import OcrService

class OcrParserAndServiceTests(TestCase):
    """Unit tests for OCR text parsing and sample Google Pay screenshot extraction."""

    SAMPLE_GPAY_TEXT = """
₹20
To:
Vishesh Chandra S O Umesh Chandra
Completed
16 Jun 2026, 12:20 pm
UPI transaction ID
124819348086
Google transaction ID
CICAgNjFz_DOCa
India Post Payment Bank
"""

    def test_sample_gpay_text_extraction(self):
        """Tests the sample Google Pay transaction extraction specified in PART 20."""
        parsed = OcrService.parse_transaction_data(self.SAMPLE_GPAY_TEXT)

        self.assertEqual(parsed['amount'], 20.00)
        self.assertIn("Vishesh Chandra", parsed['merchant_name'])
        self.assertEqual(parsed['transaction_date'], "2026-06-16")
        self.assertEqual(parsed['transaction_time'], "12:20")
        self.assertEqual(parsed['payment_status'].upper(), "COMPLETED")
        self.assertEqual(parsed['upi_transaction_id'], "124819348086")
        self.assertEqual(parsed['google_transaction_id'], "CICAgNjFz_DOCa")
        self.assertEqual(parsed['bank_name'], "India Post Payment Bank")
        self.assertEqual(parsed['suggested_category'], "Other")

    def test_category_suggestions(self):
        """Tests automatic merchant to category detection."""
        self.assertEqual(OcrService.suggest_category("Swiggy Order #123"), "Food")
        self.assertEqual(OcrService.suggest_category("Zomato Delivery"), "Food")
        self.assertEqual(OcrService.suggest_category("Uber Rides"), "Travel")
        self.assertEqual(OcrService.suggest_category("Amazon Pay Seller"), "Shopping")
        self.assertEqual(OcrService.suggest_category("Airtel Prepaid"), "Bills")
        self.assertEqual(OcrService.suggest_category("Netflix Subscription"), "Entertainment")
        self.assertEqual(OcrService.suggest_category("Apollo Pharmacy"), "Health")
        self.assertEqual(OcrService.suggest_category("Random Merchant"), "Other")

    def test_empty_or_sparse_text_returns_null(self):
        """Ensures missing fields return None rather than inventing data."""
        parsed = OcrService.parse_transaction_data("")
        self.assertIsNone(parsed['amount'])
        self.assertIsNone(parsed['merchant_name'])
        self.assertIsNone(parsed['upi_transaction_id'])


class OcrEndpointTests(TestCase):
    """Tests for POST /api/ocr/analyze/ and POST /api/ocr/confirm/."""

    def setUp(self):
        self.user = User.objects.create_user(email="ocruser@example.com", password="Password123")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.analyze_url = reverse('ocr:ocr-analyze')
        self.confirm_url = reverse('ocr:ocr-confirm')
        self.category = Category.objects.create(name="Food", is_default=True)

    def _generate_test_image(self, format='JPEG', size=(200, 200)):
        img = Image.new('RGB', size, color=(255, 255, 255))
        buffer = io.BytesIO()
        img.save(buffer, format=format)
        buffer.seek(0)
        return buffer.getvalue()

    @patch('ocr.ocr_service.OcrService.extract_text_from_image')
    def test_analyze_endpoint_success(self, mock_extract):
        mock_extract.return_value = (OcrParserAndServiceTests.SAMPLE_GPAY_TEXT, None)

        img_bytes = self._generate_test_image()
        upload_file = SimpleUploadedFile("screenshot.jpg", img_bytes, content_type="image/jpeg")

        response = self.client.post(self.analyze_url, {'image': upload_file}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['extracted_data']['amount'], 20.00)
        self.assertIn("Vishesh Chandra", response.data['extracted_data']['merchant_name'])
        self.assertEqual(response.data['extracted_data']['upi_transaction_id'], "124819348086")
        self.assertFalse(response.data['duplicate_warning']['is_duplicate'])

        # Verify expense was NOT auto-saved
        self.assertEqual(Expense.objects.filter(user=self.user).count(), 0)

    def test_analyze_invalid_file_extension_fails(self):
        upload_file = SimpleUploadedFile("doc.pdf", b"%PDF-1.4...", content_type="application/pdf")
        response = self.client.post(self.analyze_url, {'image': upload_file}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_confirm_expense_creation(self):
        payload = {
            "amount": 20.00,
            "merchant_name": "Vishesh Chandra S O Umesh Chandra",
            "transaction_date": "2026-06-16",
            "transaction_time": "12:20",
            "category_id": self.category.id,
            "payment_method": "Google Pay / UPI",
            "payment_status": "Completed",
            "upi_transaction_id": "124819348086",
            "google_transaction_id": "CICAgNjFz_DOCa",
            "bank_name": "India Post Payment Bank",
            "description": "Scanned payment receipt"
        }

        response = self.client.post(self.confirm_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])

        exp = Expense.objects.get(user=self.user)
        self.assertEqual(exp.amount, Decimal("20.00"))
        self.assertEqual(exp.upi_transaction_id, "124819348086")
        self.assertEqual(exp.google_transaction_id, "CICAgNjFz_DOCa")
        self.assertEqual(exp.source, "Screenshot OCR")

    def test_confirm_duplicate_detection(self):
        # Create existing expense
        Expense.objects.create(
            user=self.user,
            amount=Decimal("20.00"),
            merchant_name="Vishesh Chandra",
            expense_date="2026-06-16",
            upi_transaction_id="124819348086"
        )

        # Attempt to confirm exact same UPI ID
        payload = {
            "amount": 20.00,
            "merchant_name": "Vishesh Chandra",
            "transaction_date": "2026-06-16",
            "upi_transaction_id": "124819348086"
        }
        response = self.client.post(self.confirm_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertTrue(response.data['is_duplicate'])

        # With force_save=true, it should save anyway
        payload['force_save'] = True
        response_force = self.client.post(self.confirm_url, payload, format='json')
        self.assertEqual(response_force.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Expense.objects.filter(user=self.user).count(), 2)
