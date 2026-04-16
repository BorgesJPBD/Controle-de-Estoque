import csv
import os
from datetime import datetime
from services import ProdutoService, MovimentacaoService


REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "relatorios")


def _garantir_pasta():
    os.makedirs(REPORTS_DIR, exist_ok=True)


def _nome_arquivo(prefixo: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(REPORTS_DIR, f"{prefixo}_{ts}.csv")


def relatorio_estoque_completo() -> str:
    _garantir_pasta()
    caminho = _nome_arquivo("estoque_completo")
    produtos = ProdutoService.listar()
    campos = ["ID", "Nome", "Categoria", "Unidade", "Preço (R$)",
              "Quantidade", "Estoque Mínimo", "Valor Total (R$)",
              "Alerta", "Cadastrado em"]
    with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(campos)
        for p in produtos:
            w.writerow([
                p.id, p.nome, p.categoria, p.unidade,
                f"{p.preco:.2f}", p.quantidade, p.estoque_minimo,
                f"{p.valor_total:.2f}",
                "⚠ BAIXO" if p.estoque_baixo else "OK",
                p.criado_em,
            ])
    return caminho


def relatorio_estoque_baixo() -> str:
    _garantir_pasta()
    caminho = _nome_arquivo("estoque_baixo")
    produtos = ProdutoService.estoque_baixo()
    campos = ["ID", "Nome", "Categoria", "Unidade", "Quantidade", "Estoque Mínimo"]
    with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(campos)
        for p in produtos:
            w.writerow([p.id, p.nome, p.categoria, p.unidade,
                        p.quantidade, p.estoque_minimo])
    return caminho


def relatorio_movimentacoes(produto_id=None, tipo=None) -> str:
    _garantir_pasta()
    prefixo = "movimentacoes"
    if tipo:
        prefixo += f"_{tipo}"
    caminho = _nome_arquivo(prefixo)
    movs = MovimentacaoService.historico(produto_id=produto_id, tipo=tipo)
    campos = ["ID", "Produto", "Tipo", "Quantidade", "Responsável", "Observação", "Data"]
    with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(campos)
        for m in movs:
            w.writerow([
                m["id"], m["produto_nome"], m["tipo"], m["quantidade"],
                m["responsavel"], m["observacao"], m["data"],
            ])
    return caminho


def relatorio_resumo_por_categoria() -> str:
    _garantir_pasta()
    caminho = _nome_arquivo("resumo_categoria")
    produtos = ProdutoService.listar()
    # agrupa por categoria
    cats: dict = {}
    for p in produtos:
        cat = p.categoria
        if cat not in cats:
            cats[cat] = {"qtd_itens": 0, "total_unidades": 0, "valor_total": 0.0}
        cats[cat]["qtd_itens"] += 1
        cats[cat]["total_unidades"] += p.quantidade
        cats[cat]["valor_total"] += p.valor_total
    campos = ["Categoria", "Qtd de Produtos", "Total de Unidades", "Valor Total (R$)"]
    with open(caminho, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(campos)
        for cat, dados in sorted(cats.items()):
            w.writerow([cat, dados["qtd_itens"], dados["total_unidades"],
                        f"{dados['valor_total']:.2f}"])
    return caminho
