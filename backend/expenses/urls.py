from django.urls import path
from .views import ExpenseListCreateView, ExpenseDetailView, DuplicateCheckView

app_name = 'expenses'

urlpatterns = [
    path('', ExpenseListCreateView.as_view(), name='expense-list-create'),
    path('check-duplicate/', DuplicateCheckView.as_view(), name='expense-check-duplicate'),
    path('<int:pk>/', ExpenseDetailView.as_view(), name='expense-detail'),
]
