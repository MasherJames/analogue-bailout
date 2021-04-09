from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from sentry_sdk import capture_exception


from utils.producer import transaction_producer
from backendservice.serializers import (UserRegisterSerializer, UserLoginSerializer, BitcoinWalletSerializer, EthereumWalletSerializer, TransactionsSerializer, TransactionHistorySerializer)
from backendservice.models import User, BitcoinWallet, EthereumWallet, Transaction, TransactionHistory
from utils.gen_key_sign_verify import GenKeySignAndVerify


class RegistrationAPIView(generics.CreateAPIView):
    serializer_class = UserRegisterSerializer

    def post(self, request):

        user = request.data
        serializer = self.serializer_class(data=user)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        payload = serializer.data

        return Response(payload, status=status.HTTP_201_CREATED)


class LoginAPIView(generics.GenericAPIView):
    serializer_class = UserLoginSerializer

    def post(self, request):

        user_creds = request.data
        serializer = self.serializer_class(data=user_creds)
        serializer.is_valid(raise_exception=True)
        payload = serializer.data

        return Response(payload, status=status.HTTP_200_OK)


class BitcoinWalletAPIView(generics.ListCreateAPIView):
    serializer_class = BitcoinWalletSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.data["user"] = request.user.identifier
        private_key, public_key = GenKeySignAndVerify.generate_keys()
        request.data["private_key"] = private_key
        request.data["public_key"] = public_key
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        payload = serializer.data

        return Response(payload, status=status.HTTP_201_CREATED)

    def list(self, request):
        queryset = BitcoinWallet.objects.all()
        serializer = BitcoinWalletSerializer(queryset, many=True)
        payload = serializer.data

        return Response(payload, status=status.HTTP_200_OK)


class EthereumWalletAPIView(generics.ListCreateAPIView):
    serializer_class = EthereumWalletSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.data["user"] = request.user.identifier
        private_key, public_key = GenKeySignAndVerify.generate_keys()
        request.data["private_key"] = private_key
        request.data["public_key"] = public_key
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        payload = serializer.data

        return Response(payload, status=status.HTTP_201_CREATED)

    def list(self, request):
        queryset = EthereumWallet.objects.all()
        serializer = EthereumWalletSerializer(queryset, many=True)
        payload = serializer.data

        return Response(payload, status=status.HTTP_200_OK)


class TransactionsAPIView(generics.ListCreateAPIView):
    serializer_class = TransactionsSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # target user
        target_user_pk = request.data["target_user"]
        currency_type = request.data["currency_type"]

        currency_types = {
            "Bitcoin": BitcoinWallet,
            "Ethereum": EthereumWallet
        }

        if currency_type not in currency_types:
            return Response(
                {"Message": "Crypto wallet does not exist, use Bitcoin or Ethereum"},
                status=status.HTTP_404_NOT_FOUND
            )

        WalletType = currency_types[currency_type]

        try:
            User.objects.get(pk=target_user_pk)
        except User.DoesNotExist:
            raise NotFound("Target user does not exist")

        try:
            WalletType.objects.get(user=target_user_pk)
        except WalletType.DoesNotExist:
            raise NotFound("Target user does not have a wallet")

        # source user
        source_user_pk = request.user.identifier
        request.data["source_user"] = source_user_pk
        source_user_wallet = None
        try:
            source_user_wallet = WalletType.objects.get(user=source_user_pk)
        except WalletType.DoesNotExist:
            raise NotFound("You don't have a wallet, please create one")

        private_key = source_user_wallet.private_key
        signature = GenKeySignAndVerify.sign_transaction(private_key, request.data)
        request.data["signature"] = signature

        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        payload = serializer.data

        payload["source_user"] = str(payload["source_user"])
        payload["target_user"] = str(payload["target_user"])

        # add the transaction to rabbitmq for processing
        transaction_producer(payload)

        return Response(payload, status=status.HTTP_201_CREATED)

    def list(self, request):
        queryset = Transaction.objects.all()
        serializer = TransactionsSerializer(queryset, many=True)
        payload = serializer.data

        return Response(payload, status=status.HTTP_200_OK)


class TransactionStatusAPIView(generics.ListAPIView):
    serializer_class = TransactionsSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, transaction_identifier):
        try:
            transaction = Transaction.objects.get(identifier=transaction_identifier)
            payload = {"identifier": transaction.identifier, "status": transaction.state}

            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            capture_exception(e)


class TransactionHistoryAPIView(generics.ListAPIView):
    serializer_class = TransactionHistorySerializer
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user.identifier
        try:
            queryset = TransactionHistory.objects.filter(user=user)
            serializer = TransactionHistorySerializer(queryset, many=True)

            payload = serializer.data

            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            capture_exception(e)
