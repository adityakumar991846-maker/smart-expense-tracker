from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Max, Count
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from expenses.models import Expense
from expenses.serializers import ExpenseSerializer
from categories.models import Category

class DashboardSummaryView(APIView):
    """
    GET /api/dashboard/summary/
    Returns core metrics: total expenses, today's, this month's, count, highest,
    budget progress and recent expenses.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        today = timezone.localdate() if hasattr(timezone, 'localdate') else timezone.now().date()
        first_of_month = today.replace(day=1)

        user_expenses = Expense.objects.filter(user=user)

        total_spent = user_expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        today_spent = user_expenses.filter(expense_date=today).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        month_spent = user_expenses.filter(expense_date__gte=first_of_month, expense_date__lte=today).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        total_txns = user_expenses.count()
        highest_expense = user_expenses.aggregate(highest=Max('amount'))['highest'] or Decimal('0.00')

        recent_expenses = user_expenses.order_by('-expense_date', '-created_at')[:5]

        # Budget calculation
        monthly_budget = user.monthly_budget or Decimal('0.00')
        remaining_budget = max(Decimal('0.00'), monthly_budget - month_spent)
        budget_used_percent = (
            min(100.0, round(float(month_spent / monthly_budget * 100), 1))
            if monthly_budget > 0 else 0.0
        )
        is_budget_warning = budget_used_percent >= 80.0 if monthly_budget > 0 else False

        return Response({
            "success": True,
            "currency": user.currency,
            "metrics": {
                "total_spent": float(total_spent),
                "today_spent": float(today_spent),
                "month_spent": float(month_spent),
                "transactions_count": total_txns,
                "highest_expense": float(highest_expense),
            },
            "budget": {
                "monthly_budget": float(monthly_budget),
                "month_spent": float(month_spent),
                "remaining_budget": float(remaining_budget),
                "used_percentage": budget_used_percent,
                "is_warning": is_budget_warning
            },
            "recent_expenses": ExpenseSerializer(recent_expenses, many=True, context={'request': request}).data
        }, status=status.HTTP_200_OK)

class CategorySummaryView(APIView):
    """
    GET /api/dashboard/category-summary/
    Aggregates spending by category for doughnut / pie chart.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        qs = Expense.objects.filter(user=user).values('category_name').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')

        results = [
            {
                "category": item['category_name'] or 'Other',
                "total": float(item['total']),
                "count": item['count']
            }
            for item in qs
        ]

        return Response({"success": True, "results": results}, status=status.HTTP_200_OK)

class MonthlySummaryView(APIView):
    """
    GET /api/dashboard/monthly-summary/
    Aggregates spending by month over the past 6 months for trend line/bar charts.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        today = timezone.localdate() if hasattr(timezone, 'localdate') else timezone.now().date()

        # Generate last 6 calendar months
        months_data = []
        for i in range(5, -1, -1):
            year = today.year
            month = today.month - i
            while month <= 0:
                month += 12
                year -= 1

            start_date = datetime(year, month, 1).date()
            if month == 12:
                end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
            else:
                end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)

            month_label = start_date.strftime('%b %Y')
            total = Expense.objects.filter(
                user=user,
                expense_date__gte=start_date,
                expense_date__lte=end_date
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            months_data.append({
                "month_label": month_label,
                "year": year,
                "month": month,
                "total": float(total)
            })

        return Response({"success": True, "results": months_data}, status=status.HTTP_200_OK)

class ReportsView(APIView):
    """
    GET /api/reports/
    Returns analytical reports filtered by period (daily, weekly, monthly, custom).
    Supports export=csv for downloading CSV report.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        today = timezone.localdate() if hasattr(timezone, 'localdate') else timezone.now().date()

        period = request.query_params.get('period', 'monthly').lower()
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        export = request.query_params.get('export', '').lower()

        queryset = Expense.objects.filter(user=user)

        # Date filtering
        if period == 'daily':
            queryset = queryset.filter(expense_date=today)
        elif period == 'weekly':
            seven_days_ago = today - timedelta(days=7)
            queryset = queryset.filter(expense_date__gte=seven_days_ago, expense_date__lte=today)
        elif period == 'monthly':
            first_of_month = today.replace(day=1)
            queryset = queryset.filter(expense_date__gte=first_of_month, expense_date__lte=today)
        elif period == 'custom':
            if date_from:
                queryset = queryset.filter(expense_date__gte=date_from)
            if date_to:
                queryset = queryset.filter(expense_date__lte=date_to)

        # Handle CSV Export
        if export == 'csv':
            import csv
            from django.http import HttpResponse

            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="expenses_{period}_{today}.csv"'

            writer = csv.writer(response)
            writer.writerow([
                'ID', 'Date', 'Time', 'Merchant / Receiver', 'Amount (INR)',
                'Category', 'Payment Method', 'Source', 'Status',
                'UPI Transaction ID', 'Google Transaction ID', 'Bank Name', 'UPI ID', 'Description'
            ])

            for exp in queryset.order_by('-expense_date', '-created_at'):
                writer.writerow([
                    exp.id,
                    exp.expense_date,
                    exp.expense_time or '',
                    exp.merchant_name,
                    exp.amount,
                    exp.category_name,
                    exp.payment_method,
                    exp.source,
                    exp.status,
                    exp.upi_transaction_id or '',
                    exp.google_transaction_id or '',
                    exp.bank_name or '',
                    exp.upi_id or '',
                    exp.description or ''
                ])

            return response

        # Aggregate Metrics
        total_spending = queryset.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        transaction_count = queryset.count()
        highest_expense = queryset.aggregate(highest=Max('amount'))['highest'] or Decimal('0.00')
        average_expense = (
            round(total_spending / transaction_count, 2)
            if transaction_count > 0 else Decimal('0.00')
        )

        # Category Breakdown
        cat_qs = queryset.values('category_name').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')

        category_breakdown = []
        for c in cat_qs:
            c_total = float(c['total'])
            pct = round((c_total / float(total_spending) * 100), 1) if float(total_spending) > 0 else 0
            category_breakdown.append({
                "category": c['category_name'] or 'Other',
                "total": c_total,
                "count": c['count'],
                "percentage": pct
            })

        # Serialized list (limit to 50 for performance)
        recent_list = ExpenseSerializer(queryset.order_by('-expense_date', '-created_at')[:50], many=True).data

        return Response({
            "success": True,
            "period": period,
            "currency": user.currency,
            "summary": {
                "total_spending": float(total_spending),
                "transaction_count": transaction_count,
                "average_expense": float(average_expense),
                "highest_expense": float(highest_expense),
            },
            "category_breakdown": category_breakdown,
            "expenses": recent_list
        }, status=status.HTTP_200_OK)

