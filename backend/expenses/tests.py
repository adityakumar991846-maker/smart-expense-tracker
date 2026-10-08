from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
from accounts.models import User
from categories.models import Category
from .models import Expense

class ExpenseAPITests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(email="user1@example.com", password="Password123")
        self.user2 = User.objects.create_user(email="user2@example.com", password="Password123")

        self.client1 = APIClient()
        self.client1.force_authenticate(user=self.user1)

        self.client2 = APIClient()
        self.client2.force_authenticate(user=self.user2)

        self.category = Category.objects.create(name="Food", is_default=True)
        self.expense_list_url = reverse('expenses:expense-list-create')
        self.check_duplicate_url = reverse('expenses:expense-check-duplicate')

    def test_expense_creation(self):
        payload = {
            "amount": "250.50",
            "merchant_name": "Swiggy",
            "category_id": self.category.id,
            "expense_date": "2026-10-08",
            "payment_method": "Google Pay / UPI",
            "description": "Lunch order",
            "upi_transaction_id": "UPI123456789012"
        }
        response = self.client1.post(self.expense_list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(Decimal(str(response.data['expense']['amount'])), Decimal("250.50"))
        self.assertEqual(Expense.objects.filter(user=self.user1).count(), 1)

    def test_expense_negative_amount_fails(self):
        payload = {
            "amount": "-50.00",
            "merchant_name": "Invalid Merchant",
            "expense_date": "2026-10-08"
        }
        response = self.client1.post(self.expense_list_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_data_isolation(self):
        # User 1 creates an expense
        expense1 = Expense.objects.create(
            user=self.user1,
            amount=Decimal("100.00"),
            merchant_name="Private Store",
            expense_date="2026-10-08"
        )
        # User 2 creates an expense
        Expense.objects.create(
            user=self.user2,
            amount=Decimal("500.00"),
            merchant_name="User2 Store",
            expense_date="2026-10-08"
        )

        # User 1 lists expenses -> only sees own expense
        res1 = self.client1.get(self.expense_list_url)
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        results = res1.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['merchant_name'], "Private Store")

        # User 2 tries to access User 1's expense directly by ID -> 404 forbidden
        detail_url = reverse('expenses:expense-detail', kwargs={'pk': expense1.id})
        res2 = self.client2.get(detail_url)
        self.assertEqual(res2.status_code, status.HTTP_404_NOT_FOUND)

        # User 2 tries to delete User 1's expense -> 404 forbidden
        del_res = self.client2.delete(detail_url)
        self.assertEqual(del_res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Expense.objects.filter(id=expense1.id).exists())

    def test_duplicate_detection(self):
        Expense.objects.create(
            user=self.user1,
            amount=Decimal("99.00"),
            merchant_name="Chai Point",
            expense_date="2026-10-08",
            upi_transaction_id="UPI_DUP_9999"
        )

        # Check duplicate by upi_transaction_id
        check_payload = {
            "upi_transaction_id": "UPI_DUP_9999",
            "amount": "99.00",
            "merchant_name": "Chai Point",
            "expense_date": "2026-10-08"
        }
        res = self.client1.post(self.check_duplicate_url, check_payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data['is_duplicate'])

        # Different user checking same upi_id has is_duplicate = False (user isolated)
        res_user2 = self.client2.post(self.check_duplicate_url, check_payload, format='json')
        self.assertEqual(res_user2.status_code, status.HTTP_200_OK)
        self.assertFalse(res_user2.data['is_duplicate'])
