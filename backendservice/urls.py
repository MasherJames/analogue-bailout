from django.urls import path
from backendservice.views import (RegistrationAPIView, LoginAPIView, BitcoinWalletAPIView,
                                  EthereumWalletAPIView, TransactionsAPIView, TransactionStatusAPIView, TransactionHistoryAPIView)


urlpatterns = [
    path("register/", RegistrationAPIView.as_view(), name="register"),
    path("login/", LoginAPIView.as_view(), name="login"),
    path("bitcoin-wallet/", BitcoinWalletAPIView.as_view(), name="bitcoin-wallet"),
    path("ethereum-wallet/", EthereumWalletAPIView.as_view(), name="ethereum-wallet"),
    path("transaction/", TransactionsAPIView.as_view(), name="transaction"),
    path("transaction/<transaction_identifier>/status/", TransactionStatusAPIView.as_view(), name="transaction-status"),
    path("transaction-history/", TransactionHistoryAPIView.as_view(), name="transaction-history"),
]
