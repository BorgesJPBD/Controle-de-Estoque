"""Proteções de segurança da aplicação web.

- Token CSRF: todo formulário POST leva um token secreto da sessão, o que
  impede que outro site envie formulários em nome do usuário logado.
- Decorator admin_obrigatorio: restringe rotas ao perfil Administrador.
"""
import hmac
import secrets
from functools import wraps
from urllib.parse import urlparse

from flask import abort, session, request
from flask_login import current_user


CHAVE_CSRF = "_csrf_token"


def gerar_token_csrf() -> str:
    if CHAVE_CSRF not in session:
        session[CHAVE_CSRF] = secrets.token_urlsafe(32)
    return session[CHAVE_CSRF]


def token_csrf_valido() -> bool:
    enviado = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token") or ""
    esperado = session.get(CHAVE_CSRF, "")
    return bool(esperado) and hmac.compare_digest(enviado, esperado)


def admin_obrigatorio(func):
    @wraps(func)
    def protegido(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return func(*args, **kwargs)
    return protegido


def destino_seguro(url: str) -> bool:
    """Aceita só caminhos internos no parâmetro ?next= (evita redirecionamento aberto)."""
    if not url:
        return False
    partes = urlparse(url)
    return not partes.netloc and not partes.scheme and url.startswith("/") and not url.startswith("//")
