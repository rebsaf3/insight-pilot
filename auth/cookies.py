"""Browser cookie helpers for persistent sessions in Streamlit.

Streamlit's ``st.session_state`` is in-memory only — it is lost on page
refresh because a new WebSocket connection is established. To persist login
across refreshes we store the session token in a browser cookie.

**Writing** uses a tiny JS snippet injected via ``st.components.v1.html``
(Streamlit has no server-side cookie-write API).

**Reading** uses ``st.context.cookies`` (available since Streamlit 1.37) which
reads the HTTP ``Cookie`` header on the server side — no JS round-trip
required.  This eliminates the fragile JS-redirect approach that caused
Streamlit to occasionally fall back to directory-based page routing.
"""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from config.settings import SESSION_EXPIRY_DAYS

COOKIE_NAME = "_ip_session"
_COOKIE_MAX_AGE = SESSION_EXPIRY_DAYS * 86400  # seconds


def set_session_cookie(token: str) -> None:
    """Set a browser cookie with the session token.

    Injects a tiny invisible iframe that executes JS to write the cookie on
    the parent document (the main Streamlit page). Must be called once right
    after successful login.
    """
    js = f"""
    <script>
    (function() {{
        var cookieStr = "{COOKIE_NAME}={token}; path=/; max-age={_COOKIE_MAX_AGE}; SameSite=Lax";
        try {{ parent.document.cookie = cookieStr; }} catch(e) {{}}
        document.cookie = cookieStr;
    }})();
    </script>
    """
    components.html(js, height=0, width=0)


def clear_session_cookie() -> None:
    """Delete the session cookie from the browser."""
    js = f"""
    <script>
    (function() {{
        var cookieStr = "{COOKIE_NAME}=; path=/; max-age=0; SameSite=Lax";
        try {{ parent.document.cookie = cookieStr; }} catch(e) {{}}
        document.cookie = cookieStr;
    }})();
    </script>
    """
    components.html(js, height=0, width=0)


def restore_session_from_cookie() -> str | None:
    """Read the session token from the browser cookie (server-side).

    Uses ``st.context.cookies`` to read the HTTP Cookie header directly
    on the server — no JavaScript redirect needed.  Returns the token
    string if present and non-empty, else ``None``.
    """
    try:
        token = st.context.cookies.get(COOKIE_NAME)
        if token:
            return token
    except Exception:
        # st.context.cookies may not be available in very old Streamlit
        # or during certain lifecycle phases — fail gracefully.
        pass

    return None
