import requests
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.parsers import MultiPartParser, FormParser

from .serializers import SignupSerializer, UserSerializer

User = get_user_model()


def issue_tokens(user):
    """JWT access/refresh 발급"""
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class SignupView(APIView):
    """SIGNUP_01 - 회원가입"""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        # 회원가입 성공 시에만 홈 이동 → 프론트가 판단하도록 토큰까지 응답
        return Response(
            {"user": UserSerializer(user).data, "token": issue_tokens(user)},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """LOGIN_01 - 이메일 로그인. 미일치 시 메시지 출력"""

    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").lower()
        password = request.data.get("password", "")

        user = User.objects.filter(email=email).first()
        # 계정 존재 여부 노출 방지 위해 통합 메시지
        if user is None or not user.check_password(password):
            return Response(
                {"detail": "이메일 또는 비밀번호가 일치하지 않습니다."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response(
            {"user": UserSerializer(user).data, "token": issue_tokens(user)},
            status=status.HTTP_200_OK,
        )


class SocialLoginView(APIView):


    permission_classes = [AllowAny]

    def post(self, request, provider):
        access_token = request.data.get("access_token")
        if not access_token:
            return Response(
                {"detail": "access_token이 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if provider == User.Provider.KAKAO:
            profile = self._get_kakao_profile(access_token)
        elif provider == User.Provider.NAVER:
            profile = self._get_naver_profile(access_token)
        else:
            return Response(
                {"detail": "지원하지 않는 소셜 로그인입니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if profile is None:
            return Response(
                {"detail": "소셜 인증에 실패했습니다."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user, created = self._get_or_create_social_user(provider, profile)
        return Response(
            {
                "user": UserSerializer(user).data,
                "token": issue_tokens(user),
                "created": created,  # 신규 가입 여부 (온보딩 분기용)
            },
            status=status.HTTP_200_OK,
        )

    # --- provider별 프로필 조회 ---

    def _get_kakao_profile(self, access_token):
        resp = requests.get(
            "https://kapi.kakao.com/v2/user/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=5,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        account = data.get("kakao_account", {})
        return {
            "social_id": str(data["id"]),
            "email": account.get("email"),
            "nickname": account.get("profile", {}).get("nickname"),
        }

    def _get_naver_profile(self, access_token):
        resp = requests.get(
            "https://openapi.naver.com/v1/nid/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=5,
        )
        if resp.status_code != 200:
            return None
        data = resp.json().get("response", {})
        if not data:
            return None
        return {
            "social_id": str(data["id"]),
            "email": data.get("email"),
            "nickname": data.get("nickname"),
        }

    # --- 로그인 or 자동가입 ---

    def _get_or_create_social_user(self, provider, profile):
        user = User.objects.filter(
            provider=provider, social_id=profile["social_id"]
        ).first()
        if user:
            return user, False

        # 소셜 유저는 name/phone/nickname 모두 빈칸 → 나중에 프로필에서 설정
            user = User.objects.create_user(
                email=profile.get("email") or f"{profile['social_id']}@{provider}.social",
                provider=provider,
                social_id=profile["social_id"],
                password=None,
            )
        # 닉네임 자동 배정
        user.nickname = f"user{user.id}"
        user.save(update_fields=["nickname"])

        return user, True

# ─────────────────────────────────────────────
# RESERVATION_01 - 매장 방문 연계
# ─────────────────────────────────────────────
from django.db import IntegrityError
from rest_framework.generics import ListAPIView

from .models import Store, Reservation
from .serializers import (
    StoreSerializer,
    ReservationSerializer,
    ReservationCreateSerializer,
)


class StoreListView(ListAPIView):
    """RESERVATION_01(1) - 운영 중인 매장 목록"""

    permission_classes = [AllowAny]
    serializer_class = StoreSerializer
    pagination_class = None  # 매장 수가 적어 전체 반환

    def get_queryset(self):
        return Store.objects.filter(is_active=True)


class BookedTimeListView(APIView):
    """
    RESERVATION_01(2) - 날짜 선택 지원.
    특정 매장·날짜에 이미 예약된 시간 목록을 반환 → 프론트가 마감 처리
    GET /api/reservations/booked/?store=1&date=2026-08-20
    """

    permission_classes = [AllowAny]

    def get(self, request):
        store_id = request.query_params.get("store")
        date = request.query_params.get("date")
        if not store_id or not date:
            return Response(
                {"detail": "store와 date는 필수입니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booked = (
            Reservation.objects.filter(
                store_id=store_id,
                reserved_at__date=date,
                status=Reservation.Status.CONFIRMED,
            )
            .values_list("reserved_at", flat=True)
        )
        # 시각만 추출해 리스트로
        times = [dt.strftime("%H:%M") for dt in booked]
        return Response({"booked_times": times}, status=status.HTTP_200_OK)


class ReservationCreateView(APIView):
    """RESERVATION_01(3) - 예약 완료. 로그인/비로그인 모두 가능"""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ReservationCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        try:
            reservation = serializer.save()
        except IntegrityError:
            # 같은 매장·같은 시간 중복 예약 (unique_store_time)
            return Response(
                {"detail": "이미 예약된 시간입니다. 다른 시간을 선택해주세요."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(
            ReservationSerializer(reservation).data,
            status=status.HTTP_201_CREATED,
        )

# ─────────────────────────────────────────────
# MYPAGE_01 - 프로필/계정관리
# ─────────────────────────────────────────────
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import RetrieveAPIView, UpdateAPIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from .serializers import ProfileUpdateSerializer, WithdrawSerializer


class ProfileView(RetrieveAPIView):
    """MYPAGE_01(1) - 프로필 조회"""

    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class NicknameUpdateView(UpdateAPIView):
    """MYPAGE_01(2) - 닉네임 수정"""

    permission_classes = [IsAuthenticated]
    serializer_class = ProfileUpdateSerializer
    parser_classes = [MultiPartParser, FormParser]
    http_method_names = ["patch"]

    def get_object(self):
        return self.request.user


class LogoutView(APIView):
    """MYPAGE_01(7) - 로그아웃. refresh token 블랙리스트 처리"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"detail": "refresh 토큰이 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            return Response({"detail": "유효하지 않은 토큰입니다."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_205_RESET_CONTENT)


class WithdrawView(APIView):
    """MYPAGE_01(8) - 회원탈퇴. is_active=False 처리(소프트 삭제)"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = WithdrawSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.is_active = False
        user.save(update_fields=["is_active"])

        return Response({"detail": "탈퇴가 완료되었습니다."}, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────
# MYPAGE_01(3) - 예약 내역 조회/변경/취소
# ─────────────────────────────────────────────
from .serializers import (
    ReservationUpdateSerializer,
    ItemListSerializer,
    OwnershipSerializer,
    OwnershipCreateSerializer,
    WishlistSerializer,
    WishlistCreateSerializer,
)


class MyReservationListView(ListAPIView):
    """MYPAGE_01(3.1) - 내 예약 내역. 지난 예약 포함 전체"""

    permission_classes = [IsAuthenticated]
    serializer_class = ReservationSerializer
    pagination_class = None

    def get_queryset(self):
        return (
            Reservation.objects.filter(user=self.request.user)
            .select_related("store")
            .order_by("-reserved_at")
        )


class ReservationDetailView(APIView):
    """MYPAGE_01(3.2) - 예약 변경(PATCH) / 취소(DELETE)"""

    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        return Reservation.objects.filter(pk=pk, user=user).first()

    def patch(self, request, pk):
        reservation = self.get_object(pk, request.user)
        if reservation is None:
            return Response({"detail": "예약을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ReservationUpdateSerializer(reservation, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            reservation = serializer.save(status=Reservation.Status.CHANGED)
        except IntegrityError:
            return Response(
                {"detail": "이미 예약된 시간입니다."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(ReservationSerializer(reservation).data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        reservation = self.get_object(pk, request.user)
        if reservation is None:
            return Response({"detail": "예약을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        # 취소는 상태 변경(소프트). 명세: 취소 시 해당 예약 삭제 → 실제 삭제 원하면 reservation.delete()
        reservation.status = Reservation.Status.CANCELED
        reservation.save(update_fields=["status"])
        return Response({"detail": "예약이 취소되었습니다."}, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────
# MYPAGE_01(4) - 저장 작품 / 타임라인
# ─────────────────────────────────────────────
from maker.models import Item


class MyItemListView(ListAPIView):
    """MYPAGE_01(4.1, 4.2) - 저장한 노리개 목록. 최신순(타임라인)"""

    permission_classes = [IsAuthenticated]
    serializer_class = ItemListSerializer
    pagination_class = None

    def get_queryset(self):
        return (
            Item.objects.filter(user=self.request.user)
            .select_related("knot", "tassel", "decoration")
            .order_by("-created_at")
        )


class MyItemDetailView(RetrieveAPIView):
    """MYPAGE_01(4.1) - 저장 작품 상세(노리개 디자인)"""

    permission_classes = [IsAuthenticated]
    serializer_class = ItemListSerializer

    def get_queryset(self):
        return Item.objects.filter(user=self.request.user).select_related(
            "knot", "tassel", "decoration"
        )


# ─────────────────────────────────────────────
# MYPAGE_01(5) - 소유 등록
# ─────────────────────────────────────────────
from .models import Ownership


class OwnershipListCreateView(APIView):
    """MYPAGE_01(5.1) - 소유 목록 조회 / 소유 등록"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Ownership.objects.filter(user=request.user).select_related("product").order_by("-created_at")
        return Response(OwnershipSerializer(qs, many=True).data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = OwnershipCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        ownership = serializer.save()
        return Response(OwnershipSerializer(ownership).data, status=status.HTTP_201_CREATED)


# ─────────────────────────────────────────────
# MYPAGE_01(6) - 관심상품(위시리스트)
# ─────────────────────────────────────────────
from .models import Wishlist


class WishlistListCreateView(APIView):
    """MYPAGE_01(6) - 관심 조합 조회 / 등록"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = (
            Wishlist.objects.filter(user=request.user)
            .select_related("knot", "tassel", "decoration")
            .order_by("-created_at")
        )
        return Response(WishlistSerializer(qs, many=True).data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = WishlistCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        wishlist = serializer.save()
        return Response(WishlistSerializer(wishlist).data, status=status.HTTP_201_CREATED)


class WishlistDeleteView(APIView):
    """MYPAGE_01(6) - 관심 조합 삭제"""

    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        wishlist = Wishlist.objects.filter(pk=pk, user=request.user).first()
        if wishlist is None:
            return Response({"detail": "관심 항목을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        wishlist.delete()
        return Response({"detail": "삭제되었습니다."}, status=status.HTTP_200_OK)


from .serializers import PasswordChangeSerializer


class PasswordChangeView(APIView):
    """MYPAGE - 비밀번호 변경"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "비밀번호가 변경되었습니다."},
            status=status.HTTP_200_OK,
        )