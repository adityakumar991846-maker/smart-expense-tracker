from django.urls import path
from .views import DashboardSummaryView, CategorySummaryView, MonthlySummaryView

app_name = 'dashboard'

urlpatterns = [
    path('summary/', DashboardSummaryView.as_view(), name='dashboard-summary'),
    path('category-summary/', CategorySummaryView.as_view(), name='dashboard-category-summary'),
    path('monthly-summary/', MonthlySummaryView.as_view(), name='dashboard-monthly-summary'),
]
