import json
from uuid import UUID
from ecdsa import SigningKey, VerifyingKey
from sentry_sdk import capture_exception


class GenKeySignAndVerify:

    @staticmethod
    def generate_keys():
        try:
            # uses NIST192p as the curve
            private_key = SigningKey.generate()
            public_key = private_key.verifying_key

            private_key_string = private_key.to_string().hex()
            public_key_string = public_key.to_string().hex()

            return private_key_string, public_key_string
        except Exception as e:
            capture_exception(e)

    @staticmethod
    def format_sig_data(data):
        source = data["source_user"]
        target = data["target_user"]
        currency_type = data["currency_type"]
        amount = data["amount"]

        return f'{source}-{target}-{currency_type}-{amount}'

    @staticmethod
    def sign_transaction(private_key_hex, data):
        try:

            signature_data = GenKeySignAndVerify.format_sig_data(data)

            data_in_byte_str = signature_data.encode('utf-8')
            # convert hex to by string
            private_key_bytes = bytes.fromhex(private_key_hex)
            # get the privatekey from the byte string vesrison
            private_key = SigningKey.from_string(private_key_bytes)
            signature = private_key.sign(data_in_byte_str)

            return signature.hex()
        except Exception as e:
            capture_exception(e)

    @staticmethod
    def verify_transaction_signature(public_key_hex, signature_hex, data):

        public_key_bytes = bytes.fromhex(public_key_hex)
        verifying_key = VerifyingKey.from_string(public_key_bytes)
        signature = bytes.fromhex(signature_hex)
        signature_data = GenKeySignAndVerify.format_sig_data(data)
        data_in_byte_str = signature_data.encode('utf-8')
        try:
            return verifying_key.verify(signature, data_in_byte_str)
        except Exception as e:
            capture_exception(e)
