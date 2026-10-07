import re
from datetime import datetime

from werkzeug.security import generate_password_hash, check_password_hash

from models.produto import Produto
from models.movimentacao import Movimentacao
from models.usuario import Usuario, PERFIS
import database as db


# ═══════════════════════════════════════════════════════════════════════════════
#  Produtos
# ═══════════════════════════════════════════════════════════════════════════════

class ProdutoService:

    @staticmethod
    def _checar_duplicado(produto: Produto, ignorar_id: int = None):
        """Bloqueia nome ou código repetido com uma mensagem clara.

        Corrige o bug "código de produto duplicado no cadastro": antes o banco
        recusava o registro e o usuário via um erro técnico do PostgreSQL.
        """
        existente = db.buscar_produto_duplicado(produto.nome, produto.codigo, ignorar_id)
        if not existente:
            return
        if produto.codigo and existente.codigo and existente.codigo.upper() == produto.codigo.upper():
            raise ValueError(
                f"O código {produto.codigo} já pertence ao produto “{existente.nome}”."
            )
        raise ValueError(
            f"Já existe um produto chamado “{existente.nome}” (código {existente.codigo})."
        )

    @staticmethod
    def _traduzir_erro_unicidade(erro):
        restricao = getattr(getattr(erro, "diag", None), "constraint_name", "") or ""
        if "codigo" in restricao:
            return ValueError("Já existe um produto com esse código.")
        return ValueError("Já existe um produto com esse nome.")

    @staticmethod
    def criar(nome, categoria, unidade, preco, quantidade, estoque_minimo, codigo=None) -> Produto:
        produto = Produto(
            nome=nome, categoria=categoria, unidade=unidade, preco=preco,
            quantidade=quantidade, estoque_minimo=estoque_minimo, codigo=codigo,
        )
        ProdutoService._checar_duplicado(produto)
        try:
            produto.id = db.inserir_produto(produto)
        except db.ErroUnicidade as e:
            raise ProdutoService._traduzir_erro_unicidade(e)
        return produto

    @staticmethod
    def editar(produto_id, nome, categoria, unidade, preco, estoque_minimo, codigo=None) -> Produto:
        produto = db.buscar_produto_por_id(produto_id)
        if not produto:
            raise ValueError("Produto não encontrado.")
        produto.nome = nome
        produto.categoria = categoria
        produto.unidade = unidade
        produto.preco = preco
        produto.estoque_minimo = estoque_minimo
        if codigo is not None:
            produto.codigo = codigo or produto.codigo
        ProdutoService._checar_duplicado(produto, ignorar_id=produto_id)
        try:
            db.atualizar_produto(produto)
        except db.ErroUnicidade as e:
            raise ProdutoService._traduzir_erro_unicidade(e)
        return produto

    @staticmethod
    def remover(produto_id: int) -> bool:
        if not db.buscar_produto_por_id(produto_id):
            raise ValueError("Produto não encontrado.")
        return db.deletar_produto(produto_id)

    @staticmethod
    def listar(filtro_nome="", filtro_categoria="", filtro_status=""):
        return db.listar_produtos(filtro_nome, filtro_categoria, filtro_status)

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
    def contar_estoque_baixo() -> int:
        return db.contar_estoque_baixo()

    @staticmethod
    def resumo():
        return db.resumo_estoque()


# ═══════════════════════════════════════════════════════════════════════════════
#  Movimentações
# ═══════════════════════════════════════════════════════════════════════════════

class MovimentacaoService:

    @staticmethod
    def entrada(produto_id, quantidade, responsavel="", observacao="",
                usuario_id=None) -> Movimentacao:
        mov = Movimentacao(
            produto_id=produto_id, tipo="entrada", quantidade=quantidade,
            responsavel=responsavel, observacao=observacao, usuario_id=usuario_id,
        )
        db.registrar_movimentacao(mov)
        return mov

    @staticmethod
    def saida(produto_id, quantidade, responsavel="", observacao="",
              setor="", usuario_id=None, exigir_setor=False) -> Movimentacao:
        mov = Movimentacao(
            produto_id=produto_id, tipo="saida", quantidade=quantidade,
            responsavel=responsavel, observacao=observacao, setor=setor,
            usuario_id=usuario_id,
        )
        if exigir_setor and not mov.setor:
            raise ValueError("Informe o setor de destino da saída.")
        db.registrar_movimentacao(mov)
        return mov

    @staticmethod
    def historico(produto_id=None, tipo=None, limite=200, busca=None, setor=None,
                  data_inicio=None, data_fim=None, offset=0):
        return db.listar_movimentacoes(produto_id, tipo, limite, busca, setor,
                                       data_inicio, data_fim, offset)

    @staticmethod
    def contar(produto_id=None, tipo=None, busca=None, setor=None,
               data_inicio=None, data_fim=None) -> int:
        return db.contar_movimentacoes(produto_id, tipo, busca, setor, data_inicio, data_fim)

    @staticmethod
    def setores_usados():
        return db.listar_setores_usados()


