import re


def formatar_moeda(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def validar_numero_positivo(valor_str: str, inteiro: bool = False) -> bool:
    try:
        v = int(valor_str) if inteiro else float(valor_str.replace(",", "."))
        return v >= 0
    except (ValueError, AttributeError):
        return False


def so_numeros(texto: str) -> str:
    return re.sub(r"[^\d]", "", texto)
