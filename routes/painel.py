from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import current_user

from services import PainelService, saudacao
from utils import agora
from utils.seguranca import admin_obrigatorio
from database import demo


bp = Blueprint("painel", __name__)


@bp.route("/")
def inicio():
    dados = PainelService.dados()
    por_dia = dados["por_dia"]
    grafico = {
        "rotulos": [d["dia"].strftime("%d/%m") for d in por_dia],
        "entradas": [int(d["entradas"]) for d in por_dia],
        "saidas": [int(d["saidas"]) for d in por_dia],
    }
    max_setor = max((float(s["valor"]) for s in dados["por_setor"]), default=0)
    return render_template(
        "painel.html", **dados, grafico=grafico, max_setor=max_setor,
        saudacao=saudacao(agora()),
    )


@bp.route("/dados-demonstracao", methods=["POST"])
@admin_obrigatorio
def carregar_demo():
    try:
        total = demo.carregar(usuario_id=current_user.id, responsavel=current_user.nome)
        flash(f"{total} produtos de demonstração carregados, com 4 semanas de movimentações.",
              "success")
    except ValueError as e:
        flash(str(e), "warning")
    return redirect(url_for("painel.inicio"))
