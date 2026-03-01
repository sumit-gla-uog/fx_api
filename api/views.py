from django.shortcuts import render

from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

# Create your views here.
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
def currencies_list(request):
    currencies = [
  { "code": 'GBP', "name": 'British Pound', "symbol": '£', "flag": '🇬🇧', "enabled": True },
  { "code": 'USD', "name": 'US Dollar', "symbol": '$', "flag": '🇺🇸', "enabled": True },
  { "code": 'EUR', "name": 'Euro', "symbol": '€', "flag": '🇪🇺', "enabled": True },
  { "code": 'JPY', "name": 'Japanese Yen', "symbol": '¥', "flag": '🇯🇵', "enabled": True },
  { "code": 'CNY', "name": 'Chinese Yuan', "symbol": '¥', "flag": '🇨🇳', "enabled": True },
  { "code": 'HKD', "name": 'Hong Kong Dollar', "symbol": 'HK$', "flag": '🇭🇰', "enabled": True },
  { "code": 'AUD', "name": 'Australian Dollar', "symbol": 'A$', "flag": '🇦🇺', "enabled": True },
  { "code": 'CAD', "name": 'Canadian Dollar', "symbol": 'C$', "flag": '🇨🇦', "enabled": True },
  { "code": 'CHF', "name": 'Swiss Franc', "symbol": 'CHF', "flag": '🇨🇭', "enabled": True },
  { "code": 'SGD', "name": 'Singapore Dollar', "symbol": 'S$', "flag": '🇸🇬', "enabled": True },
]
    return Response({"currencies": currencies})
