from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user

from models import PERFIS, STATUS
from services import UsuarioService
from utils import SETORES_HOSPITALARES
from utils.seguranca import admin_obrigatorio


bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")


@bp.before_request
@admin_obrigatorio
def somente_admin():
    """Todas as rotas deste módulo são exclusivas do administrador."""
    return None


@bp.route("/")
def lista():
    usuarios = UsuarioService.listar()
    pendentes = [u for u in usuarios if u.status == "pendente"]
    demais = [u for u in usuarios if u.status != "pendente"]
    return render_template("usuarios/lista.html", pendentes=pendentes, usuarios=demais,
                           perfis=PERFIS)


def _form(usuario=None, erro=None, dados=None):
    if dados is None:
        dados = usuario.to_dict() if usuario else {"perfil": "almoxarife", "status": "ativo"}
    return render_template("usuarios/form.html", usuario=usuario, dados=dados, erro=erro,
                           perfis=PERFIS, status=STATUS, setores=SETORES_HOSPITALARES)


@bp.route("/novo", methods=["GET", "POST"])
def novo():
    if request.method == "POST":
        try:
            usuario = UsuarioService.criar_por_admin(
                nome=request.form.get("nome", ""),
                email=request.form.get("email", ""),
                setor=request.form.get("setor", ""),
                perfil=request.form.get("perfil", "almoxarife"),
                senha=request.form.get("senha", ""),
                confirmacao=request.form.get("confirmacao", ""),
            )
            flash(f"Conta de {usuario.nome} criada. Envie a senha inicial para a pessoa.", "success")
            return redirect(url_for("usuarios.lista"))
        except ValueError as e:
            return _form(erro=str(e), dados=request.form)
    return _form()


@bp.route("/<int:usuario_id>/editar", methods=["GET", "POST"])
def editar(usuario_id):
    usuario = UsuarioService.buscar_por_id(usuario_id)
    if not usuario:
        flash("Usuário não encontrado.", "warning")
        return redirect(url_for("usuarios.lista"))
    if request.method == "POST":
        try:
            usuario = UsuarioService.editar_por_admin(
                usuario_id,
                nome=request.form.get("nome", ""),
                email=request.form.get("email", ""),
                setor=request.form.get("setor", ""),
                perfil=request.form.get("perfil", usuario.perfil),
                status=request.form.get("status", usuario.status),
                nova_senha=request.form.get("nova_senha", ""),
                admin_id=current_user.id,
            )
            flash(f"Alterações em {usuario.nome} salvas.", "success")
            return redirect(url_for("usuarios.lista"))
        except ValueError as e:
            return _form(usuario, erro=str(e), dados=request.form)
    return _form(usuario)


@bp.route("/<int:usuario_id>/aprovar", methods=["POST"])
def aprovar(usuario_id):
    try:
        usuario = UsuarioService.aprovar(usuario_id, request.form.get("perfil", "almoxarife"))
        flash(f"Acesso de {usuario.nome} aprovado como {usuario.perfil_nome}.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for("usuarios.lista"))


@bp.route("/<int:usuario_id>/recusar", methods=["POST"])
def recusar(usuario_id):
    try:
        usuario = UsuarioService.recusar(usuario_id)
        flash(f"Solicitação de {usuario.nome} recusada.", "info")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for("usuarios.lista"))


@bp.route("/<int:usuario_id>/status", methods=["POST"])
def alternar_status(usuario_id):
    try:
        usuario = UsuarioService.alternar_status(usuario_id, current_user.id)
        texto = "reativada" if usuario.status == "ativo" else "desativada"
        flash(f"Conta de {usuario.nome} {texto}.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for("usuarios.lista"))
