import os
import unicodedata
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
from psycopg2 import errors

from models.produto import Produto
from models.movimentacao import Movimentacao
from models.usuario import Usuario


# Fuso usado pelo banco para gravar e comparar datas (NOW(), CURRENT_DATE).
FUSO_HORARIO = os.environ.get("TZ_APP", "America/Campo_Grande")

# Erros de unicidade ficam acessíveis para as camadas de cima.
ErroUnicidade = errors.UniqueViolation


def _conectar():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "db"),
        port=os.environ.get("DB_PORT", 5432),
        dbname=os.environ.get("DB_NAME", "almoxarifado"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASSWORD", "postgres"),
        options=f"-c timezone={FUSO_HORARIO}",
    )


@contextmanager
def _cursor(dicionario: bool = True):
    """Abre conexão + cursor, faz commit no fim e sempre fecha a conexão."""
    conn = _conectar()
    try:
        fabrica = psycopg2.extras.RealDictCursor if dicionario else None
        with conn.cursor(cursor_factory=fabrica) as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Estrutura do banco ────────────────────────────────────────────────────────

def inicializar():
    """Cria as tabelas e aplica as migrações. Pode rodar várias vezes."""
    with _cursor(dicionario=False) as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id                SERIAL PRIMARY KEY,
                nome              TEXT NOT NULL,
                email             TEXT NOT NULL UNIQUE,
                senha_hash        TEXT NOT NULL,
                perfil            TEXT NOT NULL DEFAULT 'almoxarife',
                status            TEXT NOT NULL DEFAULT 'pendente',
                setor             TEXT NOT NULL DEFAULT '',
                tentativas_falhas INTEGER NOT NULL DEFAULT 0,
                bloqueado_ate     TIMESTAMP,
                ultimo_acesso     TIMESTAMP,
                criado_em         TIMESTAMP DEFAULT NOW()
            )
        """)
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

        # Migração v2: código do produto (corrige o bug de produto duplicado)
        cur.execute("ALTER TABLE produtos ADD COLUMN IF NOT EXISTS codigo TEXT")
        cur.execute("""
            UPDATE produtos SET codigo = 'PRD-' || LPAD(id::text, 5, '0')
            WHERE codigo IS NULL OR codigo = ''
        """)
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS produtos_codigo_uk
            ON produtos (UPPER(codigo))
        """)

        # Migração v2: setor de destino e usuário que registrou a movimentação
        cur.execute("ALTER TABLE movimentacoes ADD COLUMN IF NOT EXISTS setor TEXT NOT NULL DEFAULT ''")
        cur.execute("""
            ALTER TABLE movimentacoes ADD COLUMN IF NOT EXISTS usuario_id INTEGER
            REFERENCES usuarios(id) ON DELETE SET NULL
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS movimentacoes_data_idx ON movimentacoes (data DESC)")


# ── Produtos ──────────────────────────────────────────────────────────────────

def _gerar_codigo(cur, produto_id: int) -> str:
    base = f"PRD-{produto_id:05d}"
    codigo, sufixo = base, 1
    while True:
        cur.execute("SELECT 1 FROM produtos WHERE UPPER(codigo) = %s", (codigo,))
        if not cur.fetchone():
            return codigo
        sufixo += 1
        codigo = f"{base}-{sufixo}"


def inserir_produto(p: Produto) -> int:
    with _cursor() as cur:
        cur.execute(
            """INSERT INTO produtos (codigo, nome, categoria, unidade, preco, quantidade, estoque_minimo)
               VALUES (%(codigo)s, %(nome)s, %(categoria)s, %(unidade)s, %(preco)s,
                       %(quantidade)s, %(estoque_minimo)s)
               RETURNING id""",
            p.to_dict()
        )
        novo_id = cur.fetchone()["id"]
        if not p.codigo:
            codigo = _gerar_codigo(cur, novo_id)
            cur.execute("UPDATE produtos SET codigo = %s WHERE id = %s", (codigo, novo_id))
            p.codigo = codigo
    return novo_id


def atualizar_produto(p: Produto) -> bool:
    with _cursor() as cur:
        cur.execute(
            """UPDATE produtos SET codigo=%(codigo)s, nome=%(nome)s, categoria=%(categoria)s,
                   unidade=%(unidade)s, preco=%(preco)s, estoque_minimo=%(estoque_minimo)s
               WHERE id=%(id)s""",
            p.to_dict()
        )
        return cur.rowcount > 0


def deletar_produto(produto_id: int) -> bool:
    with _cursor() as cur:
        cur.execute("DELETE FROM produtos WHERE id = %s", (produto_id,))
        return cur.rowcount > 0


def buscar_produto_por_id(produto_id: int):
    with _cursor() as cur:
        cur.execute("SELECT * FROM produtos WHERE id = %s", (produto_id,))
        row = cur.fetchone()
    return _row_to_produto(row) if row else None


def buscar_produto_duplicado(nome: str, codigo: str = None, ignorar_id: int = None):
    """Procura outro produto com o mesmo nome ou código (sem diferenciar maiúsculas)."""
    query = "SELECT * FROM produtos WHERE (LOWER(nome) = LOWER(%s)"
    params = [nome]
    if codigo:
        query += " OR UPPER(codigo) = UPPER(%s)"
        params.append(codigo)
    query += ")"
    if ignorar_id:
        query += " AND id <> %s"
        params.append(ignorar_id)
    query += " LIMIT 1"
    with _cursor() as cur:
        cur.execute(query, params)
        row = cur.fetchone()
    return _row_to_produto(row) if row else None


def listar_produtos(filtro_nome: str = "", filtro_categoria: str = "", filtro_status: str = ""):
    query = "SELECT * FROM produtos WHERE 1=1"
    params = []
    if filtro_nome:
        query += " AND (nome ILIKE %s OR codigo ILIKE %s)"
        params += [f"%{filtro_nome}%", f"%{filtro_nome}%"]
    if filtro_categoria:
        query += " AND categoria = %s"
        params.append(filtro_categoria)
    if filtro_status == "critico":
        query += " AND quantidade <= estoque_minimo"
    elif filtro_status == "atencao":
        query += " AND quantidade > estoque_minimo AND quantidade <= estoque_minimo * 1.5"
    elif filtro_status == "normal":
        query += " AND quantidade > estoque_minimo * 1.5"
    with _cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()
    # ordena em Python para "Álcool" ficar junto do "A", qualquer que seja o idioma do banco
    return sorted((_row_to_produto(r) for r in rows), key=lambda p: _chave_ordem(p.nome))


def _chave_ordem(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.casefold()


def listar_categorias():
    with _cursor(dicionario=False) as cur:
        cur.execute("SELECT DISTINCT categoria FROM produtos")
        rows = cur.fetchall()
    return sorted((r[0] for r in rows), key=_chave_ordem)


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
        codigo=row.get("codigo"),
    )


# ── Movimentações ─────────────────────────────────────────────────────────────

def registrar_movimentacao(m: Movimentacao) -> bool:
    with _cursor() as cur:
        # FOR UPDATE trava a linha do produto: duas saídas ao mesmo tempo
        # não conseguem deixar o estoque negativo.
        cur.execute(
            "SELECT quantidade, unidade FROM produtos WHERE id = %s FOR UPDATE", (m.produto_id,)
        )
        produto = cur.fetchone()
        if not produto:
            raise ValueError("Produto não encontrado.")
        qtd_atual = produto["quantidade"]
        if m.tipo == "saida" and m.quantidade > qtd_atual:
            raise ValueError(
                f"Estoque insuficiente. Disponível: {qtd_atual} {produto['unidade']}."
            )
        delta = m.quantidade if m.tipo == "entrada" else -m.quantidade
        cur.execute(
            "UPDATE produtos SET quantidade = quantidade + %s WHERE id = %s",
            (delta, m.produto_id)
        )
        cur.execute(
            """INSERT INTO movimentacoes
                   (produto_id, tipo, quantidade, responsavel, observacao, setor, usuario_id)
               VALUES (%(produto_id)s, %(tipo)s, %(quantidade)s, %(responsavel)s,
                       %(observacao)s, %(setor)s, %(usuario_id)s)""",
            m.to_dict()
        )
    return True


def _filtros_movimentacoes(produto_id=None, tipo=None, busca=None, setor=None,
                           data_inicio=None, data_fim=None):
    where = " WHERE 1=1"
    params = []
    if produto_id:
        where += " AND m.produto_id = %s"
        params.append(produto_id)
    if tipo:
        where += " AND m.tipo = %s"
        params.append(tipo)
    if busca:
        where += " AND (p.nome ILIKE %s OR p.codigo ILIKE %s)"
        params += [f"%{busca}%", f"%{busca}%"]
    if setor:
        where += " AND m.setor = %s"
        params.append(setor)
    if data_inicio:
        where += " AND m.data >= %s::date"
        params.append(data_inicio)
    if data_fim:
        where += " AND m.data < %s::date + 1"
        params.append(data_fim)
    return where, params


def listar_movimentacoes(produto_id: int = None, tipo: str = None, limite: int = 200,
                         busca: str = None, setor: str = None, data_inicio=None,
                         data_fim=None, offset: int = 0):
    where, params = _filtros_movimentacoes(produto_id, tipo, busca, setor, data_inicio, data_fim)
    query = f"""
        SELECT m.*, p.nome AS produto_nome, p.codigo AS produto_codigo,
               p.unidade AS produto_unidade, u.nome AS usuario_nome
        FROM movimentacoes m
        JOIN produtos p ON p.id = m.produto_id
        LEFT JOIN usuarios u ON u.id = m.usuario_id
        {where}
        ORDER BY m.data DESC, m.id DESC
        LIMIT %s OFFSET %s
    """
    with _cursor() as cur:
        cur.execute(query, params + [limite, offset])
        rows = cur.fetchall()
    return [dict(r) for r in rows]


def contar_movimentacoes(produto_id=None, tipo=None, busca=None, setor=None,
                         data_inicio=None, data_fim=None) -> int:
    where, params = _filtros_movimentacoes(produto_id, tipo, busca, setor, data_inicio, data_fim)
    with _cursor() as cur:
        cur.execute(
            f"SELECT COUNT(*) AS total FROM movimentacoes m JOIN produtos p ON p.id = m.produto_id {where}",
            params,
        )
        return cur.fetchone()["total"]


def listar_setores_usados():
    with _cursor(dicionario=False) as cur:
        cur.execute("SELECT DISTINCT setor FROM movimentacoes WHERE setor <> ''")
        return sorted((r[0] for r in cur.fetchall()), key=_chave_ordem)


def produtos_estoque_baixo():
    with _cursor() as cur:
        cur.execute(
            """SELECT * FROM produtos WHERE quantidade <= estoque_minimo
               ORDER BY (quantidade::float / GREATEST(estoque_minimo, 1)), nome"""
        )
        rows = cur.fetchall()
    return [_row_to_produto(r) for r in rows]


def contar_estoque_baixo() -> int:
    with _cursor() as cur:
        cur.execute("SELECT COUNT(*) AS total FROM produtos WHERE quantidade <= estoque_minimo")
        return cur.fetchone()["total"]


def resumo_estoque():
    with _cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) AS total_produtos,
                   COALESCE(SUM(quantidade), 0) AS total_itens,
                   COALESCE(SUM(preco * quantidade), 0) AS valor_total,
                   COUNT(*) FILTER (WHERE quantidade <= estoque_minimo) AS criticos,
                   COUNT(*) FILTER (WHERE quantidade > estoque_minimo
                                      AND quantidade <= estoque_minimo * 1.5) AS atencao
            FROM produtos
        """)
        row = cur.fetchone()
    return dict(row)


