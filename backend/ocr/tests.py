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
To:
Vishesh Chandra S O Umesh Chandra
Bank account ending 7623
₹ 20
Completed
16 Jun 2026, 12:20 pm
UPI transaction ID
124819348086
Google transaction ID
CICAgNjFz_DOCA
India Post Payment Bank
"""

    VISHESH_GPAY_OCR_TEXT = """
To Vishesh Chandra S o Umesh Chandra
© Completed
16 Jun 2026, 12:20pm
==———= India Post Payment Bank
————- 7623.
UPI transaction ID
124819348086
To: Vishesh Chandra S o Umesh Chandra
From: ADITYA MADDHESHIYA (India Post Payment Bank)
Google transaction ID
CICAgNjFz_DOCA
G Pay
"""

    PAWAN_MOBILE_OCR_TEXT = """
To PAWAN MOBILE
Completed
10 Oct 2026, 9:00 pm
India Post Payment Bank
7623.
�Q� Payment of 30 completed
Receiver's bank has confirmed deposit
of money to PAWAN MOBILE's bank
account
UPI transaction ID
131070273113
To: PAWAN MOBILE
[redacted UPI address]
From: [redacted payer details]
Google transaction ID
CICAgLimyYPWIA
G Pay
"""

    def test_sample_gpay_text_extraction(self):
        """Tests the sample Google Pay transaction extraction specified in PART 20."""
        parsed = OcrService.parse_transaction_data(self.SAMPLE_GPAY_TEXT)

        self.assertEqual(Decimal(str(parsed['amount'])), Decimal("20.00"))
        self.assertIn("Vishesh Chandra", parsed['merchant_name'])
        self.assertEqual(parsed['transaction_date'], "2026-06-16")
        self.assertEqual(parsed['transaction_time'], "12:20")
        self.assertEqual(parsed['payment_status'].upper(), "COMPLETED")
        self.assertEqual(parsed['upi_transaction_id'], "124819348086")
        self.assertEqual(parsed['google_transaction_id'], "CICAgNjFz_DOCA")
        self.assertEqual(parsed['bank_name'], "India Post Payment Bank")
        self.assertEqual(parsed['suggested_category'], "Other")

    @patch('ocr.ocr_service.pytesseract.image_to_string')
    def test_vishesh_receipt_recovers_amount_missed_by_full_page_ocr(self, mock_ocr):
        mock_ocr.side_effect = [self.VISHESH_GPAY_OCR_TEXT, "=20"]
        image_buffer = io.BytesIO()
        Image.new('RGB', (540, 1324), color=(255, 255, 255)).save(
            image_buffer,
            format='JPEG',
        )
        upload = SimpleUploadedFile(
            "vishesh-receipt.jpg",
            image_buffer.getvalue(),
            content_type="image/jpeg",
        )

        text, error = OcrService.extract_text_from_image(upload)

        self.assertIsNone(error)
        self.assertIn("Payment amount: 20", text)
        parsed = OcrService.parse_transaction_data(text)
        self.assertEqual(Decimal(str(parsed['amount'])), Decimal("20.00"))
        self.assertNotEqual(parsed['amount'], 7623.00)
        self.assertEqual(parsed['upi_transaction_id'], "124819348086")
        self.assertEqual(mock_ocr.call_count, 2)

    def test_pawan_mobile_receipt_extracts_payment_of_amount(self):
        parsed = OcrService.parse_transaction_data(self.PAWAN_MOBILE_OCR_TEXT)

        self.assertEqual(Decimal(str(parsed['amount'])), Decimal("30.00"))
        self.assertEqual(parsed['merchant_name'], "PAWAN MOBILE")
        self.assertEqual(parsed['transaction_date'], "2026-10-10")
        self.assertEqual(parsed['transaction_time'], "21:00")
        self.assertEqual(parsed['bank_name'], "India Post Payment Bank")
        self.assertEqual(parsed['upi_transaction_id'], "131070273113")
        self.assertEqual(parsed['google_transaction_id'], "CICAgLimyYPWIA")

    def test_account_suffix_is_not_guessed_as_amount(self):
        """Unlabelled numbers in receipt metadata must not become expense amounts."""
        text = """
