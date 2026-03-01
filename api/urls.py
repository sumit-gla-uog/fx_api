from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    currencies_list,
    pairs_list,
    portfolio_view,
    signup,
    me,
    logout_view,
)

urlpatterns = [
    path("v1/auth/signup/", signup, name="auth-signup"),
    path("v1/auth/login/", TokenObtainPairView.as_view(), name="auth-login"),
    path("v1/auth/refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("v1/auth/me/", me, name="auth-me"),
    path("v1/auth/logout/", logout_view, name="auth-logout"),

    path("v1/currencies/", currencies_list, name="currencies-list"),
    path("v1/pairs/", pairs_list, name="pairs-list"),
    path("v1/portfolio/", portfolio_view, name="portfolio"),
]
