from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class MLAdminAccessTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username="admin_user",
            password="testpass123",
            role=User.Role.ADMIN,
        )
        self.officer_user = User.objects.create_user(
            username="officer_user",
            password="testpass123",
            role=User.Role.OFFICER,
        )

    def test_admin_can_access_ml_model_list(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("ml_models:model_list"))

        self.assertEqual(response.status_code, 200)

    def test_officer_is_redirected_from_ml_model_list(self):
        self.client.force_login(self.officer_user)

        response = self.client.get(reverse("ml_models:model_list"))

        self.assertRedirects(response, reverse("accounts:dashboard"))

    def test_officer_is_redirected_from_train_model_view(self):
        self.client.force_login(self.officer_user)

        response = self.client.get(reverse("ml_models:train_model"))

        self.assertRedirects(response, reverse("accounts:dashboard"))
