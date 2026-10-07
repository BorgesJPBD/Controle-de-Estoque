import os
import re
from datetime import date, datetime
from zoneinfo import ZoneInfo


# Fuso do hospital (Mato Grosso do Sul por padrão). Mude com a variável TZ_APP.
FUSO = ZoneInfo(os.environ.get("TZ_APP", "America/Campo_Grande"))


def agora() -> datetime:
    return datetime.now(FUSO)


# Sugestões exibidas nos formulários (o usuário também pode digitar outro valor).
SETORES_HOSPITALARES = [
    "Ambulatório", "Centro Cirúrgico", "Centro Obstétrico", "Central de Material (CME)",
    "Enfermaria Clínica", "Enfermaria Cirúrgica", "Farmácia", "Hemodiálise",
    "Laboratório", "Maternidade", "Pediatria", "Pronto-Socorro", "Radiologia",
    "UTI Adulto", "UTI Neonatal", "Administração",
]

UNIDADES_MEDIDA = [
    ("UN", "Unidade"), ("CX", "Caixa"), ("PCT", "Pacote"), ("PAR", "Par"),
    ("FR", "Frasco"), ("AMP", "Ampola"), ("BOLSA", "Bolsa"), ("RL", "Rolo"),
    ("L", "Litro"), ("ML", "Mililitro"), ("KG", "Quilo"), ("G", "Grama"),
]


def formatar_moeda(valor: float) -> str:
    return f"R$ {float(valor or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_numero(valor) -> str:
    """1234 -> '1.234'"""
    try:
        return f"{int(valor):,}".replace(",", ".")
    except (TypeError, ValueError):
        return str(valor)


def _para_datetime(valor):
    if valor is None or valor == "":
        return None
    if isinstance(valor, (datetime, date)):
        return valor
    texto = str(valor)
    for formato in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(texto, formato)
        except ValueError:
            continue
    return None


def formatar_data(valor) -> str:
    dt = _para_datetime(valor)
    return dt.strftime("%d/%m/%Y") if dt else ""


def formatar_data_hora(valor) -> str:
    dt = _para_datetime(valor)
    if not dt:
        return ""
    if isinstance(dt, datetime):
        return dt.strftime("%d/%m/%Y %H:%M")
    return dt.strftime("%d/%m/%Y")


def formatar_quando(valor) -> str:
    """Data curta e relativa: 'hoje, 14:20', 'ontem, 09:05' ou '03/10, 16:40'."""
    dt = _para_datetime(valor)
    if not isinstance(dt, datetime):
        return formatar_data(valor)
    hoje = agora().date()
    if dt.date() == hoje:
        return f"hoje, {dt:%H:%M}"
    if (hoje - dt.date()).days == 1:
        return f"ontem, {dt:%H:%M}"
    if dt.year == hoje.year:
        return f"{dt:%d/%m}, {dt:%H:%M}"
    return f"{dt:%d/%m/%Y}, {dt:%H:%M}"


DIAS_SEMANA = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
               "sexta-feira", "sábado", "domingo"]
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]


def formatar_data_extenso(valor) -> str:
    """datetime -> 'Quarta-feira, 7 de outubro de 2026'"""
    dt = _para_datetime(valor)
    if not dt:
        return ""
    texto = f"{DIAS_SEMANA[dt.weekday()]}, {dt.day} de {MESES[dt.month - 1]} de {dt.year}"
    return texto[0].upper() + texto[1:]


def validar_numero_positivo(valor_str: str, inteiro: bool = False) -> bool:
    try:
        v = int(valor_str) if inteiro else float(valor_str.replace(",", "."))
        return v >= 0
    except (ValueError, AttributeError):
        return False


def so_numeros(texto: str) -> str:
    return re.sub(r"[^\d]", "", texto)
