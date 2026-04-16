from datetime import datetime


TIPOS_VALIDOS = ("entrada", "saida")


class Movimentacao:
    def __init__(self, produto_id: int, tipo: str, quantidade: int,
                 responsavel: str = "", observacao: str = "",
                 mov_id: int = None, data: str = None):
        self._id = mov_id
        self._produto_id = None
        self._tipo = None
        self._quantidade = None
        self._responsavel = None
        self._observacao = None
        self._data = data or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.produto_id = produto_id
        self.tipo = tipo
        self.quantidade = quantidade
        self.responsavel = responsavel
        self.observacao = observacao

    # ── id ────────────────────────────────────────────────────────────────────
    @property
    def id(self):
        return self._id

    # ── produto_id ────────────────────────────────────────────────────────────
    @property
    def produto_id(self):
        return self._produto_id

    @produto_id.setter
    def produto_id(self, value: int):
        value = int(value)
        if value <= 0:
            raise ValueError("produto_id inválido.")
        self._produto_id = value

    # ── tipo ──────────────────────────────────────────────────────────────────
    @property
    def tipo(self):
        return self._tipo

    @tipo.setter
    def tipo(self, value: str):
        value = value.strip().lower()
        if value not in TIPOS_VALIDOS:
            raise ValueError(f"Tipo deve ser um de {TIPOS_VALIDOS}.")
        self._tipo = value

    # ── quantidade ────────────────────────────────────────────────────────────
    @property
    def quantidade(self):
        return self._quantidade

    @quantidade.setter
    def quantidade(self, value: int):
        value = int(value)
        if value <= 0:
            raise ValueError("Quantidade deve ser maior que zero.")
        self._quantidade = value

    # ── responsável ───────────────────────────────────────────────────────────
    @property
    def responsavel(self):
        return self._responsavel

    @responsavel.setter
    def responsavel(self, value: str):
        self._responsavel = value.strip() if value else ""

    # ── observação ────────────────────────────────────────────────────────────
    @property
    def observacao(self):
        return self._observacao

    @observacao.setter
    def observacao(self, value: str):
        self._observacao = value.strip() if value else ""

    @property
    def data(self):
        return self._data

    # ── helpers ───────────────────────────────────────────────────────────────
    @property
    def sinal(self) -> str:
        return "+" if self._tipo == "entrada" else "-"

    def to_dict(self) -> dict:
        return {
            "id": self._id,
            "produto_id": self._produto_id,
            "tipo": self._tipo,
            "quantidade": self._quantidade,
            "responsavel": self._responsavel,
            "observacao": self._observacao,
            "data": self._data,
        }

    def __repr__(self):
        return (f"Movimentacao(tipo='{self._tipo}', "
                f"qtd={self._quantidade}, data='{self._data}')")
