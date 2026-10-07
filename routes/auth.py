from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user

from services import UsuarioService
from utils import SETORES_HOSPITALARES
from utils.seguranca import destino_seguro


bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("painel.inicio"))

    erro = None
    email = request.form.get("email", "")
    if request.method == "POST":
        try:
            usuario = UsuarioService.autenticar(email, request.form.get("senha", ""))
            login_user(usuario, remember=bool(request.form.get("lembrar")))
            destino = request.args.get("next")
            return redirect(destino if destino_seguro(destino) else url_for("painel.inicio"))
        except ValueError as e:
            erro = str(e)
    return render_template("auth/login.html", erro=erro, email=email)


@bp.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if current_user.is_authenticated:
        return redirect(url_for("painel.inicio"))

    erro = None
    if request.method == "POST":
        try:
            UsuarioService.solicitar_acesso(
                nome=request.form.get("nome", ""),
                email=request.form.get("email", ""),
                setor=request.form.get("setor", ""),
                senha=request.form.get("senha", ""),
                confirmacao=request.form.get("confirmacao", ""),
            )
            return render_template("auth/cadastro_enviado.html",
                                   nome=request.form.get("nome", "").split()[0])
        except ValueError as e:
            erro = str(e)
    return render_template("auth/cadastro.html", erro=erro, dados=request.form,
                           setores=SETORES_HOSPITALARES)


@bp.route("/primeiro-acesso", methods=["GET", "POST"])
def primeiro_acesso():
    if not UsuarioService.precisa_configurar():
        return redirect(url_for("auth.login"))

    erro = None
    if request.method == "POST":
        try:
            usuario = UsuarioService.criar_primeiro_admin(
                nome=request.form.get("nome", ""),
                email=request.form.get("email", ""),
                senha=request.form.get("senha", ""),
                confirmacao=request.form.get("confirmacao", ""),
            )
            login_user(usuario)
            flash("Conta de administrador criada. Bem-vindo ao sistema!", "success")
            return redirect(url_for("painel.inicio"))
        except ValueError as e:
            erro = str(e)
    return render_template("auth/primeiro_acesso.html", erro=erro, dados=request.form)


@bp.route("/sair", methods=["POST"])
def sair():
    logout_user()
    flash("Você saiu do sistema.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/perfil", methods=["GET", "POST"])
def perfil():
    erro_dados = erro_senha = None
    if request.method == "POST":
        acao = request.form.get("acao")
        try:
            if acao == "dados":
                UsuarioService.atualizar_dados(current_user.id, request.form.get("nome", ""),
                                               request.form.get("setor", ""))
                flash("Dados atualizados.", "success")
            elif acao == "senha":
                UsuarioService.alterar_senha(
                    current_user.id, request.form.get("senha_atual", ""),
                    request.form.get("nova_senha", ""), request.form.get("confirmacao", ""),
                )
                flash("Senha alterada.", "success")
            return redirect(url_for("auth.perfil"))
        except ValueError as e:
            if acao == "senha":
                erro_senha = str(e)
            else:
                erro_dados = str(e)
    return render_template("auth/perfil.html", erro_dados=erro_dados, erro_senha=erro_senha,
                           setores=SETORES_HOSPITALARES)
