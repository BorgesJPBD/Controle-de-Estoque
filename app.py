import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, render_template, request, redirect, url_for, flash
import database as db
from services.service import ProdutoService, MovimentacaoService

app = Flask(__name__)
app.secret_key = "almoxarifado-2024"


def aguardar_banco(tentativas=10, espera=2):
    for i in range(tentativas):
        try:
            db.inicializar()
            print("Banco conectado!")
            return
        except Exception as e:
            print(f"Tentativa {i+1}/{tentativas}: {e}")
            time.sleep(espera)
    raise RuntimeError("Não foi possível conectar ao banco.")


@app.route("/")
def index():
    produtos = ProdutoService.listar()
    resumo = ProdutoService.resumo()
    alertas = ProdutoService.estoque_baixo()
    categorias = ProdutoService.categorias()
    return render_template("index.html", produtos=produtos,
                           resumo=resumo, alertas=alertas, categorias=categorias)


@app.route("/produto/novo", methods=["GET", "POST"])
def novo_produto():
    if request.method == "POST":
        try:
            ProdutoService.criar(
                nome=request.form["nome"],
                categoria=request.form["categoria"],
                unidade=request.form["unidade"],
                preco=float(request.form["preco"]),
                quantidade=int(request.form["quantidade"]),
                estoque_minimo=int(request.form["estoque_minimo"]),
            )
            flash("Produto cadastrado!", "success")
            return redirect(url_for("index"))
        except Exception as e:
            flash(f"Erro: {e}", "danger")
    return render_template("produto_form.html", produto=None)


@app.route("/produto/<int:produto_id>/editar", methods=["GET", "POST"])
def editar_produto(produto_id):
    produto = ProdutoService.buscar_por_id(produto_id)
    if request.method == "POST":
        try:
            ProdutoService.editar(
                produto_id=produto_id,
                nome=request.form["nome"],
                categoria=request.form["categoria"],
                unidade=request.form["unidade"],
                preco=float(request.form["preco"]),
                estoque_minimo=int(request.form["estoque_minimo"]),
            )
            flash("Produto atualizado!", "success")
            return redirect(url_for("index"))
        except Exception as e:
            flash(f"Erro: {e}", "danger")
    return render_template("produto_form.html", produto=produto)


@app.route("/produto/<int:produto_id>/remover", methods=["POST"])
def remover_produto(produto_id):
    try:
        ProdutoService.remover(produto_id)
        flash("Produto removido!", "success")
    except Exception as e:
        flash(f"Erro: {e}", "danger")
    return redirect(url_for("index"))


@app.route("/movimentacao/entrada", methods=["GET", "POST"])
def entrada():
    produtos = ProdutoService.listar()
    if request.method == "POST":
        try:
            MovimentacaoService.entrada(
                produto_id=int(request.form["produto_id"]),
                quantidade=int(request.form["quantidade"]),
                responsavel=request.form.get("responsavel", ""),
                observacao=request.form.get("observacao", ""),
            )
            flash("Entrada registrada!", "success")
            return redirect(url_for("historico"))
        except Exception as e:
            flash(f"Erro: {e}", "danger")
    return render_template("movimentacao_form.html", tipo="entrada", produtos=produtos)


@app.route("/movimentacao/saida", methods=["GET", "POST"])
def saida():
    produtos = ProdutoService.listar()
    if request.method == "POST":
        try:
            MovimentacaoService.saida(
                produto_id=int(request.form["produto_id"]),
                quantidade=int(request.form["quantidade"]),
                responsavel=request.form.get("responsavel", ""),
                observacao=request.form.get("observacao", ""),
            )
            flash("Saída registrada!", "success")
            return redirect(url_for("historico"))
        except Exception as e:
            flash(f"Erro: {e}", "danger")
    return render_template("movimentacao_form.html", tipo="saida", produtos=produtos)


@app.route("/historico")
def historico():
    tipo = request.args.get("tipo", "")
    movs = MovimentacaoService.historico(tipo=tipo if tipo else None)
    return render_template("historico.html", movimentacoes=movs, tipo=tipo)


@app.route("/alertas")
def alertas():
    produtos = ProdutoService.estoque_baixo()
    return render_template("alertas.html", produtos=produtos)


if __name__ == "__main__":
    aguardar_banco()
    app.run(host="0.0.0.0", port=5000, debug=False)