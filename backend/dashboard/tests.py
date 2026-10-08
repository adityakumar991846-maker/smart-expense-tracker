from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
from django.utils import timezone
from accounts.models import User
from expenses.models import Expense

class DashboardMetricsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="dash@example.com",
            password="Password123",
            monthly_budget=Decimal("5000.00")
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.summary_url = reverse('dashboard:dashboard-summary')
        self.category_url = reverse('dashboard:dashboard-category-summary')

        today = timezone.localdate() if hasattr(timezone, 'localdate') else timezone.now().date()
        Expense.objects.create(
            user=self.user,
            amount=Decimal("350.00"),
            merchant_name="Zomato",
            category_name="Food",
            expense_date=today
        )
        Expense.objects.create(
            user=self.user,
            amount=Decimal("1200.00"),
            merchant_name="Uber",
            category_name="Travel",
            expense_date=today
        )

    def test_dashboard_summary_calculations(self):
        res = self.client.get(self.summary_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        metrics = res.data['metrics']
        self.assertEqual(metrics['total_spent'], 1550.00)
        self.assertEqual(metrics['today_spent'], 1550.00)
        self.assertEqual(metrics['transactions_count'], 2)
        self.assertEqual(metrics['highest_expense'], 1200.00)

        # Budget verification: 1550 / 5000 = 31%
        budget = res.data['budget']
        self.assertEqual(budget['monthly_budget'], 5000.00)
        self.assertEqual(budget['used_percentage'], 31.0)
        self.assertFalse(budget['is_warning'])

    def test_category_summary(self):
        res = self.client.get(self.category_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        results = res.data['results']
        categories = {r['category']: r['total'] for r in results}
        self.assertEqual(categories.get('Travel'), 1200.00)
        self.assertEqual(categories.get('Food'), 350.00)

    def test_reports_endpoint_and_csv_export(self):
        reports_url = reverse('reports')

        # Test JSON summary
        res = self.client.get(f"{reports_url}?period=monthly")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['summary']['total_spending'], 1550.00)
        self.assertEqual(res.data['summary']['transaction_count'], 2)
        self.assertEqual(res.data['summary']['average_expense'], 775.00)

        # Test CSV export
        csv_res = self.client.get(f"{reports_url}?period=monthly&export=csv")
        self.assertEqual(csv_res.status_code, status.HTTP_200_OK)
        self.assertEqual(csv_res['Content-Type'], 'text/csv')
        self.assertIn('attachment; filename=', csv_res['Content-Disposition'])
        content = csv_res.content.decode('utf-8')
        self.assertIn("Zomato", content)
        self.assertIn("Uber", content)
        self.assertIn("350.00", content)

