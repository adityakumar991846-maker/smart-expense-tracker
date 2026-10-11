"""
OCR Service for Google Pay & UPI Payment Confirmation Screenshots.
Processes screenshots locally using Pillow & Tesseract OCR.
Does not send image data to external services.
"""

import os
import re
from datetime import datetime
from decimal import Decimal
from PIL import Image, ImageEnhance
from django.conf import settings
import pytesseract

# Configure Tesseract path if set
tesseract_cmd = getattr(settings, 'TESSERACT_CMD', os.getenv('TESSERACT_CMD', 'tesseract'))
if tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

# Merchant to Category mapping rules
MERCHANT_CATEGORY_RULES = {
    # Food & Dining
    'swiggy': 'Food',
    'zomato': 'Food',
    'mcdonald': 'Food',
    'domino': 'Food',
    'pizza': 'Food',
    'kfc': 'Food',
    'starbucks': 'Food',
    'chai': 'Food',
    'cafe': 'Food',
    'restaurant': 'Food',
    'baker': 'Food',
    'dhaba': 'Food',
    'eats': 'Food',
    'canteen': 'Food',

    # Travel & Commute
    'uber': 'Travel',
    'ola': 'Travel',
    'rapido': 'Travel',
    'metro': 'Travel',
    'irctc': 'Travel',
    'indian railway': 'Travel',
    'railway': 'Travel',
    'indigo': 'Travel',
    'air india': 'Travel',
    'redbus': 'Travel',
    'petrol': 'Travel',
    'fuel': 'Travel',
    'shell': 'Travel',
    'hpcl': 'Travel',
    'bpcl': 'Travel',
    'ioc': 'Travel',
    'toll': 'Travel',
    'fastag': 'Travel',

    # Shopping & E-Commerce
    'amazon': 'Shopping',
    'flipkart': 'Shopping',
    'myntra': 'Shopping',
    'meesho': 'Shopping',
    'ajio': 'Shopping',
    'zara': 'Shopping',
    'h&m': 'Shopping',
    'decathlon': 'Shopping',
    'croma': 'Shopping',
    'reliance digital': 'Shopping',
    'retail': 'Shopping',
    'mall': 'Shopping',

    # Groceries
    'blinkit': 'Groceries',
    'zepto': 'Groceries',
    'instamart': 'Groceries',
    'bigbasket': 'Groceries',
    'dmart': 'Groceries',
    'spencer': 'Groceries',
    'supermarket': 'Groceries',
    'kirana': 'Groceries',
    'provision': 'Groceries',

    # Bills & Utilities & Recharge
    'airtel': 'Bills',
    'jio': 'Bills',
    'vi': 'Bills',
    'vodafone': 'Bills',
    'bsnl': 'Bills',
    'recharge': 'Bills',
    'electricity': 'Bills',
    'bescom': 'Bills',
    'tata power': 'Bills',
    'adani electricity': 'Bills',
    'water': 'Bills',
    'gas': 'Bills',
    'cylinder': 'Bills',
    'indane': 'Bills',
    'hp gas': 'Bills',
    'broadband': 'Bills',
    'wifi': 'Bills',

    # Entertainment
    'netflix': 'Entertainment',
    'prime': 'Entertainment',
    'hotstar': 'Entertainment',
    'spotify': 'Entertainment',
    'bookmyshow': 'Entertainment',
    'pvr': 'Entertainment',
    'inox': 'Entertainment',
    'cinema': 'Entertainment',
    'movie': 'Entertainment',
    'gaming': 'Entertainment',
    'playstation': 'Entertainment',

    # Health & Medical
    'apollo': 'Health',
    'netmeds': 'Health',
    '1mg': 'Health',
    'pharmeasy': 'Health',
    'pharmacy': 'Health',
    'medplus': 'Health',
    'chemist': 'Health',
    'hospital': 'Health',
    'clinic': 'Health',
    'doctor': 'Health',
    'dental': 'Health',
    'pathology': 'Health',
    'diagnostic': 'Health',

    # Education
    'college': 'Education',
    'school': 'Education',
    'university': 'Education',
    'fee': 'Education',
    'tuition': 'Education',
    'coaching': 'Education',
    'coursera': 'Education',
    'udemy': 'Education',
    'allen': 'Education',
    'unacademy': 'Education',

    # Rent
    'rent': 'Rent',
    'landlord': 'Rent',
    'society': 'Rent',
    'maintenance': 'Rent',
    'flat': 'Rent',
    'apartment': 'Rent',
}

