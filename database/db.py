import os
import psycopg2
import psycopg2.extras
from models.produto import Produto
from models.movimentacao import Movimentacao

def _conectar():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "db"),
        port=os.environ.get("DB_PORT", 5432),
        dbname=os.environ.get("DB_NAME", "almoxarifado"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASSWORD", "postgres"),
    )


def inicializar():
    with _conectar() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS produtos (
                    id              SERIAL PRIMARY KEY,
                    nome            TEXT    NOT NULL UNIQUE,
                    categoria       TEXT    NOT NULL DEFAULT 'Geral',
                    unidade         TEXT    NOT NULL DEFAULT 'UN',
                    preco           NUMERIC(10,2) NOT NULL DEFAULT 0,
                    quantidade      INTEGER NOT NULL DEFAULT 0,
                    estoque_minimo  INTEGER NOT NULL DEFAULT 5,
                    criado_em       TIMESTAMP DEFAULT NOW()
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS movimentacoes (
                    id          SERIAL PRIMARY KEY,
                    produto_id  INTEGER NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
                    tipo        TEXT    NOT NULL,
                    quantidade  INTEGER NOT NULL,
                    responsavel TEXT    DEFAULT '',
                    observacao  TEXT    DEFAULT '',
                    data        TIMESTAMP DEFAULT NOW()
                )
            """)
        conn.commit()


# ── Produtos ──────────────────────────────────────────────────────────────────

def inserir_produto(p: Produto) -> int:
    with _conectar() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO produtos (nome, categoria, unidade, preco, quantidade, estoque_minimo)
                   VALUES (%(nome)s, %(categoria)s, %(unidade)s, %(preco)s, %(quantidade)s, %(estoque_minimo)s)
                   RETURNING id""",
                p.to_dict()
            )
            novo_id = cur.fetchone()[0]
        conn.commit()
    return novo_id


def atualizar_produto(p: Produto) -> bool:
    with _conectar() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE produtos SET nome=%(nome)s, categoria=%(categoria)s, unidade=%(unidade)s,
                   preco=%(preco)s, estoque_minimo=%(estoque_minimo)s WHERE id=%(id)s""",
                p.to_dict()
            )
            updated = cur.rowcount > 0
        conn.commit()
    return updated


def deletar_produto(produto_id: int) -> bool:
    with _conectar() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM produtos WHERE id = %s", (produto_id,))
            deleted = cur.rowcount > 0
        conn.commit()
    return deleted


def buscar_produto_por_id(produto_id: int):
    with _conectar() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM produtos WHERE id = %s", (produto_id,))
            row = cur.fetchone()
    return _row_to_produto(row) if row else None


def listar_produtos(filtro_nome: str = "", filtro_categoria: str = ""):
    query = "SELECT * FROM produtos WHERE 1=1"
    params = []
    if filtro_nome:
        query += " AND nome ILIKE %s"
        params.append(f"%{filtro_nome}%")
    if filtro_categoria:
        query += " AND categoria = %s"
        params.append(filtro_categoria)
    query += " ORDER BY nome"
    with _conectar() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
    return [_row_to_produto(r) for r in rows]


def listar_categorias():
    with _conectar() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT categoria FROM produtos ORDER BY categoria")
            rows = cur.fetchall()
    return [r[0] for r in rows]


def _row_to_produto(row) -> Produto:
    return Produto(
        nome=row["nome"],
        categoria=row["categoria"],
        unidade=row["unidade"],
        preco=float(row["preco"]),
        quantidade=row["quantidade"],
        estoque_minimo=row["estoque_minimo"],
        produto_id=row["id"],
        criado_em=str(row["criado_em"]),
    )

# ── Movimentações ─────────────────────────────────────────────────────────────

def registrar_movimentacao(m: Movimentacao) -> bool:
    with _conectar() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT quantidade FROM produtos WHERE id = %s", (m.produto_id,)
            )
            produto = cur.fetchone()
            if not produto:
                raise ValueError("Produto não encontrado.")
            qtd_atual = produto["quantidade"]
            if m.tipo == "saida" and m.quantidade > qtd_atual:
                raise ValueError(f"Estoque insuficiente. Disponível: {qtd_atual}.")
            delta = m.quantidade if m.tipo == "entrada" else -m.quantidade
            cur.execute(
                "UPDATE produtos SET quantidade = quantidade + %s WHERE id = %s",
                (delta, m.produto_id)
            )
            cur.execute(
                """INSERT INTO movimentacoes (produto_id, tipo, quantidade, responsavel, observacao)
                   VALUES (%(produto_id)s, %(tipo)s, %(quantidade)s, %(responsavel)s, %(observacao)s)""",
                m.to_dict()
            )
        conn.commit()
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
        query += " AND m.produto_id = %s"
        params.append(produto_id)
    if tipo:
        query += " AND m.tipo = %s"
        params.append(tipo)
    query += " ORDER BY m.data DESC LIMIT %s"
    params.append(limite)
    with _conectar() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
    return [dict(r) for r in rows]


def produtos_estoque_baixo():
    with _conectar() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM produtos WHERE quantidade <= estoque_minimo ORDER BY quantidade"
            )
            rows = cur.fetchall()
    return [_row_to_produto(r) for r in rows]


def resumo_estoque():
    with _conectar() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT COUNT(*) as total_produtos,
                       COALESCE(SUM(quantidade), 0) as total_itens,
                       COALESCE(SUM(preco * quantidade), 0) as valor_total
                FROM produtos
            """)
            row = cur.fetchone()
    return dict(row)