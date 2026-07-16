from django.conf import settings


def set_auth_cookies(response, access_token, refresh_token):
    """Set JWT tokens as HttpOnly cookies on the response."""
    jwt_settings = settings.SIMPLE_JWT

    access_lifetime = jwt_settings["ACCESS_TOKEN_LIFETIME"]
    refresh_lifetime = jwt_settings["REFRESH_TOKEN_LIFETIME"]

    cookie_kwargs = {
        "path": jwt_settings.get("AUTH_COOKIE_PATH", "/"),
        "secure": jwt_settings.get("AUTH_COOKIE_SECURE", False),
        "httponly": jwt_settings.get("AUTH_COOKIE_HTTP_ONLY", True),
        "samesite": jwt_settings.get("AUTH_COOKIE_SAMESITE", "Lax"),
    }

    response.set_cookie(
        jwt_settings["AUTH_COOKIE"],
        str(access_token),
        max_age=int(access_lifetime.total_seconds()),
        **cookie_kwargs,
    )

    response.set_cookie(
        jwt_settings["AUTH_COOKIE_REFRESH"],
        str(refresh_token),
        max_age=int(refresh_lifetime.total_seconds()),
        **cookie_kwargs,
    )

    return response


def clear_auth_cookies(response):
    """Clear JWT cookies on logout."""
    jwt_settings = settings.SIMPLE_JWT
    response.delete_cookie(jwt_settings["AUTH_COOKIE"])
    response.delete_cookie(jwt_settings["AUTH_COOKIE_REFRESH"])
    return response