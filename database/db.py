import sqlite3
import os
from models.produto import Produto
from models.movimentacao import Movimentacao

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "almoxarifado.db")


def _conectar() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def inicializar():
    with _conectar() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS produtos (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                nome            TEXT    NOT NULL UNIQUE,
                categoria       TEXT    NOT NULL DEFAULT 'Geral',
                unidade         TEXT    NOT NULL DEFAULT 'UN',
                preco           REAL    NOT NULL DEFAULT 0,
                quantidade      INTEGER NOT NULL DEFAULT 0,
                estoque_minimo  INTEGER NOT NULL DEFAULT 5,
                criado_em       TEXT    DEFAULT (datetime('now','localtime'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS movimentacoes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                produto_id  INTEGER NOT NULL,
                tipo        TEXT    NOT NULL,
                quantidade  INTEGER NOT NULL,
                responsavel TEXT    DEFAULT '',
                observacao  TEXT    DEFAULT '',
                data        TEXT    DEFAULT (datetime('now','localtime')),
                FOREIGN KEY (produto_id) REFERENCES produtos(id) ON DELETE CASCADE
            )
        """)


# ── Produtos ──────────────────────────────────────────────────────────────────

def inserir_produto(p: Produto) -> int:
    with _conectar() as conn:
        cur = conn.execute(
            """INSERT INTO produtos (nome, categoria, unidade, preco, quantidade, estoque_minimo)
               VALUES (:nome, :categoria, :unidade, :preco, :quantidade, :estoque_minimo)""",
            p.to_dict()
        )
        return cur.lastrowid


def atualizar_produto(p: Produto) -> bool:
    with _conectar() as conn:
        cur = conn.execute(
            """UPDATE produtos SET nome=:nome, categoria=:categoria, unidade=:unidade,
               preco=:preco, estoque_minimo=:estoque_minimo WHERE id=:id""",
            p.to_dict()
        )
        return cur.rowcount > 0


def deletar_produto(produto_id: int) -> bool:
    with _conectar() as conn:
        cur = conn.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))
        return cur.rowcount > 0


def buscar_produto_por_id(produto_id: int):
    with _conectar() as conn:
        row = conn.execute("SELECT * FROM produtos WHERE id = ?", (produto_id,)).fetchone()
    return _row_to_produto(row) if row else None


def listar_produtos(filtro_nome: str = "", filtro_categoria: str = ""):
    query = "SELECT * FROM produtos WHERE 1=1"
    params = []
    if filtro_nome:
        query += " AND nome LIKE ?"
        params.append(f"%{filtro_nome}%")
    if filtro_categoria:
        query += " AND categoria = ?"
        params.append(filtro_categoria)
    query += " ORDER BY nome"
    with _conectar() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_row_to_produto(r) for r in rows]


def listar_categorias():
    with _conectar() as conn:
        rows = conn.execute(
            "SELECT DISTINCT categoria FROM produtos ORDER BY categoria"
        ).fetchall()
    return [r["categoria"] for r in rows]


def _row_to_produto(row) -> Produto:
    return Produto(
        nome=row["nome"],
        categoria=row["categoria"],
        unidade=row["unidade"],
        preco=row["preco"],
        quantidade=row["quantidade"],
        estoque_minimo=row["estoque_minimo"],
        produto_id=row["id"],
        criado_em=row["criado_em"],
    )


# ── Movimentações ─────────────────────────────────────────────────────────────

def registrar_movimentacao(m: Movimentacao) -> bool:
    with _conectar() as conn:
        produto = conn.execute(
            "SELECT quantidade FROM produtos WHERE id = ?", (m.produto_id,)
        ).fetchone()
        if not produto:
            raise ValueError("Produto não encontrado.")
        qtd_atual = produto["quantidade"]
        if m.tipo == "saida" and m.quantidade > qtd_atual:
            raise ValueError(f"Estoque insuficiente. Disponível: {qtd_atual}.")
        delta = m.quantidade if m.tipo == "entrada" else -m.quantidade
        conn.execute(
            "UPDATE produtos SET quantidade = quantidade + ? WHERE id = ?",
            (delta, m.produto_id)
        )
        conn.execute(
            """INSERT INTO movimentacoes (produto_id, tipo, quantidade, responsavel, observacao)
               VALUES (:produto_id, :tipo, :quantidade, :responsavel, :observacao)""",
            m.to_dict()
        )
    return True


def listar_movimentacoes(produto_id: int = None, tipo: str = None, limite: int = 200):
    query = """
        SELECT m.*, p.nome AS produto_nome
        FROM movimentacoes m
        JOIN produtos p ON p.id = m.produto_id
        WHERE 1=1
    """
    params = []
    if produto_id:
        query += " AND m.produto_id = ?"
        params.append(produto_id)
    if tipo:
        query += " AND m.tipo = ?"
        params.append(tipo)
    query += " ORDER BY m.data DESC LIMIT ?"
    params.append(limite)
    with _conectar() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def produtos_estoque_baixo():
    with _conectar() as conn:
        rows = conn.execute(
            "SELECT * FROM produtos WHERE quantidade <= estoque_minimo ORDER BY quantidade"
        ).fetchall()
    return [_row_to_produto(r) for r in rows]


def resumo_estoque():
    with _conectar() as conn:
        row = conn.execute("""
            SELECT COUNT(*) as total_produtos,
                   SUM(quantidade) as total_itens,
                   SUM(preco * quantidade) as valor_total
            FROM produtos
        """).fetchone()
    return dict(row)
