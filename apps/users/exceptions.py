import logging
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler
from rest_framework.exceptions import (
    ValidationError,
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
)

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom DRF exception handler.
    Returns consistent JSON error responses.
    Never exposes stack traces or internal details in production.
    """
    # Convert Django ValidationError to DRF ValidationError
    if isinstance(exc, DjangoValidationError):
        exc = ValidationError(detail=exc.messages)

    response = exception_handler(exc, context)

    if response is not None:
        error_payload = {
            "status": "error",
            "code": response.status_code,
            "message": _get_error_message(exc, response),
            "errors": response.data if isinstance(response.data, dict) else {"detail": response.data},
        }
        response.data = error_payload

    return response


def _get_error_message(exc, response):
    if isinstance(exc, NotAuthenticated):
        return "Authentication is required to access this resource."
    if isinstance(exc, AuthenticationFailed):
        return "Invalid credentials. Please check your email and password."
    if isinstance(exc, PermissionDenied):
        return "You do not have permission to perform this action."
    if isinstance(exc, ValidationError):
        return "Please correct the errors below and try again."
    if response.status_code == 404:
        return "The requested resource was not found."
    if response.status_code == 405:
        return "This request method is not allowed."
    if response.status_code >= 500:
        return "An unexpected server error occurred. Our team has been notified."
    return str(getattr(exc, "detail", "An error occurred."))