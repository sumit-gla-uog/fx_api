from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
# from .views import currencies_list, signup, me, logout_view
from .views import (
    currencies_list, signup, me, logout_view,
    pairs_list,
    portfolio,
    dashboard_summary, dashboard_market_snapshot,
    pair_latest, pair_history,
    trade_market, trades_list, trades_export,
    order_limit, orders_list, order_cancel,
)

urlpatterns = [
    # Auth
    path("v1/auth/signup/", signup, name="auth-signup"),
    path("v1/auth/login/", TokenObtainPairView.as_view(), name="auth-login"),
    path("v1/auth/refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("v1/auth/me/", me, name="auth-me"),
    path("v1/auth/logout/", logout_view, name="auth-logout"),

    # Currencies
    path("v1/currencies/", currencies_list, name="currencies-list"),

    # Pairs
    path("v1/pairs/", pairs_list, name="pairs-list"),
    path("v1/pairs/<int:id>/latest/", pair_latest, name="pair-latest"),
    path("v1/pairs/<int:id>/history/",pair_history, name="pair-history"),

    # Portfolio
    path("v1/portfolio/", portfolio, name="portfolio"),

    # Dashboard
    path("v1/dashboard/summary/", dashboard_summary, name="dashboard-summary"),
    path("v1/dashboard/market-snapshot/", dashboard_market_snapshot, name="dashboard-market-snapshot"),

    # Trades
    path("v1/trades/market/", trade_market,   name="trade-market"),   
    path("v1/trades/",        trades_list,    name="trades-list"),    
    path("v1/trades/export/", trades_export,  name="trades-export"),   

    # Orders
    path("v1/orders/limit/",          order_limit,  name="order-limit"),   
    path("v1/orders/",                orders_list,  name="orders-list"), 
    path("v1/orders/<int:id>/cancel/",order_cancel, name="order-cancel"),
]