# ── Painel (indicadores) ──────────────────────────────────────────────────────

def movimentos_por_dia(dias: int = 14):
    """Número de entradas e saídas registradas por dia, incluindo os dias sem movimento.

    Conta registros (e não quantidades) porque os produtos têm unidades
    diferentes: somar caixas com frascos não daria um número com sentido.
    """
    with _cursor() as cur:
        cur.execute("""
            SELECT d::date AS dia,
                   COUNT(m.id) FILTER (WHERE m.tipo = 'entrada') AS entradas,
                   COUNT(m.id) FILTER (WHERE m.tipo = 'saida')   AS saidas
            FROM generate_series(CURRENT_DATE - (%s - 1), CURRENT_DATE, INTERVAL '1 day') AS d
            LEFT JOIN movimentacoes m ON m.data::date = d::date
            GROUP BY d ORDER BY d
        """, (dias,))
        return [dict(r) for r in cur.fetchall()]


def consumo_por_setor(dias: int = 30, limite: int = 6):
    with _cursor() as cur:
        cur.execute("""
            SELECT COALESCE(NULLIF(m.setor, ''), 'Não informado') AS setor,
                   SUM(m.quantidade) AS quantidade,
                   SUM(m.quantidade * p.preco) AS valor
            FROM movimentacoes m JOIN produtos p ON p.id = m.produto_id
            WHERE m.tipo = 'saida' AND m.data >= CURRENT_DATE - (%s - 1)
            GROUP BY 1 ORDER BY valor DESC LIMIT %s
        """, (dias, limite))
        return [dict(r) for r in cur.fetchall()]


