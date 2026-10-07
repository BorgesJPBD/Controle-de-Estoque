import re
from datetime import datetime


# Faixa de "atenção": acima do mínimo, mas a menos de 50% de folga.
FATOR_ATENCAO = 1.5

_CODIGO_VALIDO = re.compile(r"^[A-Z0-9][A-Z0-9\-_.]*$")


class Produto:
    def __init__(self, nome: str, categoria: str, unidade: str,
                 preco: float, quantidade: int = 0,
                 estoque_minimo: int = 5, produto_id: int = None,
                 criado_em: str = None, codigo: str = None):
        self._id = produto_id
        self._codigo = None
        self._nome = None
        self._categoria = None
        self._unidade = None
        self._preco = None
        self._quantidade = None
        self._estoque_minimo = None
        self._criado_em = criado_em or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # usa setters para validar
        self.codigo = codigo
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

    # ── código ────────────────────────────────────────────────────────────────
    @property
    def codigo(self):
        return self._codigo

    @codigo.setter
    def codigo(self, value: str):
        """Código interno do produto (ex.: LUV-001). Se vazio, o banco gera um."""
        value = (value or "").strip().upper()
        if not value:
            self._codigo = None
            return
        if len(value) > 30:
            raise ValueError("O código deve ter no máximo 30 caracteres.")
        if not _CODIGO_VALIDO.match(value):
            raise ValueError("Use apenas letras, números, hífen, ponto ou sublinhado no código.")
        self._codigo = value

    # ── nome ──────────────────────────────────────────────────────────────────
    @property
    def nome(self):
        return self._nome

    @nome.setter
    def nome(self, value: str):
        value = " ".join((value or "").split())
        if not value:
            raise ValueError("Informe o nome do produto.")
        if len(value) > 100:
            raise ValueError("O nome deve ter no máximo 100 caracteres.")
        self._nome = value

    # ── categoria ─────────────────────────────────────────────────────────────
    @property
    def categoria(self):
        return self._categoria

    @categoria.setter
    def categoria(self, value: str):
        value = " ".join((value or "").split())
        self._categoria = value if value else "Geral"

    # ── unidade ───────────────────────────────────────────────────────────────
    @property
    def unidade(self):
        return self._unidade

    @unidade.setter
    def unidade(self, value: str):
        value = (value or "").strip().upper()
        if not value:
            raise ValueError("Informe a unidade de medida.")
        if len(value) > 10:
            raise ValueError("A unidade deve ter no máximo 10 caracteres.")
        self._unidade = value

    # ── preço ─────────────────────────────────────────────────────────────────
    @property
    def preco(self):
        return self._preco

    @preco.setter
    def preco(self, value: float):
        try:
            value = float(str(value).replace(",", ".")) if value not in (None, "") else 0.0
        except ValueError:
            raise ValueError("Preço inválido.")
        if value < 0:
            raise ValueError("O preço não pode ser negativo.")
        self._preco = round(value, 2)

    # ── quantidade ────────────────────────────────────────────────────────────
    @property
    def quantidade(self):
        return self._quantidade

    @quantidade.setter
    def quantidade(self, value: int):
        try:
            value = int(value) if value not in (None, "") else 0
        except ValueError:
            raise ValueError("Quantidade inválida.")
        if value < 0:
            raise ValueError("A quantidade não pode ser negativa.")
        self._quantidade = value

    # ── estoque mínimo ────────────────────────────────────────────────────────
    @property
    def estoque_minimo(self):
        return self._estoque_minimo

    @estoque_minimo.setter
    def estoque_minimo(self, value: int):
        try:
            value = int(value) if value not in (None, "") else 0
        except ValueError:
            raise ValueError("Estoque mínimo inválido.")
        if value < 0:
            raise ValueError("O estoque mínimo não pode ser negativo.")
        self._estoque_minimo = value

    @property
    def criado_em(self):
        return self._criado_em

    # ── helpers ───────────────────────────────────────────────────────────────
    @property
    def estoque_baixo(self) -> bool:
        return self._quantidade <= self._estoque_minimo

    @property
    def status(self) -> str:
        """'critico' (no mínimo ou abaixo), 'atencao' (perto do mínimo) ou 'normal'."""
        if self.estoque_baixo:
            return "critico"
        if self._quantidade <= self._estoque_minimo * FATOR_ATENCAO:
            return "atencao"
        return "normal"

    @property
    def deficit(self) -> int:
        """Quanto falta para voltar ao estoque mínimo."""
        return max(self._estoque_minimo - self._quantidade, 0)

    @property
    def reposicao_sugerida(self) -> int:
        """Quantidade para chegar ao dobro do mínimo (folga de segurança)."""
        alvo = max(self._estoque_minimo * 2, 1)
        return max(alvo - self._quantidade, 0)

    @property
    def nivel(self) -> float:
        """Posição da barra de nível (0 a 100). O mínimo fica em 1/3 da barra."""
        escala = max(self._estoque_minimo * 3, 1)
        return round(min(self._quantidade / escala, 1) * 100, 1)

    @property
    def marca_minimo(self) -> float:
        return 33.3 if self._estoque_minimo > 0 else 0

    @property
    def valor_total(self) -> float:
        return round(self._preco * self._quantidade, 2)

    def to_dict(self) -> dict:
        return {
            "id": self._id,
            "codigo": self._codigo,
            "nome": self._nome,
            "categoria": self._categoria,
            "unidade": self._unidade,
            "preco": self._preco,
            "quantidade": self._quantidade,
            "estoque_minimo": self._estoque_minimo,
            "criado_em": self._criado_em,
        }

    def __repr__(self):
        return (f"Produto(id={self._id}, codigo='{self._codigo}', nome='{self._nome}', "
                f"qtd={self._quantidade}, preco={self._preco})")
