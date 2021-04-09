from typing import Dict, Union, List
from django.db import transaction
from django.contrib import auth
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from sentry_sdk import capture_exception


from backendservice.models import User, BitcoinWallet, EthereumWallet, Transaction, TransactionHistory
from utils.validators import validate_required_data, validate_auth_data


class UserRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        extra_kwargs = {"password": {"write_only": True, "min_length": 4}}

        fields = [
            "identifier",
            "name",
            "description",
            "password",
            "email",
            "max_amount_per_transaction",
        ]

    def validate(
        self, data: Dict[str, Union[str, float]]
    ) -> Dict[str, Union[str, float]]:
        """

        :param data: a dictionary with the data required to create a user
        :return: the passed data object after validation
        """

        is_not_input_valid: Union[None, Dict[str, str]] = validate_auth_data(data)

        if is_not_input_valid is not None:
            raise serializers.ValidationError(is_not_input_valid["Message"])

        return data

    def create(
        self, validated_data: Dict[str, Union[float, str]]
    ) -> User:
        """

        :param validated_data: valid data to create a new user
        :return: user
        """

        try:

            with transaction.atomic():
                user: User = User.objects.create_user(**validated_data)
                return user
        except Exception as e:
            # send to sentry
            capture_exception(e)


class UserLoginSerializer(serializers.ModelSerializer):
    email = serializers.CharField(max_length=255)
    password = serializers.CharField(min_length=4, write_only=True)
    identifier = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    max_amount_per_transaction = serializers.CharField(read_only=True)
    tokens = serializers.SerializerMethodField()

    class Meta:
        model = User

        fields = [
            "email",
            "password",
            "identifier",
            "name",
            "description",
            "max_amount_per_transaction",
            "tokens"
        ]

    def get_tokens(self, obj):
        user = User.objects.get(email=obj['email'])

        return {
            'refresh': user.tokens()['refresh'],
            'access': user.tokens()['access']
        }

    def validate(self, data: Dict[str, str]) -> Dict[str, str]:
        """

        :param data: a dictionary with the data required to login
        :return: an existing user
        """
        email: str = data.get("email", None)
        password: str = data.get("password", None)

        is_not_input_valid: Union[None, Dict[str, str]] = validate_auth_data(data)

        if is_not_input_valid is not None:
            raise serializers.ValidationError(is_not_input_valid["Message"])

        user: Union[User, None] = auth.authenticate(email=email, password=password)

        if not user:
            raise AuthenticationFailed("Invalid credetials, try again")
        return {
            'email': user.email,
            'name': user.name,
            'identifier': user.identifier,
            'max_amount_per_transaction': user.max_amount_per_transaction,
            'tokens': user.tokens,
        }


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["identifier", "name", "email", "max_amount_per_transaction"]


class BitcoinWalletSerializer(serializers.ModelSerializer):
    owner = UserSerializer(source='user', read_only=True)

    class Meta:
        model = BitcoinWallet
        extra_kwargs = {"private_key": {"write_only": True}, "user": {"write_only": True}}
        fields = ["identifier", "public_key", "private_key", "balance", "user", "owner"]

    def validate(
        self, data: Dict[str, Union[str, float]]
    ) -> Dict[str, Union[str, float]]:
        """

        :param data: a dictionary with the data required to create a a bitcoin wallet
        :return: the passed data object after validation
        """
        balance = data.get("balance", None)

        if balance and balance < 0:
            raise serializers.ValidationError("Bitcoin Wallet balance can't be negative")
        return data

    def create(
        self, validated_data: Dict[str, Union[float, str]]
    ) -> Dict[str, Union[str, float, Dict]]:
        """

        :param validated_data: valid data to create a bitcoin wallet
        :return: wallet
        """

        try:

            with transaction.atomic():
                bitcoin_wallet: BitcoinWallet = BitcoinWallet.objects.create(**validated_data)
                return bitcoin_wallet
        except Exception as e:
            # send to sentry
            capture_exception(e)


class EthereumWalletSerializer(serializers.ModelSerializer):
    owner = UserSerializer(source='user', read_only=True)

    class Meta:
        model = EthereumWallet
        extra_kwargs = {"private_key": {"write_only": True}, "user": {"write_only": True}}
        fields = ["identifier", "public_key", "private_key", "balance", "user", "owner"]

    def validate(
        self, data: Dict[str, Union[str, float]]
    ) -> Dict[str, Union[str, float]]:
        """

        :param data: a dictionary with the data required to create an ethereum wallet
        :return: the passed data object after validation
        """
        balance = data.get("balance", None)

        if balance and balance < 0:
            raise serializers.ValidationError("Ethereum Wallet balance can't be negative")
        return data

    def create(
        self, validated_data: Dict[str, Union[float, str]]
    ) -> Dict[str, Union[str, float, Dict]]:
        """

        :param validated_data: valid data to create a ethereum wallet
        :return: wallet
        """

        try:

            with transaction.atomic():
                ethereum_wallet: EthereumWallet = EthereumWallet.objects.create(**validated_data)
                return ethereum_wallet
        except Exception as e:
            # send to sentry
            capture_exception(e)


class TransactionsSerializer(serializers.ModelSerializer):

    class Meta:
        model = Transaction
        fields = "__all__"

    def validate(
        self, data: Dict[str, Union[str, float]]
    ) -> Dict[str, Union[str, float]]:
        """

        :param data: a dictionary with the data required to create a transaction
        :return: the passed data object after validation
        """
        amount = data.get("amount", None)
        target_user = data.get("target_user")
        source_user = data.get("source_user")

        if amount and amount < 0:
            raise serializers.ValidationError("Transaction amount can't be negative")

        if target_user.max_amount_per_transaction < amount:
            raise serializers.ValidationError("Transaction amount is greater target user max allowed amount")

        if source_user.max_amount_per_transaction < amount:
            raise serializers.ValidationError("Transaction amount is greater your max allowed amount")

        return data

    def create(
        self, validated_data: Dict[str, Union[float, str]]
    ):
        """

        :param validated_data: valid data to create a transaction
        :return: transaction
        """

        try:

            with transaction.atomic():
                btc_transaction = Transaction.objects.create(**validated_data)
                # record transaction history for the source user
                TransactionHistory.objects.create(user=validated_data["source_user"],
                                                  transaction=btc_transaction)
                # record transaction history for the target user
                TransactionHistory.objects.create(user=validated_data["target_user"],
                                                  transaction=btc_transaction)
                return btc_transaction
        except Exception as e:
            # send to sentry
            capture_exception(e)


class TransactionHistorySerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    transaction = TransactionsSerializer(read_only=True)

    class Meta:
        model = TransactionHistory
        fields = ["identifier", "transaction", "user"]
