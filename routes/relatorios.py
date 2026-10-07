from flask import Blueprint, Response, render_template, request, abort

import reports
from services import ProdutoService, MovimentacaoService
from routes.movimentacoes import filtros_historico


bp = Blueprint("relatorios", __name__)


def _download(conteudo: str, prefixo: str) -> Response:
    return Response(
        conteudo,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{reports.nome_arquivo(prefixo)}"'},
    )


@bp.route("/relatorios")
def inicio():
    return render_template(
        "relatorios.html",
        resumo=ProdutoService.resumo(),
        total_movimentacoes=MovimentacaoService.contar(),
    )


@bp.route("/relatorios/<relatorio>.csv")
def baixar(relatorio):
    if relatorio == "estoque":
        conteudo = reports.csv_estoque_completo(
            request.args.get("busca", ""), request.args.get("categoria", ""),
            request.args.get("status", ""),
        )
        return _download(conteudo, "estoque_completo")
    if relatorio == "estoque-baixo":
        return _download(reports.csv_estoque_baixo(), "estoque_baixo")
    if relatorio == "movimentacoes":
        filtros = {k: (v or None) for k, v in filtros_historico().items()}
        return _download(reports.csv_movimentacoes(**filtros), "movimentacoes")
    if relatorio == "categorias":
        return _download(reports.csv_resumo_por_categoria(), "resumo_por_categoria")
    abort(404)