# ═══════════════════════════════════════════════════════════════════════════════
#  Painel
# ═══════════════════════════════════════════════════════════════════════════════

class PainelService:

    @staticmethod
    def dados(dias_grafico: int = 14, dias_setor: int = 30) -> dict:
        return {
            "resumo": db.resumo_estoque(),
            "hoje": db.movimentacoes_hoje(),
            "por_dia": db.movimentos_por_dia(dias_grafico),
            "por_setor": db.consumo_por_setor(dias_setor, limite=8),
            "criticos": db.produtos_estoque_baixo()[:6],
            "recentes": db.listar_movimentacoes(limite=6),
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  Usuários e autenticação
# ═══════════════════════════════════════════════════════════════════════════════

MAX_TENTATIVAS = 5
MINUTOS_BLOQUEIO = 10

# Hash usado quando o e-mail não existe, para o tempo de resposta ser igual
# e não revelar quais e-mails estão cadastrados.
_HASH_FICTICIO = generate_password_hash("senha-ficticia-para-comparacao")


class UsuarioService:

    # ── regras de senha ───────────────────────────────────────────────────────
    @staticmethod
    def validar_senha(senha: str, confirmacao: str = None):
        senha = senha or ""
        if len(senha) < 8:
            raise ValueError("A senha precisa ter pelo menos 8 caracteres.")
        if not re.search(r"[A-Za-z]", senha) or not re.search(r"\d", senha):
            raise ValueError("A senha precisa ter letras e números.")
        if confirmacao is not None and senha != confirmacao:
            raise ValueError("A confirmação não confere com a senha.")

    @staticmethod
    def _email_em_uso(email: str, ignorar_id: int = None) -> bool:
        existente = db.buscar_usuario_por_email(email)
        return bool(existente and existente.id != ignorar_id)

    # ── cadastro ──────────────────────────────────────────────────────────────
    @staticmethod
    def precisa_configurar() -> bool:
        """True enquanto nenhum usuário existir (primeiro acesso ao sistema)."""
        return db.contar_usuarios() == 0

    @staticmethod
    def _criar(nome, email, senha, confirmacao, perfil, status, setor="") -> Usuario:
        usuario = Usuario(nome=nome, email=email, perfil=perfil, status=status, setor=setor)
        UsuarioService.validar_senha(senha, confirmacao)
        if UsuarioService._email_em_uso(usuario.email):
            raise ValueError("Esse e-mail já está cadastrado.")
        usuario.senha_hash = generate_password_hash(senha)
        try:
            usuario.id = db.inserir_usuario(usuario)
        except db.ErroUnicidade:
            raise ValueError("Esse e-mail já está cadastrado.")
        return usuario

    @staticmethod
    def criar_primeiro_admin(nome, email, senha, confirmacao) -> Usuario:
        if not UsuarioService.precisa_configurar():
            raise ValueError("O sistema já foi configurado.")
        return UsuarioService._criar(nome, email, senha, confirmacao, "admin", "ativo")

    @staticmethod
    def solicitar_acesso(nome, email, setor, senha, confirmacao) -> Usuario:
        """Cadastro pela tela pública: a conta fica pendente até um admin aprovar."""
        return UsuarioService._criar(nome, email, senha, confirmacao, "almoxarife", "pendente", setor)

    @staticmethod
    def criar_por_admin(nome, email, setor, perfil, senha, confirmacao=None) -> Usuario:
        return UsuarioService._criar(nome, email, senha, confirmacao, perfil, "ativo", setor)

    # ── login ─────────────────────────────────────────────────────────────────
    @staticmethod
    def autenticar(email: str, senha: str) -> Usuario:
        usuario = db.buscar_usuario_por_email(email)
        if not usuario:
            check_password_hash(_HASH_FICTICIO, senha or "")
            raise ValueError("E-mail ou senha incorretos.")

        # Bloqueio vencido: zera o contador antes de conferir a senha
        if usuario.bloqueado_ate and not db.conta_bloqueada(usuario.id):
            db.liberar_bloqueio(usuario.id)
        elif db.conta_bloqueada(usuario.id):
            raise ValueError(
                f"Acesso bloqueado por excesso de tentativas. Tente de novo em {MINUTOS_BLOQUEIO} minutos."
            )

        if not check_password_hash(usuario.senha_hash, senha or ""):
            falha = db.registrar_login_falha(usuario.id, MAX_TENTATIVAS, MINUTOS_BLOQUEIO)
            restantes = MAX_TENTATIVAS - falha["tentativas_falhas"]
            if restantes <= 0:
                raise ValueError(
                    f"Acesso bloqueado por excesso de tentativas. Tente de novo em {MINUTOS_BLOQUEIO} minutos."
                )
            if restantes <= 2:
                raise ValueError(
                    f"E-mail ou senha incorretos. Restam {restantes} tentativa(s) antes do bloqueio."
                )
            raise ValueError("E-mail ou senha incorretos.")

        if usuario.status == "pendente":
            raise ValueError("Sua conta ainda aguarda a aprovação de um administrador.")
        if usuario.status == "inativo":
            raise ValueError("Sua conta está desativada. Fale com o administrador do sistema.")

        db.registrar_login_sucesso(usuario.id)
        return usuario

    # ── consultas ─────────────────────────────────────────────────────────────
    @staticmethod
    def buscar_por_id(usuario_id):
        try:
            return db.buscar_usuario_por_id(int(usuario_id))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def listar():
        return db.listar_usuarios()

    @staticmethod
    def contar_pendentes() -> int:
        return db.contar_usuarios(status="pendente")

    # ── perfil do próprio usuário ─────────────────────────────────────────────
    @staticmethod
    def atualizar_dados(usuario_id, nome, setor) -> Usuario:
        usuario = db.buscar_usuario_por_id(usuario_id)
        if not usuario:
            raise ValueError("Usuário não encontrado.")
        usuario.nome = nome
        usuario.setor = setor
        db.atualizar_usuario(usuario)
        return usuario

    @staticmethod
    def alterar_senha(usuario_id, senha_atual, nova, confirmacao):
        usuario = db.buscar_usuario_por_id(usuario_id)
        if not usuario or not check_password_hash(usuario.senha_hash, senha_atual or ""):
            raise ValueError("A senha atual está incorreta.")
        UsuarioService.validar_senha(nova, confirmacao)
        if check_password_hash(usuario.senha_hash, nova):
            raise ValueError("A nova senha precisa ser diferente da atual.")
        db.atualizar_senha(usuario_id, generate_password_hash(nova))

    # ── administração ─────────────────────────────────────────────────────────
    @staticmethod
    def _garantir_admin_restante(usuario: Usuario, novo_perfil: str, novo_status: str):
        """Impede que o sistema fique sem nenhum administrador ativo."""
        deixa_de_ser_admin_ativo = (
            usuario.perfil == "admin" and usuario.status == "ativo"
            and (novo_perfil != "admin" or novo_status != "ativo")
        )
        if deixa_de_ser_admin_ativo and db.contar_usuarios(perfil="admin", status="ativo") <= 1:
            raise ValueError("O sistema precisa de pelo menos um administrador ativo.")

    @staticmethod
    def editar_por_admin(usuario_id, nome, email, setor, perfil, status,
                         nova_senha="", admin_id=None) -> Usuario:
        usuario = db.buscar_usuario_por_id(usuario_id)
        if not usuario:
            raise ValueError("Usuário não encontrado.")
        if perfil not in PERFIS:
            raise ValueError("Perfil de acesso inválido.")
        if admin_id == usuario.id and status != "ativo":
            raise ValueError("Você não pode desativar a sua própria conta.")
        UsuarioService._garantir_admin_restante(usuario, perfil, status)
        usuario.nome = nome
        usuario.email = email
        usuario.setor = setor
        usuario.perfil = perfil
        usuario.status = status
        if UsuarioService._email_em_uso(usuario.email, ignorar_id=usuario.id):
            raise ValueError("Esse e-mail já está cadastrado.")
        if nova_senha:
            UsuarioService.validar_senha(nova_senha)
        try:
            db.atualizar_usuario(usuario)
        except db.ErroUnicidade:
            raise ValueError("Esse e-mail já está cadastrado.")
        if nova_senha:
            db.atualizar_senha(usuario.id, generate_password_hash(nova_senha))
        return usuario

    @staticmethod
    def aprovar(usuario_id, perfil="almoxarife") -> Usuario:
        usuario = db.buscar_usuario_por_id(usuario_id)
        if not usuario:
            raise ValueError("Usuário não encontrado.")
        usuario.perfil = perfil if perfil in PERFIS else "almoxarife"
        usuario.status = "ativo"
        db.atualizar_usuario(usuario)
        return usuario

    @staticmethod
    def recusar(usuario_id) -> Usuario:
        usuario = db.buscar_usuario_por_id(usuario_id)
        if not usuario or usuario.status != "pendente":
            raise ValueError("Só é possível recusar solicitações pendentes.")
        db.deletar_usuario(usuario.id)
        return usuario

    @staticmethod
    def alternar_status(usuario_id, admin_id) -> Usuario:
        usuario = db.buscar_usuario_por_id(usuario_id)
        if not usuario:
            raise ValueError("Usuário não encontrado.")
        if usuario.id == admin_id:
            raise ValueError("Você não pode desativar a sua própria conta.")
        novo = "inativo" if usuario.status == "ativo" else "ativo"
        UsuarioService._garantir_admin_restante(usuario, usuario.perfil, novo)
        usuario.status = novo
        db.atualizar_usuario(usuario)
        if novo == "ativo":
            db.liberar_bloqueio(usuario.id)
        return usuario


def saudacao(agora: datetime) -> str:
    if agora.hour < 12:
        return "Bom dia"
    if agora.hour < 18:
        return "Boa tarde"
    return "Boa noite"
