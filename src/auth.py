"""
PV AI Workbench — Authentication Gate

Supports two parallel auth methods:
  1. Local username/password via streamlit-authenticator (always available)
  2. Google / GitHub OAuth via Streamlit's built-in st.login() (when configured)

Call require_auth() at the top of every page before rendering any content.
Call auth_sidebar() in the sidebar to show user info and a logout button.
"""

from __future__ import annotations
import streamlit as st
import streamlit_authenticator as stauth
from streamlit_authenticator.utilities.exceptions import LoginError


# ── Build authenticator from secrets ─────────────────────────────────────────

def _build_authenticator() -> stauth.Authenticate:
    creds_raw = st.secrets.get("credentials", {})
    usernames  = creds_raw.get("usernames", {})
    # secrets.toml nested tables come through as dicts
    credentials = {"usernames": {k: dict(v) for k, v in usernames.items()}}
    cookie      = st.secrets.get("cookie", {})
    return stauth.Authenticate(
        credentials,
        cookie.get("name", "pv_workbench_auth"),
        cookie.get("key", "fallback_key_change_me"),
        cookie_expiry_days=int(cookie.get("expiry_days", 30)),
        auto_hash=False,
    )


def _get_authenticator() -> stauth.Authenticate:
    if "authenticator" not in st.session_state:
        st.session_state.authenticator = _build_authenticator()
    return st.session_state.authenticator


# ── OAuth helpers ─────────────────────────────────────────────────────────────

def _provider_configured(provider: str) -> bool:
    try:
        cfg = st.secrets.get("auth", {}).get(provider, {})
        return bool(cfg.get("client_id", "").strip())
    except Exception:
        return False


def _oauth_user_logged_in() -> bool:
    try:
        return bool(st.user.is_logged_in)
    except Exception:
        return False


# ── Public interface ──────────────────────────────────────────────────────────

def is_authenticated() -> bool:
    """True if user is authenticated by any method."""
    if _oauth_user_logged_in():
        return True
    return bool(st.session_state.get("authentication_status"))


def current_user() -> dict:
    """Return display info for the authenticated user."""
    if _oauth_user_logged_in():
        try:
            return {
                "name":     getattr(st.user, "name", "") or st.user.email,
                "email":    st.user.email,
                "method":   "oauth",
            }
        except Exception:
            return {"name": "OAuth User", "email": "", "method": "oauth"}
    return {
        "name":   st.session_state.get("name", "User"),
        "email":  "",
        "method": "local",
    }


def require_auth() -> None:
    """
    Call at the top of every page.
    Renders the login screen and calls st.stop() if not authenticated.
    Returns normally when the user is authenticated.
    """
    if is_authenticated():
        return

    # ── Login page ────────────────────────────────────────────────────────────
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] {display: none;}
        .block-container {max-width: 480px; margin: 60px auto;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("## 🔬 PV AI Workbench")
    st.caption("Pharmacovigilance Signal Intelligence — Restricted Access")
    st.markdown("---")

    google_ok = _provider_configured("google")
    github_ok = _provider_configured("github")
    has_oauth = google_ok or github_ok

    if has_oauth:
        tab_local, tab_oauth = st.tabs(["Password", "Single Sign-On"])
    else:
        tab_local = st.container()

    # ── Local password tab ────────────────────────────────────────────────────
    with tab_local:
        authenticator = _get_authenticator()
        try:
            authenticator.login(
                location="main",
                fields={
                    "Form name": "Sign in",
                    "Username":  "Username",
                    "Password":  "Password",
                    "Login":     "Sign in",
                },
            )
        except LoginError:
            # Stale or invalid cookie — clear session and fall through to form
            for key in ("authentication_status", "name", "username", "email", "authenticator"):
                st.session_state.pop(key, None)
        auth_status = st.session_state.get("authentication_status")
        if auth_status is False:
            st.error("Incorrect username or password.")
        elif auth_status is None:
            st.caption("Enter your credentials above.")

    # ── OAuth tab ─────────────────────────────────────────────────────────────
    if has_oauth:
        with tab_oauth:
            if google_ok:
                if st.button("Sign in with Google", use_container_width=True, type="primary"):
                    st.login("google")
            if github_ok:
                if st.button("Sign in with GitHub", use_container_width=True):
                    st.login("github")
            st.caption(
                "You will be redirected to your identity provider and returned here after sign-in."
            )

    st.stop()


def auth_sidebar() -> None:
    """
    Call inside a `with st.sidebar:` block on every page.
    Shows the logged-in user and a logout button.
    """
    if not is_authenticated():
        return

    user = current_user()
    st.markdown("---")
    st.markdown(f"**{user['name']}**")
    if user["email"]:
        st.caption(user["email"])
    st.caption(f"Auth: {user['method']}")

    if user["method"] == "oauth":
        if st.button("Sign out", key="logout_oauth"):
            st.logout()
    else:
        authenticator = _get_authenticator()
        authenticator.logout(button_name="Sign out", location="sidebar", key="logout_local")