KNOWN_BANKS = [
    'India Post Payment Bank',
    'India Post Payments Bank',
    'State Bank of India',
    'SBI',
    'HDFC Bank',
    'ICICI Bank',
    'Axis Bank',
    'Kotak Mahindra Bank',
    'Punjab National Bank',
    'Bank of Baroda',
    'Canara Bank',
    'Union Bank of India',
    'Paytm Payments Bank',
    'Airtel Payments Bank',
    'IndusInd Bank',
    'Federal Bank',
    'IDFC First Bank',
    'Yes Bank',
]

class OcrService:
    """Service to preprocess, extract, and parse payment screenshot text."""

    @staticmethod
    def validate_image_file(file_obj):
        """Validates extension, size, and readable format."""
        max_bytes = 5 * 1024 * 1024  # 5MB
        if file_obj.size > max_bytes:
            return False, "Image size exceeds 5MB limit. Please upload a smaller image."

        allowed_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
        ext = os.path.splitext(file_obj.name.lower())[1]
        if ext not in allowed_extensions:
            return False, "Unsupported file format. Please upload a JPG, PNG, or WEBP image."

        try:
            image = Image.open(file_obj)
            image.verify()
            file_obj.seek(0)
            return True, None
        except Exception:
            return False, "Uploaded file is not a valid or readable image."

    @staticmethod
    def preprocess_image(image_file):
        """
        Enhances image for Tesseract recognition:
        - Converts to RGB
        - Upscales if narrow
        - Converts to grayscale without amplifying OCR noise
        """
        image_file.seek(0)
        img = Image.open(image_file).convert('RGB')

        # Resize if width < 1200 to boost OCR character resolution
        width, height = img.size
        if width < 1200:
            scale = 1200 / float(width)
            new_size = (1200, int(height * scale))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        # Grayscale
        gray = img.convert('L')

        return gray

    @classmethod
    def extract_text_from_image(cls, image_file):
        """Executes local Tesseract OCR on preprocessed image."""
        try:
            processed_img = cls.preprocess_image(image_file)
            # PSM 6 or 3 is ideal for mobile receipt screenshots
            custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(processed_img, config=custom_config)

            # If sparse, fallback to default PSM 3
            if len(text.strip()) < 15:
                text = pytesseract.image_to_string(processed_img, config=r'--oem 3 --psm 3')

            if cls._extract_amount(text, text.splitlines()) is None:
                amount_text = cls._extract_top_center_amount(processed_img)
                if amount_text:
                    text = f'{text.rstrip()}\nPayment amount: {amount_text}'

            return text, None
        except pytesseract.TesseractNotFoundError:
            return None, "Tesseract OCR is not installed or configured on the server."
        except Exception as e:
            return None, "We couldn't read this screenshot. Please upload a clearer payment screenshot."

    @staticmethod
    def _extract_top_center_amount(image):
        """Read the prominent payment amount area when full-page OCR misses it."""
        width, height = image.size
        amount_regions = (
            (0.24, 0.196, 0.76, 0.28),
            (0.30, 0.18, 0.70, 0.31),
        )
        amount_pattern = (
            r'(?:₹|Rs\.?|INR)?\s*'
            r'((?:\d{1,3}(?:,\d{2,3})+|\d{1,10})(?:\.\d{1,2})?)'
        )

        for left, top, right, bottom in amount_regions:
            amount_region = image.crop((
                int(width * left),
                int(height * top),
                int(width * right),
                int(height * bottom),
            ))
            amount_region = ImageEnhance.Contrast(amount_region).enhance(2)
            text = pytesseract.image_to_string(
                amount_region,
                config=r'--oem 3 --psm 6',
            ).strip()
            # Tesseract can render the rupee glyph as "=" while preserving the digits.
            text = re.sub(r'^=+\s*', '', text)
            amount_match = re.fullmatch(amount_pattern, text, re.IGNORECASE)
            if amount_match:
                return amount_match.group(1).replace(',', '')

        return None

    @classmethod
    def parse_transaction_data(cls, text):
        """
        Parses Google Pay / UPI transaction text into structured fields.
        Returns dict with extracted fields or null if not detected.
        """
        if not text:
            return cls._empty_result()

        lines = [line.strip() for line in text.split('\n') if line.strip()]

        amount = cls._extract_amount(text, lines)
        merchant = cls._extract_merchant(text, lines)
        trans_date, trans_time = cls._extract_date_time(text)
        status = cls._extract_status(text)
        payment_method = cls._extract_payment_method(text)
        upi_txn_id = cls._extract_upi_txn_id(text)
        google_txn_id = cls._extract_google_txn_id(text)
        bank_name = cls._extract_bank_name(text)
        upi_id = cls._extract_upi_id(text)
        source_app = 'Google Pay' if ('google' in text.lower() or google_txn_id) else 'UPI'

        suggested_category = cls.suggest_category(merchant)

        return {
            "amount": float(amount) if amount is not None else None,
            "merchant_name": merchant,
            "transaction_date": trans_date,
            "transaction_time": trans_time,
            "payment_status": status or 'Completed',
            "payment_method": payment_method or 'Google Pay / UPI',
            "upi_transaction_id": upi_txn_id,
            "google_transaction_id": google_txn_id,
            "bank_name": bank_name,
            "upi_id": upi_id,
            "source_app": source_app,
            "suggested_category": suggested_category,
        }

    @staticmethod
    def _extract_amount(text, lines):
        """Extracts an amount only when currency or a payment label identifies it."""
        amount_pattern = r'(?<![\w,])(?:\d{1,3}(?:,\d{2,3})+|\d{1,10})(?:\.\d{1,2})?(?![\w,])'
        currency_pattern = r'(?<![A-Za-z])(?:₹|Rs\.?|INR)(?![A-Za-z])'

        def parse_amount(value):
            match = re.fullmatch(
                rf'\s*(?:{currency_pattern}\s*)?({amount_pattern})\s*',
                value,
                re.IGNORECASE,
            )
            if not match:
                return None
            amount = Decimal(match.group(1).replace(',', ''))
            return amount if amount > 0 else None

        def is_currency_only(value):
            return bool(re.fullmatch(rf'\s*{currency_pattern}\s*', value, re.IGNORECASE))

        label_pattern = re.compile(
            r'(?<![A-Za-z])(?:payment\s+amount|payment\s+of|amount\s+(?:paid|sent)|amount|paid|sent|total)'
            r'\b\s*[:\-]?\s*(.*?)\s*$',
            re.IGNORECASE,
        )

        for index, line in enumerate(lines):
            label_match = label_pattern.search(line)
            if not label_match:
                continue

            remainder = label_match.group(1)
            amount = parse_amount(remainder)
            if amount is not None:
                return amount
            amount_with_status = re.fullmatch(
                rf'\s*(?:{currency_pattern}\s*)?({amount_pattern})'
                r'\s+(?:completed|successful|successfully|sent)\s*',
                remainder,
                re.IGNORECASE,
            )
            if amount_with_status:
                amount = Decimal(amount_with_status.group(1).replace(',', ''))
                if amount > 0:
                    return amount
            if remainder and not is_currency_only(remainder):
                continue

            for following_line in lines[index + 1:index + 3]:
                if is_currency_only(following_line):
                    continue
                amount = parse_amount(following_line)
                if amount is not None:
                    return amount
                break

        currency_amount = re.search(
            rf'{currency_pattern}\s*({amount_pattern})',
            text,
            re.IGNORECASE,
        )
        if currency_amount:
            amount = Decimal(currency_amount.group(1).replace(',', ''))
            if amount > 0:
                return amount

        return None

    @staticmethod
    def _extract_merchant(text, lines):
        """Extracts merchant or recipient name."""
        # Pattern: To: <Merchant> or Paid to <Merchant>
        to_pattern = re.search(r'(?:To|Paid to)\s*[:\-]?\s*([^\n\r]+)', text, re.IGNORECASE)
        if to_pattern:
            merchant = to_pattern.group(1).strip()
            # Clean common noise
            merchant = re.sub(r'^(the|a|an)\s+', '', merchant, flags=re.IGNORECASE)
            if len(merchant) > 1 and not re.match(r'^\d+$', merchant):
                return merchant

        # Look for name before "Completed" or "Payment to"
        for i, line in enumerate(lines):
            lower = line.lower()
            if 'completed' in lower or 'paid' in lower:
                # Often merchant is previous line
                if i > 0:
                    candidate = lines[i - 1].strip()
                    if candidate and not re.search(r'[₹\d]{2,}', candidate) and len(candidate) > 2:
                        return candidate
            if 'banking name:' in lower:
                name_match = re.search(r'banking name:\s*([^\n\r]+)', line, re.IGNORECASE)
                if name_match:
                    return name_match.group(1).strip()

        return None

    @staticmethod
    def _extract_date_time(text):
        """Extracts transaction date and time, normalizing to YYYY-MM-DD and HH:MM."""
        trans_date = None
        trans_time = None

        # Matches: "16 Jun 2026, 12:20 pm" or "16 Jun 2026 12:20 PM" or "16-06-2026 12:20"
        dt_match = re.search(
            r'(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})[,\s]+(\d{1,2}:\d{2}\s*(?:am|pm|AM|PM)?)',
            text
        )
        if dt_match:
            date_str = dt_match.group(1).strip()
            time_str = dt_match.group(2).strip()
            try:
                dt = datetime.strptime(date_str, '%d %b %Y')
                trans_date = dt.strftime('%Y-%m-%d')
            except Exception:
                try:
                    dt = datetime.strptime(date_str, '%d %B %Y')
                    trans_date = dt.strftime('%Y-%m-%d')
                except Exception:
                    pass

            # Parse time
            trans_time = OcrService._normalize_time(time_str)

        # Alternate date format: DD-MM-YYYY or DD/MM/YYYY
        if not trans_date:
            d_match = re.search(r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})', text)
            if d_match:
                try:
                    d, m, y = d_match.groups()
                    dt = datetime(int(y), int(m), int(d))
                    trans_date = dt.strftime('%Y-%m-%d')
                except Exception:
                    pass

        # Standalone time if not yet found
        if not trans_time:
            t_match = re.search(r'(\d{1,2}:\d{2}\s*(?:am|pm|AM|PM))', text)
            if t_match:
                trans_time = OcrService._normalize_time(t_match.group(1).strip())

        return trans_date, trans_time

    @staticmethod
    def _normalize_time(time_str):
        if not time_str:
            return None
        time_str = time_str.strip().lower()
        try:
            if 'am' in time_str or 'pm' in time_str:
                clean_time = time_str.replace(' ', '')
                t = datetime.strptime(clean_time, '%I:%M%p')
            else:
                t = datetime.strptime(time_str, '%H:%M')
            return t.strftime('%H:%M')
        except Exception:
            return None

    @staticmethod
    def _extract_status(text):
        lower = text.lower()
        if 'completed' in lower or 'successful' in lower or 'payment sent' in lower:
            return 'Completed'
        if 'pending' in lower or 'processing' in lower:
            return 'Pending'
        if 'failed' in lower or 'declined' in lower:
            return 'Failed'
        return 'Completed'

    @staticmethod
    def _extract_payment_method(text):
        lower = text.lower()
        if 'google pay' in lower or 'gpay' in lower:
            return 'Google Pay'
        if 'phonepe' in lower:
            return 'PhonePe'
        if 'paytm' in lower:
            return 'Paytm'
        if 'upi' in lower:
            return 'UPI'
        return 'Google Pay / UPI'

    @staticmethod
    def _extract_upi_txn_id(text):
        # 12 digit UPI reference / transaction ID
        match = re.search(r'(?:UPI\s*(?:transaction|txn|ref)?\s*(?:ID|no\.?|number)?)\s*[:\-]?\s*([0-9]{12})', text, re.IGNORECASE)
        if match:
            return match.group(1)

        # Standalone 12 digits
        standalone = re.search(r'\b([0-9]{12})\b', text)
        if standalone:
            return standalone.group(1)
        return None

    @staticmethod
    def _extract_google_txn_id(text):
        # Google transaction ID format: alphanumeric e.g. CICAgNjFz_DOCa
        match = re.search(r'Google\s*transaction\s*ID\s*[:\-]?\s*([A-Za-z0-9_\-]+)', text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    @staticmethod
    def _extract_bank_name(text):
        for bank in KNOWN_BANKS:
            if bank.lower() in text.lower():
                return bank

        # Generic bank match: "xyz Bank"
        generic = re.search(r'([A-Za-z\s]+(?:Payment\s+)?Bank)', text, re.IGNORECASE)
        if generic:
            val = generic.group(1).strip()
            if 3 < len(val) < 40:
                return val
        return None

    @staticmethod
    def _extract_upi_id(text):
        # Match user@bank format
        match = re.search(r'([a-zA-Z0-9.\-_]{2,}@[a-zA-Z0-9]{2,})', text)
        if match:
            return match.group(1).strip()
        return None

    @classmethod
    def suggest_category(cls, merchant_name):
        """Detects category based on merchant name keywords with word boundaries."""
        if not merchant_name:
            return 'Other'

        merchant_lower = merchant_name.lower()
        for keyword, category in MERCHANT_CATEGORY_RULES.items():
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, merchant_lower):
                return category
        return 'Other'

    @classmethod
    def _empty_result(cls):
        return {
            "amount": None,
            "merchant_name": None,
            "transaction_date": None,
            "transaction_time": None,
            "payment_status": "Completed",
            "payment_method": "Google Pay / UPI",
            "upi_transaction_id": None,
            "google_transaction_id": None,
            "bank_name": None,
            "upi_id": None,
            "source_app": "UPI",
            "suggested_category": "Other",
        }
