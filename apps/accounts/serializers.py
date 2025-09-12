# apps/accounts/serializers.py
from rest_framework import serializers

from apps.users.models import User
from .models import VerificationCode


# ============================
# Register flow
# ============================
class RegisterStartSerializer(serializers.Serializer):
    fullname = serializers.CharField(max_length=100)
    phone_number = serializers.CharField(max_length=20)
    role = serializers.ChoiceField(
        choices=[("student", "student"), ("teacher", "teacher")]
    )
    telegram_username = serializers.CharField(
        max_length=50, required=False, allow_blank=True
    )

    def validate(self, attrs):
        # Telefon unikal bo‘lishi kerak
        phone = attrs["phone_number"]
        if User.objects.filter(phone_number=phone).exists():
            raise serializers.ValidationError(
                {"phone_number": "This phone number is already registered."}
            )
        return attrs

    def create(self, validated_data):
        # UserManager ichidagi qo‘shimcha tekshiruvlardan qayta foydalanamiz
        return User.objects.create_user(**validated_data)


class RegisterVerifySerializer(serializers.Serializer):
    """
    Bot yuborgan register-purpose OTP ni tekshiradi.
    Muvaffaqiyatli bo‘lsa, foydalanuvchi telgramini bind qiladi.
    """

    code = serializers.CharField(max_length=6)
    phone_number = serializers.CharField(max_length=20)

    # Register verify uchun: ikkidan KAMIDA BITTASI kerak
    telegram_id = serializers.IntegerField(required=False)
    telegram_username = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        t_id = attrs.get("telegram_id")
        t_username = attrs.get("telegram_username")
        if not t_id and not t_username:
            raise serializers.ValidationError(
                "telegram_id yoki telegram_username talab qilinadi."
            )

        code = attrs["code"]
        phone = attrs["phone_number"]

        try:
            user = User.objects.get(phone_number=phone)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")

        vc = VerificationCode.objects.latest_alive_for(
            telegram_id=t_id,
            telegram_username=t_username,
            purpose=VerificationCode.Purpose.REGISTER,
        )
        if not vc or not vc.is_valid(code):
            raise serializers.ValidationError("Invalid or expired code.")

        # Boshqa userga ulangan telegram_id bo‘lsa bloklaymiz
        if t_id and User.objects.filter(telegram_id=t_id).exclude(id=user.id).exists():
            raise serializers.ValidationError(
                "This Telegram is already bound to another user."
            )

        attrs["user"] = user
        attrs["vc"] = vc
        return attrs

    def create(self, validated_data):
        user: User = validated_data["user"]
        vc: VerificationCode = validated_data["vc"]

        # Binding
        if vc.telegram_id:
            user.telegram_id = vc.telegram_id
        if vc.telegram_username and not user.telegram_username:
            user.telegram_username = vc.telegram_username
        user.save(update_fields=["telegram_id", "telegram_username", "updated_at"])

        vc.consume()
        return user


# ============================
# Login flow (FAQAT telegram_id)
# ============================
class LoginVerifySerializer(serializers.Serializer):
    """
    Login faqat Telegram OTP + telegram_id bilan.
    """

    code = serializers.CharField(max_length=6)
    telegram_id = serializers.IntegerField()  # <-- majburiy, username endi yo‘q

    def validate(self, attrs):
        t_id = attrs["telegram_id"]
        code = attrs["code"]

        vc = VerificationCode.objects.latest_alive_for(
            telegram_id=t_id,
            telegram_username=None,  # username ishlatilmaydi
            purpose=VerificationCode.Purpose.LOGIN,
        )
        if not vc or not vc.is_valid(code):
            raise serializers.ValidationError("Invalid or expired code.")

        user = User.objects.filter(telegram_id=t_id).first()
        if not user:
            raise serializers.ValidationError("User is not linked to this Telegram ID.")

        attrs["user"] = user
        attrs["vc"] = vc
        return attrs

    def create(self, validated_data):
        vc: VerificationCode = validated_data["vc"]
        vc.consume()
        return validated_data["user"]


# ============================
# OTP ingest (Bot → Backend)
# ============================
class OtpIngestSerializer(serializers.Serializer):
    """
    Telegram bot OTP ni backendga push qiladi.
    2 daqiqa amal qiladi (manager.issue(..., ttl_minutes=2)).
    """

    telegram_id = serializers.IntegerField()
    telegram_username = serializers.CharField(required=False, allow_blank=True)
    code = serializers.CharField(max_length=6)
    purpose = serializers.ChoiceField(choices=VerificationCode.Purpose.choices)

    def validate_code(self, v):
        if len(v) != 6 or not v.isdigit():
            raise serializers.ValidationError("Code must be 6 digits.")
        return v

    def create(self, validated_data):
        return VerificationCode.objects.issue(**validated_data, ttl_minutes=2)
