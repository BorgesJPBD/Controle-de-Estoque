from models.produto import Produto
from models.movimentacao import Movimentacao
import database as db


class ProdutoService:

    @staticmethod
    def criar(nome, categoria, unidade, preco, quantidade, estoque_minimo) -> Produto:
        produto = Produto(
            nome=nome, categoria=categoria, unidade=unidade,
            preco=preco, quantidade=quantidade, estoque_minimo=estoque_minimo
        )
        novo_id = db.inserir_produto(produto)
        produto.id = novo_id
        return produto

    @staticmethod
    def editar(produto_id, nome, categoria, unidade, preco, estoque_minimo) -> Produto:
        produto = db.buscar_produto_por_id(produto_id)
        if not produto:
            raise ValueError("Produto não encontrado.")
        produto.nome = nome
        produto.categoria = categoria
        produto.unidade = unidade
        produto.preco = preco
        produto.estoque_minimo = estoque_minimo
        db.atualizar_produto(produto)
        return produto

    @staticmethod
    def remover(produto_id: int) -> bool:
        if not db.buscar_produto_por_id(produto_id):
            raise ValueError("Produto não encontrado.")
        return db.deletar_produto(produto_id)

    @staticmethod
    def listar(filtro_nome="", filtro_categoria=""):
        return db.listar_produtos(filtro_nome, filtro_categoria)

    @staticmethod
    def buscar_por_id(produto_id: int):
        return db.buscar_produto_por_id(produto_id)

    @staticmethod
    def categorias():
        return db.listar_categorias()

    @staticmethod
    def estoque_baixo():
        return db.produtos_estoque_baixo()

    @staticmethod
    def resumo():
        return db.resumo_estoque()


class MovimentacaoService:

    @staticmethod
    def entrada(produto_id, quantidade, responsavel="", observacao="") -> Movimentacao:
        mov = Movimentacao(
            produto_id=produto_id, tipo="entrada",
            quantidade=quantidade, responsavel=responsavel, observacao=observacao
        )
        db.registrar_movimentacao(mov)
        return mov

    @staticmethod
    def saida(produto_id, quantidade, responsavel="", observacao="") -> Movimentacao:
        mov = Movimentacao(
            produto_id=produto_id, tipo="saida",
            quantidade=quantidade, responsavel=responsavel, observacao=observacao
        )
        db.registrar_movimentacao(mov)
        return mov

    @staticmethod
    def historico(produto_id=None, tipo=None, limite=200):
        return db.listar_movimentacoes(produto_id, tipo, limite)
