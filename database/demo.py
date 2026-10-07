"""Dados de demonstração: um almoxarifado hospitalar com 4 semanas de histórico.

Usado pelo botão "Carregar dados de demonstração" (só aparece para o
administrador enquanto não houver nenhum produto cadastrado).
"""
import random

from .db import _cursor


# (código, nome, categoria, unidade, preço, estoque mínimo, situação final desejada)
PRODUTOS = [
    ("LUV-PROC-M", "Luva de procedimento M (cx 100)", "EPI", "CX", 32.90, 40, "critico"),
    ("LUV-PROC-G", "Luva de procedimento G (cx 100)", "EPI", "CX", 32.90, 30, "normal"),
    ("MASC-N95", "Máscara N95/PFF2", "EPI", "UN", 3.80, 200, "atencao"),
    ("MASC-CIR", "Máscara cirúrgica tripla (cx 50)", "EPI", "CX", 18.50, 60, "normal"),
    ("AVT-DESC", "Avental descartável manga longa", "EPI", "UN", 4.20, 150, "normal"),
    ("TOUCA-100", "Touca descartável (pct 100)", "EPI", "PCT", 15.90, 20, "normal"),
    ("GAZE-EST", "Compressa de gaze estéril 7,5 x 7,5", "Curativos", "PCT", 2.10, 300, "critico"),
    ("ATAD-10", "Atadura de crepe 10 cm", "Curativos", "UN", 1.35, 120, "normal"),
    ("ESPAR-10", "Esparadrapo 10 cm x 4,5 m", "Curativos", "RL", 6.90, 40, "atencao"),
    ("MICROP-25", "Fita microporosa 25 mm", "Curativos", "RL", 4.50, 50, "normal"),
    ("SER-05", "Seringa descartável 5 ml", "Descartáveis", "UN", 0.38, 800, "normal"),
    ("SER-10", "Seringa descartável 10 ml", "Descartáveis", "UN", 0.52, 500, "normal"),
    ("AGU-25X7", "Agulha hipodérmica 25 x 7", "Descartáveis", "UN", 0.14, 1000, "normal"),
    ("CAT-22G", "Cateter intravenoso 22G", "Descartáveis", "UN", 1.90, 200, "critico"),
    ("EQP-MACRO", "Equipo macrogotas", "Descartáveis", "UN", 2.60, 250, "normal"),
    ("SF-500", "Soro fisiológico 0,9% 500 ml", "Soluções", "BOLSA", 4.80, 300, "atencao"),
    ("SG-500", "Soro glicosado 5% 500 ml", "Soluções", "BOLSA", 5.10, 150, "normal"),
    ("ALC-70", "Álcool 70% 1 L", "Antissépticos", "FR", 9.90, 60, "normal"),
    ("CLX-05", "Clorexidina alcoólica 0,5% 1 L", "Antissépticos", "FR", 28.00, 25, "critico"),
    ("PAP-TOA", "Papel toalha interfolha (pct 1000 fl)", "Higiene", "PCT", 11.50, 80, "normal"),
]

SETORES = [
    ("UTI Adulto", 5), ("Centro Cirúrgico", 5), ("Pronto-Socorro", 6),
    ("Enfermaria Clínica", 4), ("Pediatria", 2), ("Maternidade", 2),
    ("Ambulatório", 2), ("Laboratório", 1),
]

RESPONSAVEIS = ["Maria Souza", "Carlos Lima", "Ana Ribeiro"]

DIAS = 28


def _momento_valido(eventos, indice, quantidade, inicial, rnd) -> int:
    """Escolhe um horário nos últimos 3 dias em que a saída extra não deixa
    o estoque negativo em nenhum momento; se não houver, usa os últimos minutos."""
    do_produto = sorted((e for e in eventos if e[1] == indice), key=lambda e: -e[0])
    for _ in range(30):
        momento = rnd.randint(20, 3 * 1440)
        saldo, valido = inicial, True
        linha = sorted(do_produto + [(momento, indice, "saida", quantidade, "")], key=lambda e: -e[0])
        for minutos, _, tipo, qtd, _ in linha:
            saldo += qtd if tipo == "entrada" else -qtd
            if saldo < 0:
                valido = False
                break
        if valido:
            return momento
    return 5


