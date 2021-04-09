import re
from typing import List, Dict, Union
from rest_framework.validators import ValidationError


def validate_required_data(
    list_of_keys: List[str], data: Dict[str, Union[str, float]]
) -> Dict[str, Union[str, float]]:
    for key in list_of_keys:
        if not data.get(key):
            return {"Message": f"{key} is required"}
    return data


def validate_auth_data(
    data: Dict[str, Union[str, float]]
) -> Dict[str, Union[str, float]]:

    email: str = data.get("email", None)
    password: str = data.get("password", None)
    max_amount_per_transaction: float = data.get("max_amount_per_transaction", None)

    email_regex: str = r"^[^@]+@[^@]+\.[^@]+$"
    password_regex: str = r"^[0-9A-Za-z]{4,}$"

    is_email_valid: bool = re.match(email_regex, email)
    is_password_valid: bool = re.match(password_regex, password)

    if password and not is_password_valid:
        return {
            "Message": "Password should be alphanumeric and not less that 4 characters"
        }

    if email and not is_email_valid:
        return {"Message": "Please enter a valid email"}

    if max_amount_per_transaction and max_amount_per_transaction < 0.0:
        return {"Message": "Amount to transact with should be greater than zero"}
