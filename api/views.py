from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Currency, CurrencyPair, PortfolioHolding
from .serializers import CurrencySerializer, CurrencyPairSerializer, PortfolioHoldingSerializer


@api_view(["POST"])
@permission_classes([AllowAny])
def signup(request):
    username = request.data.get("username")
    password = request.data.get("password")
    email = request.data.get("email", "")
    role = request.data.get("role", "customer")  # "customer" | "admin"

    if not username or not password:
        return Response({"error": "username and password required"}, status=status.HTTP_400_BAD_REQUEST)
    if User.objects.filter(username=username).exists():
        return Response({"error": "username already exists"}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(username=username, password=password, email=email)
    if role == "admin":
        user.is_staff = True
        user.save()

    return Response({"ok": True}, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    u = request.user
    role = "admin" if (u.is_staff or u.is_superuser) else "customer"
    return Response({
        "user": {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": role,
        }
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def logout_view(request):
    # JWT logout is handled client-side (delete tokens).
    return Response({"ok": True})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def currencies_list(request):
    search = request.query_params.get("search", "").strip()
    qs = Currency.objects.all().order_by("code")
    if search:
        qs = qs.filter(code__icontains=search) | qs.filter(name__icontains=search)
    data = CurrencySerializer(qs, many=True).data
    return Response({"currencies": data})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def pairs_list(request):
    search = request.query_params.get("search", "").strip().upper()
    qs = CurrencyPair.objects.select_related("base_currency", "quote_currency").order_by(
        "base_currency__code", "quote_currency__code"
    )
    if search:
        # allow search like "GBP" or "GBP/USD"
        if "/" in search:
            parts = [p for p in search.split("/") if p]
            if len(parts) == 2:
                qs = qs.filter(base_currency__code__icontains=parts[0], quote_currency__code__icontains=parts[1])
        else:
            qs = qs.filter(base_currency__code__icontains=search) | qs.filter(quote_currency__code__icontains=search)
    data = CurrencyPairSerializer(qs, many=True).data
    return Response({"pairs": data})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def portfolio_view(request):
    qs = PortfolioHolding.objects.select_related("currency").filter(user=request.user).order_by("currency__code")
    data = PortfolioHoldingSerializer(qs, many=True).data
    return Response({"holdings": data})
