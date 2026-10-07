import math
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user

from services import ProdutoService, MovimentacaoService
from utils import SETORES_HOSPITALARES


bp = Blueprint("movimentacoes", __name__)

POR_PAGINA = 25


def _registrar(tipo: str):
    produtos = ProdutoService.listar()
    erro = None
    dados = {
        "produto_id": request.args.get("produto", ""),
        "quantidade": request.args.get("quantidade", ""),
        "setor": "", "observacao": "",
    }
    if request.method == "POST":
        dados = request.form
        try:
            comum = dict(
                produto_id=request.form.get("produto_id"),
                quantidade=request.form.get("quantidade"),
                responsavel=current_user.nome,
                observacao=request.form.get("observacao", ""),
                usuario_id=current_user.id,
            )
            if tipo == "entrada":
                MovimentacaoService.entrada(**comum)
            else:
                MovimentacaoService.saida(**comum, setor=request.form.get("setor", ""),
                                          exigir_setor=True)
            produto = ProdutoService.buscar_por_id(int(request.form["produto_id"]))
            verbo = "Entrada" if tipo == "entrada" else "Saída"
            flash(f"{verbo} registrada: {request.form['quantidade']} {produto.unidade} de "
                  f"{produto.nome}. Estoque atual: {produto.quantidade} {produto.unidade}.",
                  "success")
            if request.form.get("continuar"):
                return redirect(url_for(f"movimentacoes.{tipo}"))
            return redirect(url_for("movimentacoes.historico"))
        except ValueError as e:
            erro = str(e)
    return render_template("movimentacoes/form.html", tipo=tipo, produtos=produtos,
                           dados=dados, erro=erro, setores=SETORES_HOSPITALARES)


@bp.route("/movimentacoes/entrada", methods=["GET", "POST"])
def entrada():
    return _registrar("entrada")


@bp.route("/movimentacoes/saida", methods=["GET", "POST"])
def saida():
    return _registrar("saida")


def _data_valida(texto: str) -> str:
    try:
        datetime.strptime(texto, "%Y-%m-%d")
        return texto
    except (TypeError, ValueError):
        return ""


def filtros_historico() -> dict:
    tipo = request.args.get("tipo", "")
    return {
        "tipo": tipo if tipo in ("entrada", "saida") else "",
        "busca": request.args.get("busca", "").strip(),
        "setor": request.args.get("setor", ""),
        "data_inicio": _data_valida(request.args.get("data_inicio", "")),
        "data_fim": _data_valida(request.args.get("data_fim", "")),
    }


@bp.route("/movimentacoes")
def historico():
    filtros = filtros_historico()
    consulta = {k: (v or None) for k, v in filtros.items()}
    total = MovimentacaoService.contar(**consulta)
    paginas = max(math.ceil(total / POR_PAGINA), 1)
    pagina = min(max(request.args.get("pagina", 1, type=int), 1), paginas)
    movimentacoes = MovimentacaoService.historico(
        **consulta, limite=POR_PAGINA, offset=(pagina - 1) * POR_PAGINA
    )
    return render_template(
        "movimentacoes/historico.html", movimentacoes=movimentacoes, filtros=filtros,
        total=total, pagina=pagina, paginas=paginas, por_pagina=POR_PAGINA,
        setores=MovimentacaoService.setores_usados(), filtrado=any(filtros.values()),
    )


# Endereços antigos continuam funcionando
@bp.route("/historico")
def historico_antigo():
    return redirect(url_for("movimentacoes.historico", **request.args))