def carregar(usuario_id: int = None, responsavel: str = "") -> int:
    """Cria produtos e movimentações. Retorna quantos produtos foram criados."""
    rnd = random.Random(2026)
    setores = [s for s, peso in SETORES for _ in range(peso)]

    with _cursor() as cur:
        cur.execute("SELECT COUNT(*) AS total FROM produtos")
        if cur.fetchone()["total"] > 0:
            raise ValueError("Os dados de demonstração só podem ser carregados com o estoque vazio.")

        eventos = []      # (minutos atrás, índice do produto, tipo, quantidade, setor)
        estoque = []
        for i, (*_, minimo, alvo) in enumerate(PRODUTOS):
            estoque.append(int(minimo * rnd.uniform(2.4, 3.2)))
            consumo_dia = minimo / rnd.uniform(5, 9)
            for dia in range(DIAS, -1, -1):
                # saídas do dia (de 0 a 2 por produto)
                for _ in range(rnd.choice([0, 1, 1, 2])):
                    qtd = max(1, int(consumo_dia * rnd.uniform(0.5, 1.4)))
                    minutos = dia * 1440 + rnd.randint(30, 600)
                    eventos.append((minutos, i, "saida", qtd, rnd.choice(setores)))
                # reposição semanal; os itens que vão terminar críticos perdem a última
                if dia % 7 == 3 and not (alvo == "critico" and dia < 7):
                    minutos = dia * 1440 + rnd.randint(600, 700)
                    eventos.append((minutos, i, "entrada", int(minimo * 1.8), ""))

        # Simula em ordem cronológica, ignorando saídas que faltariam estoque
        eventos.sort(key=lambda e: -e[0])
        validos = []
        saldo = list(estoque)
        menor_saldo = list(estoque)
        for minutos, i, tipo, qtd, setor in eventos:
            if tipo == "saida":
                if qtd > saldo[i]:
                    continue
                saldo[i] -= qtd
            else:
                # só repõe quem está abaixo de 2x o mínimo
                if saldo[i] >= PRODUTOS[i][5] * 2:
                    continue
                saldo[i] += qtd
            menor_saldo[i] = min(menor_saldo[i], saldo[i])
            validos.append((minutos, i, tipo, qtd, setor))

        # Ajuste para cada produto terminar na situação planejada: primeiro
        # muda o estoque inicial (invisível no histórico); o que sobrar vira
        # pequenas saídas nas últimas horas.
        for i, (*_, minimo, alvo) in enumerate(PRODUTOS):
            if alvo == "critico":
                desejado = int(minimo * rnd.uniform(0.3, 0.85))
            elif alvo == "atencao":
                desejado = int(minimo * rnd.uniform(1.1, 1.4))
            else:
                desejado = max(saldo[i], int(minimo * rnd.uniform(1.9, 2.8)))
            diferenca = saldo[i] - desejado
            if diferenca < 0:
                saldo[i] = desejado
                continue
            deslocamento = min(diferenca, menor_saldo[i])
            resto = diferenca - deslocamento
            saldo[i] = desejado
            if resto > 0:
                validos.append((_momento_valido(validos, i, resto, estoque[i] - deslocamento, rnd),
                                i, "saida", resto, rnd.choice(setores)))

        # Grava produtos
        ids = []
        for (codigo, nome, categoria, unidade, preco, minimo, _), qtd in zip(PRODUTOS, saldo):
            cur.execute(
                """INSERT INTO produtos (codigo, nome, categoria, unidade, preco, quantidade,
                                         estoque_minimo, criado_em)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, NOW() - make_interval(days => %s))
                   RETURNING id""",
                (codigo, nome, categoria, unidade, preco, qtd, minimo, DIAS + 1),
            )
            ids.append(cur.fetchone()["id"])

        # Grava movimentações (a data é calculada pelo banco, no fuso correto)
        for minutos, i, tipo, qtd, setor in validos:
            if tipo == "entrada":
                obs = rnd.choice(["Reposição semanal", "NF recebida do fornecedor", ""])
            else:
                obs = rnd.choice(["", "", "Requisição do setor", "Reposição do carrinho de emergência"])
            # o histórico de exemplo fica em nome de funcionários fictícios
            resp, uid = rnd.choice(RESPONSAVEIS), None
            cur.execute(
                """INSERT INTO movimentacoes
                       (produto_id, tipo, quantidade, responsavel, observacao, setor, usuario_id, data)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, NOW() - make_interval(mins => %s))""",
                (ids[i], tipo, qtd, resp, obs, setor, uid, minutos),
            )
    return len(PRODUTOS)
