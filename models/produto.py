from datetime import datetime


class Produto:
    def __init__(self, nome: str, categoria: str, unidade: str,
                 preco: float, quantidade: int = 0,
                 estoque_minimo: int = 5, produto_id: int = None,
                 criado_em: str = None):
        self._id = produto_id
        self._nome = None
        self._categoria = None
        self._unidade = None
        self._preco = None
        self._quantidade = None
        self._estoque_minimo = None
        self._criado_em = criado_em or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # usa setters para validar
        self.nome = nome
        self.categoria = categoria
        self.unidade = unidade
        self.preco = preco
        self.quantidade = quantidade
        self.estoque_minimo = estoque_minimo

    # ── id ────────────────────────────────────────────────────────────────────
    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        if value is not None and (not isinstance(value, int) or value <= 0):
            raise ValueError("ID deve ser um inteiro positivo.")
        self._id = value

    # ── nome ──────────────────────────────────────────────────────────────────
    @property
    def nome(self):
        return self._nome

    @nome.setter
    def nome(self, value: str):
        value = value.strip()
        if not value:
            raise ValueError("Nome não pode ser vazio.")
        if len(value) > 100:
            raise ValueError("Nome deve ter no máximo 100 caracteres.")
        self._nome = value

    # ── categoria ─────────────────────────────────────────────────────────────
    @property
    def categoria(self):
        return self._categoria

    @categoria.setter
    def categoria(self, value: str):
        self._categoria = value.strip() if value else "Geral"

    # ── unidade ───────────────────────────────────────────────────────────────
    @property
    def unidade(self):
        return self._unidade

    @unidade.setter
    def unidade(self, value: str):
        value = value.strip().upper()
        if not value:
            raise ValueError("Unidade não pode ser vazia.")
        self._unidade = value

    # ── preço ─────────────────────────────────────────────────────────────────
    @property
    def preco(self):
        return self._preco

    @preco.setter
    def preco(self, value: float):
        value = float(value)
        if value < 0:
            raise ValueError("Preço não pode ser negativo.")
        self._preco = round(value, 2)

    # ── quantidade ────────────────────────────────────────────────────────────
    @property
    def quantidade(self):
        return self._quantidade

    @quantidade.setter
    def quantidade(self, value: int):
        value = int(value)
        if value < 0:
            raise ValueError("Quantidade não pode ser negativa.")
        self._quantidade = value

    # ── estoque mínimo ────────────────────────────────────────────────────────
    @property
    def estoque_minimo(self):
        return self._estoque_minimo

    @estoque_minimo.setter
    def estoque_minimo(self, value: int):
        value = int(value)
        if value < 0:
            raise ValueError("Estoque mínimo não pode ser negativo.")
        self._estoque_minimo = value

    @property
    def criado_em(self):
        return self._criado_em

    # ── helpers ───────────────────────────────────────────────────────────────
    @property
    def estoque_baixo(self) -> bool:
        return self._quantidade <= self._estoque_minimo

    @property
    def valor_total(self) -> float:
        return round(self._preco * self._quantidade, 2)

    def to_dict(self) -> dict:
        return {
            "id": self._id,
            "nome": self._nome,
            "categoria": self._categoria,
            "unidade": self._unidade,
            "preco": self._preco,
            "quantidade": self._quantidade,
            "estoque_minimo": self._estoque_minimo,
            "criado_em": self._criado_em,
        }

    def __repr__(self):
        return (f"Produto(id={self._id}, nome='{self._nome}', "
                f"qtd={self._quantidade}, preco={self._preco})")