Vishesh Chandra S o Umesh Chandra
Completed
16 Jun 2026
India Post Payment Bank
Bank account ending
7623
UPI transaction ID
124819348086
Google transaction ID
CICAgNjFz_DOCA
20
"""
        parsed = OcrService.parse_transaction_data(text)

        self.assertIsNone(parsed['amount'])

    def test_payment_label_extracts_amount_after_account_and_transaction_ids(self):
        """A labelled amount remains recognizable after account and transaction IDs."""
        text = """
Vishesh Chandra S o Umesh Chandra
Completed
16 Jun 2026
India Post Payment Bank
Bank account ending
7623
UPI transaction ID
124819348086
Google transaction ID
CICAgNjFz_DOCA
Payment amount
20
"""
        parsed = OcrService.parse_transaction_data(text)

        self.assertEqual(Decimal(str(parsed['amount'])), Decimal("20.00"))
        self.assertEqual(parsed['upi_transaction_id'], "124819348086")
        self.assertEqual(parsed['google_transaction_id'], "CICAgNjFz_DOCA")

    def test_currency_and_label_amount_formats(self):
        """Currency markers, line breaks, and comma grouping survive OCR formatting."""
        cases = (
            ("₹ 20", Decimal("20.00")),
            ("Amount\n₹\n1,234.50", Decimal("1234.50")),
            ("Rs.\n1,234.50", Decimal("1234.50")),
            ("INR 12,345", Decimal("12345.00")),
            ("Paid:\n75.50", Decimal("75.50")),
            ("₹1,23,456.78", Decimal("123456.78")),
        )

        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(OcrService._extract_amount(text, text.splitlines()), expected)

    def test_transaction_identifiers_and_dates_are_not_amounts(self):
        text = """
16 Jun 2026
UPI transaction ID
124819348086
Google transaction ID
CICAgNjFz_DOCA
"""

        self.assertIsNone(OcrService._extract_amount(text, text.splitlines()))

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

    @patch('ocr.ocr_service.OcrService.extract_text_from_image')
    def test_pawan_mobile_analyze_response_contains_amount(self, mock_extract):
        mock_extract.return_value = (
            OcrParserAndServiceTests.PAWAN_MOBILE_OCR_TEXT,
            None,
        )
        upload_file = SimpleUploadedFile(
            "pawan-receipt.jpg",
            self._generate_test_image(),
            content_type="image/jpeg",
        )

        response = self.client.post(
            self.analyze_url,
            {'image': upload_file},
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Decimal(str(response.data['extracted_data']['amount'])),
            Decimal("30.00"),
        )
        self.assertEqual(
            response.data['extracted_data']['merchant_name'],
            "PAWAN MOBILE",
        )
        self.assertEqual(
            response.data['extracted_data']['upi_transaction_id'],
            "131070273113",
        )
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

    @patch('ocr.ocr_service.OcrService.extract_text_from_image')
    def test_analyzed_receipt_amount_is_saved_unchanged(self, mock_extract):
        mock_extract.return_value = (OcrParserAndServiceTests.SAMPLE_GPAY_TEXT, None)
        upload_file = SimpleUploadedFile(
            "screenshot.jpg",
            self._generate_test_image(),
            content_type="image/jpeg",
        )

        analysis = self.client.post(
            self.analyze_url,
            {'image': upload_file},
            format='multipart',
        )
        self.assertEqual(analysis.status_code, status.HTTP_200_OK)
        extracted = analysis.data['extracted_data']
        self.assertEqual(Decimal(str(extracted['amount'])), Decimal("20.00"))

        confirmation = self.client.post(
            self.confirm_url,
            {
                "amount": extracted['amount'],
                "merchant_name": extracted['merchant_name'],
                "transaction_date": extracted['transaction_date'],
                "transaction_time": extracted['transaction_time'],
                "payment_method": extracted['payment_method'],
                "payment_status": extracted['payment_status'],
                "upi_transaction_id": extracted['upi_transaction_id'],
                "google_transaction_id": extracted['google_transaction_id'],
                "bank_name": extracted['bank_name'],
                "upi_id": extracted['upi_id'],
            },
            format='json',
        )

        self.assertEqual(confirmation.status_code, status.HTTP_201_CREATED)
        expense = Expense.objects.get(user=self.user)
        self.assertEqual(expense.amount, Decimal("20.00"))
        self.assertEqual(expense.upi_transaction_id, "124819348086")
        self.assertEqual(expense.google_transaction_id, "CICAgNjFz_DOCA")
        self.assertEqual(expense.bank_name, "India Post Payment Bank")
        self.assertEqual(expense.expense_date.isoformat(), "2026-06-16")

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
