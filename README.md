# Almoxarifado Hospitalar

Sistema de controle de estoque para almoxarifado hospitalar com interface gráfica (Tkinter) e banco de dados SQLite.

## Estrutura do projeto

```
almoxarifado/
├── main.py                  ← ponto de entrada
├── almoxarifado.db          ← banco criado automaticamente
├── relatorios/              ← CSVs exportados
│
├── models/
│   ├── produto.py           ← classe Produto (getters/setters)
│   └── movimentacao.py      ← classe Movimentacao (getters/setters)
│
├── database/
│   └── db.py                ← toda a comunicação com SQLite
│
├── services/
│   └── service.py           ← regras de negócio
│
├── reports/
│   └── relatorios.py        ← geração de CSVs
│
├── ui/
│   └── app.py               ← interface Tkinter
│
└── utils/
    └── helpers.py           ← funções auxiliares
```

## Requisitos

- Python 3.8+
- Biblioteca padrão apenas (tkinter, sqlite3, csv — sem pip necessário)

## Como executar

```bash
python main.py
```

## Funcionalidades

| Aba           | Descrição                                              |
|---------------|--------------------------------------------------------|
| Estoque       | Lista todos os produtos, busca, filtro por categoria   |
| Entrada       | Registra entrada de itens com responsável              |
| Saída         | Registra saída com validação de quantidade disponível  |
| Histórico     | Exibe todas as movimentações com filtros               |
| Alertas       | Lista produtos abaixo do estoque mínimo                |
| Relatórios    | Exporta 4 tipos de CSV para a pasta `relatorios/`      |

## Relatórios disponíveis

1. **Estoque completo** — todos os produtos com status
2. **Estoque baixo** — apenas itens críticos
3. **Movimentações** — histórico completo de entradas/saídas
4. **Resumo por categoria** — totalizadores agrupados

Os arquivos CSV usam separador `;` e encoding `UTF-8 BOM` para abrir corretamente no Excel.
