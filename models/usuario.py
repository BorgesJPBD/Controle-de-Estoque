import re


PERFIS = {
    "admin": "Administrador",
    "almoxarife": "Almoxarife",
}

STATUS = {
    "pendente": "Aguardando aprovação",
    "ativo": "Ativo",
    "inativo": "Desativado",
}

_EMAIL_VALIDO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Usuario:
    """Usuário do sistema.

    Implementa a interface que o Flask-Login espera (is_authenticated,
    is_active, is_anonymous e get_id) sem depender do framework.
    """

    def __init__(self, nome: str, email: str, perfil: str = "almoxarife",
                 status: str = "pendente", setor: str = "",
                 usuario_id: int = None, senha_hash: str = None,
                 criado_em=None, ultimo_acesso=None,
                 tentativas_falhas: int = 0, bloqueado_ate=None):
        self._id = usuario_id
        self._nome = None
        self._email = None
        self._perfil = None
        self._status = None
        self._setor = None
        self.senha_hash = senha_hash
        self.criado_em = criado_em
        self.ultimo_acesso = ultimo_acesso
        self.tentativas_falhas = tentativas_falhas or 0
        self.bloqueado_ate = bloqueado_ate

        self.nome = nome
        self.email = email
        self.perfil = perfil
        self.status = status
        self.setor = setor

    # ── id ────────────────────────────────────────────────────────────────────
    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = value

    # ── nome ──────────────────────────────────────────────────────────────────
    @property
    def nome(self):
        return self._nome

    @nome.setter
    def nome(self, value: str):
        value = " ".join((value or "").split())
        if len(value) < 3:
            raise ValueError("Informe o nome completo (mínimo de 3 letras).")
        if len(value) > 100:
            raise ValueError("O nome deve ter no máximo 100 caracteres.")
        self._nome = value

    # ── e-mail ────────────────────────────────────────────────────────────────
    @property
    def email(self):
        return self._email

    @email.setter
    def email(self, value: str):
        value = (value or "").strip().lower()
        if not _EMAIL_VALIDO.match(value) or len(value) > 150:
            raise ValueError("Informe um e-mail válido.")
        self._email = value

    # ── perfil ────────────────────────────────────────────────────────────────
    @property
    def perfil(self):
        return self._perfil

    @perfil.setter
    def perfil(self, value: str):
        if value not in PERFIS:
            raise ValueError("Perfil de acesso inválido.")
        self._perfil = value

    # ── status ────────────────────────────────────────────────────────────────
    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value: str):
        if value not in STATUS:
            raise ValueError("Situação da conta inválida.")
        self._status = value

    # ── setor ─────────────────────────────────────────────────────────────────
    @property
    def setor(self):
        return self._setor

    @setor.setter
    def setor(self, value: str):
        value = " ".join((value or "").split())
        if len(value) > 60:
            raise ValueError("O setor deve ter no máximo 60 caracteres.")
        self._setor = value

    # ── helpers de exibição ───────────────────────────────────────────────────
    @property
    def is_admin(self) -> bool:
        return self._perfil == "admin"

    @property
    def perfil_nome(self) -> str:
        return PERFIS.get(self._perfil, self._perfil)

    @property
    def status_nome(self) -> str:
        return STATUS.get(self._status, self._status)

    @property
    def primeiro_nome(self) -> str:
        return self._nome.split()[0]

    @property
    def iniciais(self) -> str:
        partes = self._nome.split()
        if len(partes) == 1:
            return partes[0][:2].upper()
        return (partes[0][0] + partes[-1][0]).upper()

    # ── interface do Flask-Login ──────────────────────────────────────────────
    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_active(self) -> bool:
        return self._status == "ativo"

    @property
    def is_anonymous(self) -> bool:
        return False

    def get_id(self) -> str:
        return str(self._id)

    def to_dict(self) -> dict:
        return {
            "id": self._id,
            "nome": self._nome,
            "email": self._email,
            "perfil": self._perfil,
            "status": self._status,
            "setor": self._setor,
            "senha_hash": self.senha_hash,
        }

    def __repr__(self):
        return f"Usuario(id={self._id}, email='{self._email}', perfil='{self._perfil}')"
