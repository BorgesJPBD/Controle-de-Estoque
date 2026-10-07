from flask import Blueprint, render_template, request, redirect, url_for, flash

from services import ProdutoService
from utils import UNIDADES_MEDIDA
from utils.seguranca import admin_obrigatorio


bp = Blueprint("produtos", __name__)


@bp.route("/produtos")
def lista():
    filtros = {
        "busca": request.args.get("busca", "").strip(),
        "categoria": request.args.get("categoria", ""),
        "status": request.args.get("status", ""),
    }
    produtos = ProdutoService.listar(filtros["busca"], filtros["categoria"], filtros["status"])
    return render_template(
        "produtos/lista.html", produtos=produtos, filtros=filtros,
        categorias=ProdutoService.categorias(), resumo=ProdutoService.resumo(),
        filtrado=any(filtros.values()),
    )


def _form_produto(produto=None, erro=None, dados=None):
    if dados is None:
        dados = produto.to_dict() if produto else {
            "codigo": "", "nome": "", "categoria": "", "unidade": "UN",
            "preco": "", "quantidade": 0, "estoque_minimo": 10,
        }
    return render_template(
        "produtos/form.html", produto=produto, dados=dados, erro=erro,
        categorias=ProdutoService.categorias(), unidades=UNIDADES_MEDIDA,
    )


@bp.route("/produtos/novo", methods=["GET", "POST"])
def novo():
    if request.method == "POST":
        try:
            produto = ProdutoService.criar(
                codigo=request.form.get("codigo", ""),
                nome=request.form.get("nome", ""),
                categoria=request.form.get("categoria", ""),
                unidade=request.form.get("unidade", ""),
                preco=request.form.get("preco", "0"),
                quantidade=request.form.get("quantidade", "0"),
                estoque_minimo=request.form.get("estoque_minimo", "0"),
            )
            flash(f"Produto “{produto.nome}” cadastrado com o código {produto.codigo}.", "success")
            if request.form.get("continuar"):
                return redirect(url_for("produtos.novo"))
            return redirect(url_for("produtos.lista"))
        except ValueError as e:
            return _form_produto(erro=str(e), dados=request.form)
    return _form_produto()


@bp.route("/produtos/<int:produto_id>/editar", methods=["GET", "POST"])
def editar(produto_id):
    produto = ProdutoService.buscar_por_id(produto_id)
    if not produto:
        flash("Produto não encontrado.", "warning")
        return redirect(url_for("produtos.lista"))
    if request.method == "POST":
        try:
            produto = ProdutoService.editar(
                produto_id=produto_id,
                codigo=request.form.get("codigo", ""),
                nome=request.form.get("nome", ""),
                categoria=request.form.get("categoria", ""),
                unidade=request.form.get("unidade", ""),
                preco=request.form.get("preco", "0"),
                estoque_minimo=request.form.get("estoque_minimo", "0"),
            )
            flash(f"Alterações em “{produto.nome}” salvas.", "success")
            return redirect(url_for("produtos.lista"))
        except ValueError as e:
            return _form_produto(produto, erro=str(e), dados=request.form)
    return _form_produto(produto)


@bp.route("/produtos/<int:produto_id>/excluir", methods=["POST"])
@admin_obrigatorio
def excluir(produto_id):
    try:
        produto = ProdutoService.buscar_por_id(produto_id)
        ProdutoService.remover(produto_id)
        flash(f"Produto “{produto.nome}” excluído.", "success")
    except ValueError as e:
        flash(str(e), "danger")
    return redirect(url_for("produtos.lista"))


@bp.route("/alertas")
def alertas():
    return render_template("alertas.html", produtos=ProdutoService.estoque_baixo())
