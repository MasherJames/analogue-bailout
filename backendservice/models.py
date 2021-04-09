import uuid
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
)
from django.core.validators import MinValueValidator
from rest_framework_simplejwt.tokens import RefreshToken


class UserManager(BaseUserManager):
    def create_user(
        self, name, description, email, max_amount_per_transaction, password=None
    ):
        if name is None:
            raise TypeError("Users should have a name")
        if email is None:
            raise TypeError("Users should have an email")

        if description is None:
            raise TypeError("Users should have an description")

        if max_amount_per_transaction is None:
            raise TypeError(
                "Users should have the maximum amount they can transact with"
            )

        user = self.model(
            name=name,
            description=description,
            email=self.normalize_email(email),
            max_amount_per_transaction=max_amount_per_transaction,
        )
        user.set_password(password)
        user.save()
        return user


class User(AbstractBaseUser):
    identifier = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=1000)
    email = models.CharField(
        max_length=255,
        unique=True,
        error_messages={"unique": "User with that email already exists"},
    )
    max_amount_per_transaction = models.DecimalField(
        validators=[MinValueValidator(0)], max_digits=26, decimal_places=18
    )

    USERNAME_FIELD = "email"

    objects = UserManager()

    def __str__(self) -> str:
        return self.name

    def tokens(self):
        refresh = RefreshToken.for_user(self)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token)
        }


class BitcoinWallet(models.Model):
    identifier = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="user_owner")
    private_key = models.CharField(max_length=64)
    public_key = models.CharField(max_length=255)
    balance = models.DecimalField(
        validators=[MinValueValidator(0)], default=0.0, max_digits=16, decimal_places=8
    )

    def __str__(self) -> str:
        return self.public_key


class EthereumWallet(models.Model):
    identifier = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    private_key = models.CharField(max_length=64)
    public_key = models.CharField(max_length=255)
    balance = models.DecimalField(
        validators=[MinValueValidator(0)], default=0.0, max_digits=26, decimal_places=18
    )

    def __str__(self) -> str:
        return self.public_key


class Transaction(models.Model):

    CurrencyType = [
        ("Bitcoin", "Bitcoin"),
        ("Ethereum", "Ethereum"),
    ]

    State = [
        ("Unconfirmed", "Unconfirmed"),
        ("Confirmed", "Confirmed"),
        ("Rejected", "Rejected"),
    ]

    identifier = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    amount = models.DecimalField(
        validators=[MinValueValidator(0)], max_digits=26, decimal_places=18
    )
    currency_type = models.CharField(max_length=8, choices=CurrencyType)
    source_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="source"
    )
    target_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="target"
    )
    signature = models.CharField(max_length=255)
    created = models.DateTimeField(default=timezone.now)
    processed = models.DateTimeField(null=True)
    state = models.CharField(max_length=11, choices=State, default="Unconfirmed")

    def __str__(self) -> str:
        return self.identifier


class TransactionHistory(models.Model):
    identifier = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user")
    transaction = models.ForeignKey(
        Transaction, on_delete=models.CASCADE, related_name="transaction"
    )

    def __str__(self) -> str:
        return self.identifier
