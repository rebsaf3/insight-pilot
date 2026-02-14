"""Browser cookie helpers for persistent sessions in Streamlit.

Streamlit's ``st.session_state`` is in-memory only — it is lost on page
refresh because a new WebSocket connection is established. To persist login
across refreshes we store the session token in an HTTP-only-like browser
cookie using a tiny JavaScript snippet injected via ``st.components.v1.html``.

Flow:
  1. On login  → ``set_session_cookie(token)`` writes the cookie.
  2. On reload → ``get_session_cookie()`` reads it back via ``st.query_params``.
  3. On logout → ``clear_session_cookie()`` deletes the cookie.

We use a two-step mechanism:
  - A JS snippet sets/reads/deletes a cookie named ``_ip_session``.
  - On page load the JS reads the cookie and, if present AND the Streamlit
    session state is empty, writes it into ``st.query_params`` so Python
    can pick it up synchronously on the very first run.
"""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from config.settings import SESSION_EXPIRY_DAYS

COOKIE_NAME = "_ip_session"
_COOKIE_MAX_AGE = SESSION_EXPIRY_DAYS * 86400  # seconds


def set_session_cookie(token: str) -> None:
    """Set a browser cookie with the session token.

    Injects a tiny invisible iframe that executes JS to write the cookie.
    Must be called once right after successful login.
    """
    js = f"""
    <script>
    document.cookie = "{COOKIE_NAME}={token}; path=/; max-age={_COOKIE_MAX_AGE}; SameSite=Lax";
    </script>
    """
    components.html(js, height=0, width=0)


def clear_session_cookie() -> None:
    """Delete the session cookie from the browser."""
    js = f"""
    <script>
    document.cookie = "{COOKIE_NAME}=; path=/; max-age=0; SameSite=Lax";
    </script>
    """
    components.html(js, height=0, width=0)


def restore_session_from_cookie() -> str | None:
    """Try to read the session token from the browser cookie.

    This works by injecting JS that reads the cookie and posts the value
    back into the Streamlit URL as a query parameter ``_tkn``. On the
    *next* rerun Python can read ``st.query_params["_tkn"]`` synchronously.

    Returns the token string if found, else None.
    """
    # Step 1: check if the token was already pushed into query_params
    token = st.query_params.get("_tkn")
    if token:
        # Clean up the URL so the token isn't visible
        st.query_params.clear()
        return token

    # Step 2: inject JS that reads the cookie and redirects with ?_tkn=…
    # The JS only fires if the cookie exists and we don't already have
    # a session in Streamlit (avoids infinite redirect loops).
    js = f"""
    <script>
    (function() {{
        // Only run if Streamlit session state is empty (no token in URL yet)
        var params = new URLSearchParams(window.location.search);
        if (params.has('_tkn')) return;

        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {{
            var c = cookies[i].trim();
            if (c.startsWith('{COOKIE_NAME}=')) {{
                var token = c.substring({len(COOKIE_NAME) + 1});
                if (token) {{
                    // Push token into query params and reload
                    var url = new URL(window.parent.location.href);
                    url.searchParams.set('_tkn', token);
                    window.parent.location.href = url.toString();
                }}
                break;
            }}
        }}
    }})();
    </script>
    """
    components.html(js, height=0, width=0)
    return None
