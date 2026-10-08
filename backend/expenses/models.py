from django.db import models
from django.conf import settings
from categories.models import Category

class Expense(models.Model):
    """
    Core Expense model.
    Stores manual entries and OCR-extracted transaction records.
    Every expense is strictly partitioned by user.
    """
    PAYMENT_METHOD_CHOICES = [
        ('Google Pay', 'Google Pay'),
        ('Google Pay / UPI', 'Google Pay / UPI'),
        ('PhonePe', 'PhonePe'),
        ('Paytm', 'Paytm'),
        ('UPI', 'UPI'),
        ('Cash', 'Cash'),
        ('Card', 'Card'),
        ('Bank Transfer', 'Bank Transfer'),
        ('Other', 'Other'),
    ]

    SOURCE_CHOICES = [
        ('Manual', 'Manual'),
        ('Screenshot OCR', 'Screenshot OCR'),
    ]

    STATUS_CHOICES = [
        ('Completed', 'Completed'),
        ('Pending', 'Pending'),
        ('Failed', 'Failed'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='expenses'
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text='Expense amount in currency'
    )
    merchant_name = models.CharField(
        max_length=255,
        help_text='Name of vendor, receiver, or merchant'
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expenses'
    )
    category_name = models.CharField(
        max_length=100,
        default='Other',
        help_text='Cached name of category for resilience'
    )
    expense_date = models.DateField(
        db_index=True,
        help_text='Date the transaction took place'
    )
    expense_time = models.TimeField(
        null=True,
        blank=True,
        help_text='Time the transaction took place'
    )
    payment_method = models.CharField(
        max_length=50,
        choices=PAYMENT_METHOD_CHOICES,
        default='Google Pay / UPI'
    )
    description = models.TextField(
        blank=True,
        default='',
        help_text='Optional user notes or transaction description'
    )
    source = models.CharField(
        max_length=50,
        choices=SOURCE_CHOICES,
        default='Manual'
    )
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='Completed'
    )

    # Google Pay / UPI Screenshot OCR metadata
    upi_transaction_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
        help_text='UPI 12-digit transaction ID or reference'
    )
    google_transaction_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
        help_text='Google Pay alphanumeric transaction ID'
    )
    bank_name = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        help_text='Bank or payment provider name'
    )
    upi_id = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        help_text='Virtual Payment Address (VPA / UPI ID)'
    )
    receipt_image = models.ImageField(
        upload_to='receipts/%Y/%m/',
        null=True,
        blank=True,
        help_text='Optional upload of the original screenshot or receipt'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-expense_date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'expense_date']),
            models.Index(fields=['user', 'upi_transaction_id']),
            models.Index(fields=['user', 'google_transaction_id']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.merchant_name} - ₹{self.amount} ({self.expense_date})"

    def save(self, *args, **kwargs):
        # Keep category_name synchronized
        if self.category:
            self.category_name = self.category.name
        elif not self.category_name:
            self.category_name = 'Other'
        super().save(*args, **kwargs)
