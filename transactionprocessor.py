import os
import pika
import json
import django
import decimal
import logging
# create logger
logger = logging.getLogger("Transaction Processor")
# set logging level to info
logger.setLevel(logging.INFO)

# create formatter
formatter = logging.Formatter('%(asctime)s - %(message)s')

# create a file handler
file_handler = logging.FileHandler('transactions.log')
# sets the file format
file_handler.setFormatter(formatter)

# add file handler to the logger
logger.addHandler(file_handler)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "analoguebailout.settings")
django.setup()

from django.utils import timezone
from django.db import transaction as db_transaction
from sentry_sdk import capture_exception
from backendservice.models import User, BitcoinWallet, EthereumWallet, Transaction
from utils.gen_key_sign_verify import GenKeySignAndVerify


class TransactionProcessor:

    def __init__(self):
        self.currency_type = {
            "Bitcoin": BitcoinWallet,
            "Ethereum": EthereumWallet
        }

        self.currency_type_abb = {
            "Bitcoin": "BTC",
            "Ethereum": "ETH"
        }

    def processor(self, body):

        transaction_info = json.loads(body)
        currency_type = transaction_info["currency_type"]
        source_user_uid = transaction_info['source_user']
        target_user_uid = transaction_info['target_user']
        signature = transaction_info['signature']
        transaction_amount = float(transaction_info['amount'])

        currency_type_abb = self.currency_type_abb[currency_type]
        WalletType = self.currency_type[currency_type]

        try:
            # get the source wallet
            source_wallet = WalletType.objects.get(user=source_user_uid)
            # get the target wallet
            target_user_wallet = WalletType.objects.get(user=target_user_uid)
            # get the transaction
            transaction = Transaction.objects.get(identifier=transaction_info["identifier"])
            # get the private key to verify the transaction
            signed_data = {
                "target_user": target_user_uid,
                "currency_type": currency_type,
                "amount": transaction_amount,
                "source_user": source_user_uid,
            }
            is_transaction_valid = GenKeySignAndVerify.verify_transaction_signature(
                source_wallet.public_key, signature, signed_data)

            # if transaction is valid
            if is_transaction_valid:

                if source_user_uid == target_user_uid:
                    with db_transaction.atomic():
                        transaction.state = "Rejected"
                        transaction.processed = timezone.now()
                        transaction.save()
                    logger.info(f'{currency_type} transaction of value {transaction_amount} {currency_type_abb} from {source_user_uid} to {target_user_uid}  rejected: Cannot send coins to your own account')
                else:
                    # check the ballance
                    source_wallet_balance = source_wallet.balance

                    if source_wallet_balance > transaction_amount:
                        with db_transaction.atomic():
                            # increase balance to the target
                            target_user_wallet.balance = target_user_wallet.balance + decimal.Decimal(transaction_amount)
                            target_user_wallet.save()
                            # decrese balance from the source
                            source_wallet.balance = source_wallet.balance - decimal.Decimal(transaction_amount)
                            source_wallet.save()
                            # update transaction state and time
                            transaction.state = "Confirmed"
                            transaction.processed = timezone.now()
                            transaction.save()
                        logger.info(f'{currency_type} transaction of value {transaction_amount} {currency_type_abb} from {source_user_uid} to {target_user_uid}  successful')
                    else:
                        with db_transaction.atomic():
                            transaction.state = "Rejected"
                            transaction.processed = timezone.now()
                            transaction.save()
                        logger.info(f'{currency_type} transaction of value {transaction_amount} {currency_type_abb} from {source_user_uid} to {target_user_uid}  rejected: Balance to low to complete transaction')
            else:
                with db_transaction.atomic():
                    transaction.state = "Rejected"
                    transaction.processed = timezone.now()
                    transaction.save()
                logger.info(f'{currency_type} transaction of value {transaction_amount} {currency_type_abb} from {source_user_uid} to {target_user_uid}  rejected: Transaction is in valid')
        except Exception as e:
            capture_exception(e)

    def consumer(self):
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='localhost'))

        channel = connection.channel()

        channel.queue_declare(queue='transactions', durable=True)

        print(' [*] Waiting for logs. To exit press CTRL+C')

        def callback(ch, method, properties, body):
            self.processor(body)
            ch.basic_ack(delivery_tag=method.delivery_tag)

        channel.basic_consume(
            queue="transactions", on_message_callback=callback)

        channel.start_consuming()


if __name__ == "__main__":
    TransactionProcessor().consumer()
