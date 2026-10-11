from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from accounts.models import User
from expenses.models import Expense
from categories.models import Category

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
        self.monthly_url = reverse('dashboard:dashboard-monthly-summary')
        self.food_category = Category.objects.create(name="Food", is_default=True)
        self.travel_category = Category.objects.create(name="Travel", is_default=True)

        today = timezone.localdate() if hasattr(timezone, 'localdate') else timezone.now().date()
        Expense.objects.create(
            user=self.user,
            amount=Decimal("350.00"),
            merchant_name="Zomato",
            category=self.food_category,
            category_name="Food",
            expense_date=today
        )
        Expense.objects.create(
            user=self.user,
            amount=Decimal("1200.00"),
            merchant_name="Uber",
            category=self.travel_category,
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
        self.assertEqual(
            {expense.category_id for expense in Expense.objects.filter(user=self.user)},
            {self.food_category.id, self.travel_category.id}
        )

    def test_dashboard_date_filters_include_month_start_and_exclude_other_dates(self):
        today = timezone.localdate()
        first_of_month = today.replace(day=1)
        previous_month_day = first_of_month - timedelta(days=1)
        next_day = today + timedelta(days=1)

        Expense.objects.create(
            user=self.user,
            amount=Decimal("11.00"),
            merchant_name="Previous month",
            expense_date=previous_month_day
        )
        Expense.objects.create(
            user=self.user,
            amount=Decimal("13.00"),
            merchant_name="First day of month",
            expense_date=first_of_month
        )
        Expense.objects.create(
            user=self.user,
            amount=Decimal("17.00"),
            merchant_name="Future date",
            expense_date=next_day
        )

        response = self.client.get(self.summary_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        metrics = response.data['metrics']
        self.assertEqual(metrics['total_spent'], 1591.00)
        self.assertEqual(metrics['month_spent'], 1563.00)
        expected_today = 1563.00 if today == first_of_month else 1550.00
        self.assertEqual(metrics['today_spent'], expected_today)
        self.assertEqual(metrics['transactions_count'], 5)

    def test_monthly_summary_returns_six_contiguous_months_and_zeroes(self):
        today = timezone.localdate()
        current_month = today.replace(day=1)
        oldest_month = current_month
        for _ in range(5):
            oldest_month = (oldest_month - timedelta(days=1)).replace(day=1)

        Expense.objects.create(
            user=self.user,
            amount=Decimal("19.00"),
            merchant_name="Oldest included month",
            expense_date=oldest_month
        )
        Expense.objects.create(
            user=self.user,
            amount=Decimal("23.00"),
            merchant_name="Outside monthly range",
            expense_date=oldest_month - timedelta(days=1)
        )

        response = self.client.get(self.monthly_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 6)
        expected_months = []
        for months_ago in range(5, -1, -1):
            year = current_month.year
            month = current_month.month - months_ago
            while month <= 0:
                month += 12
                year -= 1
            expected_months.append((year, month))
        self.assertEqual(
            [(item['year'], item['month']) for item in results],
            expected_months
        )
        self.assertEqual(results[0]['month_label'], oldest_month.strftime('%b %Y'))
        self.assertEqual(results[0]['total'], 19.00)
        self.assertEqual(
            [item['total'] for item in results[1:-1]],
            [0.00, 0.00, 0.00, 0.00]
        )
        self.assertEqual(results[-1]['total'], 1550.00)

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
