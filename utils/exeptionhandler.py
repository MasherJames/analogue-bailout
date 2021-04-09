from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):

    exception_class_key_with_handlers = {
        "NotAuthenticated": _handle_authentication_error,
    }

    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # Now add the HTTP status code to the response.
    if response is not None:
        response.data["status_code"] = response.status_code

    # thrown exception class
    exception_class = exc.__class__.__name__

    if exception_class in exception_class_key_with_handlers:
        handler = exception_class_key_with_handlers[exception_class]
        return handler(exc, context, response)
    return response


def _handle_authentication_error(exc, context, response):
    response.data["error"] = "You must be authenticated"
    return response
