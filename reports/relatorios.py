"""Relatórios em CSV (separador ';' e UTF-8 com BOM, para abrir direto no Excel).

As funções csv_* devolvem o conteúdo em texto e são usadas pela versão web
(download no navegador). As funções relatorio_* gravam o arquivo na pasta
relatorios/ e continuam disponíveis para a versão desktop antiga.
"""
import csv
import io
import os
from datetime import datetime

from services import ProdutoService, MovimentacaoService
from utils.helpers import formatar_data_hora


REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "relatorios")

STATUS_TEXTO = {"critico": "CRÍTICO", "atencao": "ATENÇÃO", "normal": "OK"}


def _num(valor: float) -> str:
    """Número no formato brasileiro (vírgula decimal) para o Excel reconhecer."""
    return f"{valor:.2f}".replace(".", ",")


def _gerar_csv(campos, linhas) -> str:
    buffer = io.StringIO()
    w = csv.writer(buffer, delimiter=";")
    w.writerow(campos)
    w.writerows(linhas)
    return "﻿" + buffer.getvalue()


# ── Conteúdo dos relatórios ───────────────────────────────────────────────────

def csv_estoque_completo(filtro_nome="", filtro_categoria="", filtro_status="") -> str:
    produtos = ProdutoService.listar(filtro_nome, filtro_categoria, filtro_status)
    campos = ["Código", "Nome", "Categoria", "Unidade", "Preço (R$)",
              "Quantidade", "Estoque Mínimo", "Valor Total (R$)", "Situação", "Cadastrado em"]
    linhas = [[
        p.codigo, p.nome, p.categoria, p.unidade, _num(p.preco),
        p.quantidade, p.estoque_minimo, _num(p.valor_total),
        STATUS_TEXTO[p.status], formatar_data_hora(p.criado_em),
    ] for p in produtos]
    return _gerar_csv(campos, linhas)


def csv_estoque_baixo() -> str:
    produtos = ProdutoService.estoque_baixo()
    campos = ["Código", "Nome", "Categoria", "Unidade", "Quantidade",
              "Estoque Mínimo", "Déficit", "Reposição sugerida"]
    linhas = [[p.codigo, p.nome, p.categoria, p.unidade, p.quantidade,
               p.estoque_minimo, p.deficit, p.reposicao_sugerida] for p in produtos]
    return _gerar_csv(campos, linhas)


def csv_movimentacoes(tipo=None, busca=None, setor=None, data_inicio=None, data_fim=None,
                      produto_id=None) -> str:
    movs = MovimentacaoService.historico(
        produto_id=produto_id, tipo=tipo, busca=busca, setor=setor,
        data_inicio=data_inicio, data_fim=data_fim, limite=100000,
    )
    campos = ["Data", "Código", "Produto", "Tipo", "Quantidade", "Unidade",
              "Setor de destino", "Responsável", "Observação"]
    linhas = [[
        formatar_data_hora(m["data"]), m.get("produto_codigo", ""), m["produto_nome"],
        "Entrada" if m["tipo"] == "entrada" else "Saída", m["quantidade"],
        m.get("produto_unidade", ""), m.get("setor", ""),
        m.get("usuario_nome") or m["responsavel"], m["observacao"],
    ] for m in movs]
    return _gerar_csv(campos, linhas)


def csv_resumo_por_categoria() -> str:
    produtos = ProdutoService.listar()
    cats: dict = {}
    for p in produtos:
        dados = cats.setdefault(p.categoria, {"qtd_itens": 0, "total_unidades": 0,
                                              "valor_total": 0.0, "criticos": 0})
        dados["qtd_itens"] += 1
        dados["total_unidades"] += p.quantidade
        dados["valor_total"] += p.valor_total
        dados["criticos"] += 1 if p.estoque_baixo else 0
    campos = ["Categoria", "Qtd de Produtos", "Total de Unidades",
              "Valor Total (R$)", "Itens Críticos"]
    linhas = [[cat, d["qtd_itens"], d["total_unidades"], _num(d["valor_total"]), d["criticos"]]
              for cat, d in sorted(cats.items())]
    return _gerar_csv(campos, linhas)


def nome_arquivo(prefixo: str) -> str:
    return f"{prefixo}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"


# ── Versão desktop: grava os arquivos em relatorios/ ──────────────────────────

def _salvar(prefixo: str, conteudo: str) -> str:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    caminho = os.path.join(REPORTS_DIR, f"{prefixo}_{ts}.csv")
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        f.write(conteudo)
    return caminho


def relatorio_estoque_completo() -> str:
    return _salvar("estoque_completo", csv_estoque_completo())


def relatorio_estoque_baixo() -> str:
    return _salvar("estoque_baixo", csv_estoque_baixo())


def relatorio_movimentacoes(produto_id=None, tipo=None) -> str:
    prefixo = f"movimentacoes_{tipo}" if tipo else "movimentacoes"
    return _salvar(prefixo, csv_movimentacoes(tipo=tipo, produto_id=produto_id))


def relatorio_resumo_por_categoria() -> str:
    return _salvar("resumo_categoria", csv_resumo_por_categoria())
