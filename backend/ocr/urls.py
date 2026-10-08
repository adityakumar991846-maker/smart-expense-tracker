from django.urls import path
from .views import OcrAnalyzeView, OcrConfirmView

app_name = 'ocr'

urlpatterns = [
    path('analyze/', OcrAnalyzeView.as_view(), name='ocr-analyze'),
    path('confirm/', OcrConfirmView.as_view(), name='ocr-confirm'),
]
