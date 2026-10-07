import os
import sys
import time
import secrets
import logging
from datetime import timedelta

sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, current_user

import database as db
from services import UsuarioService, ProdutoService
from utils import (agora, formatar_moeda, formatar_numero, formatar_data, formatar_data_hora,
                   formatar_data_extenso, formatar_quando)
from utils.seguranca import gerar_token_csrf, token_csrf_valido

from routes.auth import bp as auth_bp
from routes.painel import bp as painel_bp
from routes.produtos import bp as produtos_bp
from routes.movimentacoes import bp as movimentacoes_bp
from routes.relatorios import bp as relatorios_bp
from routes.usuarios import bp as usuarios_bp


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("almoxarifado")

# Rotas que podem ser abertas sem login
ROTAS_PUBLICAS = {"auth.login", "auth.cadastro", "auth.primeiro_acesso", "static"}


def aguardar_banco(tentativas=15, espera=2):
    for i in range(tentativas):
        try:
            db.inicializar()
            log.info("Banco conectado e estrutura atualizada.")
            return
        except Exception as e:
            log.warning("Tentativa %s/%s de conectar ao banco: %s", i + 1, tentativas, e)
            time.sleep(espera)
    raise RuntimeError("Não foi possível conectar ao banco.")


def criar_app(inicializar_banco: bool = True) -> Flask:
    app = Flask(__name__)

    chave = os.environ.get("SECRET_KEY")
    if not chave:
        chave = secrets.token_hex(32)
        log.warning("SECRET_KEY não definida: usando uma chave temporária "
                    "(os usuários serão deslogados quando o servidor reiniciar).")
    app.config.update(
        SECRET_KEY=chave,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        REMEMBER_COOKIE_DURATION=timedelta(days=14),
        REMEMBER_COOKIE_HTTPONLY=True,
        REMEMBER_COOKIE_SAMESITE="Lax",
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
        # Nome exibido no logo, no menu e nas abas do navegador
        NOME_APP=os.environ.get("NOME_APP", "Almox+"),
    )

    # ── Login ─────────────────────────────────────────────────────────────────
    login_manager = LoginManager(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Entre com sua conta para continuar."
    login_manager.login_message_category = "info"
    login_manager.session_protection = "basic"

    @login_manager.user_loader
    def carregar_usuario(usuario_id):
        usuario = UsuarioService.buscar_por_id(usuario_id)
        return usuario if usuario and usuario.is_active else None

    # ── Blueprints (cada módulo do sistema) ───────────────────────────────────
    for bp in (auth_bp, painel_bp, produtos_bp, movimentacoes_bp, relatorios_bp, usuarios_bp):
        app.register_blueprint(bp)

    # ── Verificações antes de cada requisição ─────────────────────────────────
    @app.before_request
    def proteger_rotas():
        endpoint = request.endpoint or ""

        if endpoint == "static":
            return None

        if request.method == "POST" and not token_csrf_valido():
            flash("Sua sessão expirou. Confira os dados e tente de novo.", "warning")
            voltar = request.referrer if destino_seguro_ref(request.referrer) else None
            return redirect(voltar or url_for("painel.inicio"))

        # Primeiro acesso: enquanto não houver usuários, só a tela de configuração abre
        if not app.config.get("_CONFIGURADO"):
            if UsuarioService.precisa_configurar():
                if endpoint != "auth.primeiro_acesso":
                    return redirect(url_for("auth.primeiro_acesso"))
                return None
            app.config["_CONFIGURADO"] = True

        if endpoint not in ROTAS_PUBLICAS and not current_user.is_authenticated:
            return login_manager.unauthorized()
        return None

    def destino_seguro_ref(url):
        return bool(url) and url.startswith(request.host_url)

    @app.after_request
    def cabecalhos_seguranca(resposta):
        resposta.headers.setdefault("X-Content-Type-Options", "nosniff")
        resposta.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        resposta.headers.setdefault("Referrer-Policy", "same-origin")
        return resposta

    # ── Variáveis e filtros disponíveis em todos os templates ─────────────────
    @app.context_processor
    def variaveis_globais():
        dados = {"csrf_token": gerar_token_csrf, "agora": agora(),
                 "nome_app": app.config["NOME_APP"]}
        if current_user.is_authenticated:
            try:
                dados["qtd_alertas"] = ProdutoService.contar_estoque_baixo()
                dados["qtd_pendentes"] = UsuarioService.contar_pendentes() if current_user.is_admin else 0
            except Exception:
                dados["qtd_alertas"] = dados["qtd_pendentes"] = 0
        return dados

    app.add_template_filter(formatar_moeda, "moeda")
    app.add_template_filter(formatar_numero, "numero")
    app.add_template_filter(formatar_data, "data")
    app.add_template_filter(formatar_data_hora, "datahora")
    app.add_template_filter(formatar_data_extenso, "extenso")
    app.add_template_filter(formatar_quando, "quando")

    # ── Páginas de erro ───────────────────────────────────────────────────────
    @app.errorhandler(403)
    def acesso_negado(_):
        return render_template("erro.html", codigo=403, titulo="Acesso restrito",
                               mensagem="Esta área é exclusiva para administradores. "
                                        "Peça acesso ao responsável pelo sistema."), 403

    @app.errorhandler(404)
    def nao_encontrado(_):
        return render_template("erro.html", codigo=404, titulo="Página não encontrada",
                               mensagem="O endereço pode ter mudado ou o registro foi removido."), 404

    @app.errorhandler(500)
    def erro_interno(e):
        log.exception("Erro interno: %s", e)
        return render_template("erro.html", codigo=500, titulo="Algo deu errado",
                               mensagem="O erro foi registrado. Tente de novo em alguns instantes."), 500

    if inicializar_banco:
        aguardar_banco()
    return app


app = criar_app(inicializar_banco=os.environ.get("PULAR_INICIALIZACAO_BANCO") != "1")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=os.environ.get("FLASK_DEBUG") == "1")
