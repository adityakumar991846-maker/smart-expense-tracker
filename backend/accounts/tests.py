from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from .models import User

class AccountsAuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('accounts:register')
        self.login_url = reverse('accounts:login')
        self.profile_url = reverse('accounts:profile')
        self.change_password_url = reverse('accounts:change_password')

    def test_user_registration_success(self):
        payload = {
            "full_name": "Test User",
            "email": "test@example.com",
            "password": "Password123!",
            "confirm_password": "Password123!"
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertIn('token', response.data)
        self.assertEqual(response.data['user']['email'], 'test@example.com')
        self.assertTrue(User.objects.filter(email='test@example.com').exists())

    def test_registration_duplicate_email_fails(self):
        User.objects.create_user(email="duplicate@example.com", password="Password123!")
        payload = {
            "full_name": "Another User",
            "email": "duplicate@example.com",
            "password": "Password123!",
            "confirm_password": "Password123!"
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])

    def test_registration_password_mismatch_fails(self):
        payload = {
            "full_name": "Mismatch User",
            "email": "mismatch@example.com",
            "password": "Password123!",
            "confirm_password": "DifferentPassword!"
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_success(self):
        user = User.objects.create_user(email="login@example.com", password="SecurePassword123")
        response = self.client.post(self.login_url, {
            "email": "login@example.com",
            "password": "SecurePassword123"
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('token', response.data)

    def test_login_invalid_credentials_fails(self):
        User.objects.create_user(email="login@example.com", password="SecurePassword123")
        response = self.client.post(self.login_url, {
            "email": "login@example.com",
            "password": "WrongPassword"
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