def movimentacoes_hoje():
    with _cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) FILTER (WHERE tipo = 'entrada') AS entradas,
                   COUNT(*) FILTER (WHERE tipo = 'saida')   AS saidas
            FROM movimentacoes WHERE data::date = CURRENT_DATE
        """)
        return dict(cur.fetchone())


# ── Usuários ──────────────────────────────────────────────────────────────────

def _row_to_usuario(row) -> Usuario:
    return Usuario(
        nome=row["nome"],
        email=row["email"],
        perfil=row["perfil"],
        status=row["status"],
        setor=row["setor"],
        usuario_id=row["id"],
        senha_hash=row["senha_hash"],
        criado_em=row["criado_em"],
        ultimo_acesso=row["ultimo_acesso"],
        tentativas_falhas=row["tentativas_falhas"],
        bloqueado_ate=row["bloqueado_ate"],
    )


def contar_usuarios(perfil: str = None, status: str = None) -> int:
    query = "SELECT COUNT(*) AS total FROM usuarios WHERE 1=1"
    params = []
    if perfil:
        query += " AND perfil = %s"
        params.append(perfil)
    if status:
        query += " AND status = %s"
        params.append(status)
    with _cursor() as cur:
        cur.execute(query, params)
        return cur.fetchone()["total"]


def inserir_usuario(u: Usuario) -> int:
    with _cursor() as cur:
        cur.execute(
            """INSERT INTO usuarios (nome, email, senha_hash, perfil, status, setor)
               VALUES (%(nome)s, %(email)s, %(senha_hash)s, %(perfil)s, %(status)s, %(setor)s)
               RETURNING id""",
            u.to_dict()
        )
        return cur.fetchone()["id"]


def buscar_usuario_por_id(usuario_id: int):
    with _cursor() as cur:
        cur.execute("SELECT * FROM usuarios WHERE id = %s", (usuario_id,))
        row = cur.fetchone()
    return _row_to_usuario(row) if row else None


def buscar_usuario_por_email(email: str):
    with _cursor() as cur:
        cur.execute("SELECT * FROM usuarios WHERE email = LOWER(%s)", ((email or "").strip(),))
        row = cur.fetchone()
    return _row_to_usuario(row) if row else None


def listar_usuarios():
    with _cursor() as cur:
        cur.execute("""
            SELECT * FROM usuarios
            ORDER BY CASE status WHEN 'pendente' THEN 0 WHEN 'ativo' THEN 1 ELSE 2 END, nome
        """)
        return [_row_to_usuario(r) for r in cur.fetchall()]


def atualizar_usuario(u: Usuario) -> bool:
    with _cursor() as cur:
        cur.execute(
            """UPDATE usuarios SET nome=%(nome)s, email=%(email)s, perfil=%(perfil)s,
                   status=%(status)s, setor=%(setor)s WHERE id=%(id)s""",
            u.to_dict()
        )
        return cur.rowcount > 0


def atualizar_senha(usuario_id: int, senha_hash: str) -> bool:
    with _cursor() as cur:
        cur.execute(
            """UPDATE usuarios SET senha_hash = %s, tentativas_falhas = 0, bloqueado_ate = NULL
               WHERE id = %s""",
            (senha_hash, usuario_id)
        )
        return cur.rowcount > 0


def deletar_usuario(usuario_id: int) -> bool:
    with _cursor() as cur:
        cur.execute("DELETE FROM usuarios WHERE id = %s", (usuario_id,))
        return cur.rowcount > 0


def registrar_login_sucesso(usuario_id: int):
    with _cursor() as cur:
        cur.execute(
            """UPDATE usuarios SET ultimo_acesso = NOW(), tentativas_falhas = 0,
                   bloqueado_ate = NULL WHERE id = %s""",
            (usuario_id,)
        )


def registrar_login_falha(usuario_id: int, max_tentativas: int, minutos_bloqueio: int):
    """Soma uma falha; ao atingir o limite, bloqueia a conta por alguns minutos."""
    with _cursor() as cur:
        cur.execute(
            """UPDATE usuarios SET
                   tentativas_falhas = tentativas_falhas + 1,
                   bloqueado_ate = CASE WHEN tentativas_falhas + 1 >= %s
                                        THEN NOW() + (%s || ' minutes')::interval
                                        ELSE bloqueado_ate END
               WHERE id = %s
               RETURNING tentativas_falhas, bloqueado_ate""",
            (max_tentativas, str(minutos_bloqueio), usuario_id)
        )
        return dict(cur.fetchone())


def conta_bloqueada(usuario_id: int) -> bool:
    with _cursor() as cur:
        cur.execute(
            "SELECT bloqueado_ate IS NOT NULL AND bloqueado_ate > NOW() AS bloqueada FROM usuarios WHERE id = %s",
            (usuario_id,)
        )
        row = cur.fetchone()
    return bool(row and row["bloqueada"])


def liberar_bloqueio(usuario_id: int):
    with _cursor() as cur:
        cur.execute(
            "UPDATE usuarios SET tentativas_falhas = 0, bloqueado_ate = NULL WHERE id = %s",
            (usuario_id,)
        )
