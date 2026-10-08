from django.db import models
from django.conf import settings

DEFAULT_CATEGORIES = [
    {"name": "Food", "icon": "utensils", "color": "#f97316"},
    {"name": "Travel", "icon": "car", "color": "#3b82f6"},
    {"name": "Shopping", "icon": "shopping-bag", "color": "#ec4899"},
    {"name": "Bills", "icon": "file-text", "color": "#eab308"},
    {"name": "Education", "icon": "graduation-cap", "color": "#8b5cf6"},
    {"name": "Entertainment", "icon": "film", "color": "#a855f7"},
    {"name": "Health", "icon": "heart-pulse", "color": "#ef4444"},
    {"name": "Groceries", "icon": "shopping-cart", "color": "#10b981"},
    {"name": "Rent", "icon": "home", "color": "#06b6d4"},
    {"name": "Other", "icon": "more-horizontal", "color": "#64748b"},
]

class Category(models.Model):
    """
    Expense category model.
    System categories have user=None and is_default=True.
    User custom categories have user=request.user.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='custom_categories'
    )
    name = models.CharField(max_length=50)
    icon = models.CharField(max_length=50, default='tag')
    color = models.CharField(max_length=20, default='#6366f1')
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'name'],
                name='unique_user_category_name'
            )
        ]

    def __str__(self):
        return f"{self.name} {'(System)' if self.is_default else f'({self.user})'}"

    @classmethod
    def seed_defaults(cls):
        """Ensures default system categories are present in database."""
        created = []
        for cat in DEFAULT_CATEGORIES:
            obj, is_new = cls.objects.get_or_create(
                user=None,
                name=cat["name"],
                defaults={
                    "icon": cat["icon"],
                    "color": cat["color"],
                    "is_default": True
                }
            )
            if is_new:
                created.append(obj)
        return created
