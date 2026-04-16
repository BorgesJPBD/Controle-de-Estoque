import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from services import ProdutoService, MovimentacaoService
from reports import (relatorio_estoque_completo, relatorio_estoque_baixo,
                     relatorio_movimentacoes, relatorio_resumo_por_categoria)
from utils import formatar_moeda

# ── Paleta hospitalar ─────────────────────────────────────────────────────────
COR_BG       = "#f0f4f8"
COR_SIDEBAR  = "#1a3c5e"
COR_HEADER   = "#2563a8"
COR_BRANCO   = "#ffffff"
COR_ALERTA   = "#e53e3e"
COR_OK       = "#38a169"
COR_TEXTO    = "#1a202c"
COR_SUBTEXTO = "#718096"
FONTE        = ("Segoe UI", 10)
FONTE_BOLD   = ("Segoe UI", 10, "bold")
FONTE_TITULO = ("Segoe UI", 14, "bold")


# ═══════════════════════════════════════════════════════════════════════════════
#  Janela principal
# ═══════════════════════════════════════════════════════════════════════════════
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Almoxarifado Hospitalar")
        self.geometry("1100x680")
        self.minsize(900, 580)
        self.configure(bg=COR_BG)
        self._build_layout()
        self._mostrar_aba(EstoqueFrame)

    def _build_layout(self):
        # sidebar
        self.sidebar = tk.Frame(self, bg=COR_SIDEBAR, width=190)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        tk.Label(self.sidebar, text="🏥 Almoxarifado", bg=COR_SIDEBAR,
                 fg=COR_BRANCO, font=("Segoe UI", 12, "bold"),
                 pady=20).pack(fill="x")
        ttk.Separator(self.sidebar, orient="horizontal").pack(fill="x", padx=10)

        botoes = [
            ("📦  Estoque",        EstoqueFrame),
            ("🔽  Entrada",        EntradaFrame),
            ("🔼  Saída",          SaidaFrame),
            ("📋  Histórico",      HistoricoFrame),
            ("⚠   Alertas",        AlertasFrame),
            ("📊  Relatórios",     RelatoriosFrame),
        ]
        self.btn_refs = []
        for label, frame_cls in botoes:
            btn = tk.Button(
                self.sidebar, text=label, anchor="w", padx=18,
                bg=COR_SIDEBAR, fg=COR_BRANCO, font=FONTE,
                relief="flat", bd=0, activebackground="#2563a8",
                activeforeground=COR_BRANCO, cursor="hand2",
                command=lambda fc=frame_cls: self._mostrar_aba(fc)
            )
            btn.pack(fill="x", ipady=10)
            self.btn_refs.append((btn, frame_cls))

        # área principal
        self.main = tk.Frame(self, bg=COR_BG)
        self.main.pack(side="left", fill="both", expand=True)
        self.frame_atual = None

    def _mostrar_aba(self, frame_cls):
        if self.frame_atual:
            self.frame_atual.destroy()
        self.frame_atual = frame_cls(self.main, self)
        self.frame_atual.pack(fill="both", expand=True)
        # destaca botão ativo
        for btn, fc in self.btn_refs:
            btn.config(bg=COR_HEADER if fc == frame_cls else COR_SIDEBAR)

    def atualizar(self):
        self._mostrar_aba(type(self.frame_atual))


# ═══════════════════════════════════════════════════════════════════════════════
#  Componentes reutilizáveis
# ═══════════════════════════════════════════════════════════════════════════════
def _titulo(parent, texto):
    tk.Label(parent, text=texto, font=FONTE_TITULO,
             bg=COR_BG, fg=COR_HEADER).pack(anchor="w", padx=20, pady=(18, 4))
    ttk.Separator(parent, orient="horizontal").pack(fill="x", padx=20, pady=(0, 10))


def _label_entry(parent, texto, row, col=0, width=28, valor=""):
    tk.Label(parent, text=texto, font=FONTE, bg=COR_BRANCO,
             fg=COR_TEXTO).grid(row=row, column=col, sticky="e", padx=(12, 4), pady=6)
    var = tk.StringVar(value=valor)
    e = ttk.Entry(parent, textvariable=var, width=width)
    e.grid(row=row, column=col + 1, sticky="w", pady=6)
    return var


def _btn(parent, texto, cmd, cor=COR_HEADER):
    return tk.Button(parent, text=texto, command=cmd, font=FONTE_BOLD,
                     bg=cor, fg=COR_BRANCO, relief="flat", padx=14, pady=6,
                     cursor="hand2", activebackground=COR_SIDEBAR,
                     activeforeground=COR_BRANCO)


def _tabela(parent, colunas, alturas=None):
    frame = tk.Frame(parent, bg=COR_BG)
    style = ttk.Style()
    style.configure("Treeview", font=FONTE, rowheight=24)
    style.configure("Treeview.Heading", font=FONTE_BOLD)
    style.map("Treeview", background=[("selected", COR_HEADER)])
    tree = ttk.Treeview(frame, columns=colunas, show="headings",
                        height=alturas or 16)
    vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")
    return frame, tree


# ═══════════════════════════════════════════════════════════════════════════════
#  Aba Estoque
# ═══════════════════════════════════════════════════════════════════════════════
class EstoqueFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=COR_BG)
        self.app = app
        _titulo(self, "📦  Estoque Atual")
        self._barra_acoes()
        self._tabela_estoque()
        self._resumo()
        self._carregar()

    def _barra_acoes(self):
        bar = tk.Frame(self, bg=COR_BG)
        bar.pack(fill="x", padx=20, pady=(0, 8))
        tk.Label(bar, text="Buscar:", bg=COR_BG, font=FONTE).pack(side="left")
        self.var_busca = tk.StringVar()
        self.var_busca.trace_add("write", lambda *_: self._carregar())
        ttk.Entry(bar, textvariable=self.var_busca, width=22).pack(side="left", padx=6)
        tk.Label(bar, text="Categoria:", bg=COR_BG, font=FONTE).pack(side="left", padx=(12, 4))
        self.var_cat = tk.StringVar(value="Todas")
        self.cb_cat = ttk.Combobox(bar, textvariable=self.var_cat, width=16, state="readonly")
        self.cb_cat.pack(side="left")
        self.cb_cat.bind("<<ComboboxSelected>>", lambda _: self._carregar())
        _btn(bar, "+ Novo Produto", self._novo).pack(side="right")
        _btn(bar, "✏ Editar", self._editar, "#4a5568").pack(side="right", padx=6)
        _btn(bar, "🗑 Remover", self._remover, COR_ALERTA).pack(side="right")
        self._atualizar_cats()

    def _tabela_estoque(self):
        cols = ("ID", "Nome", "Categoria", "Unidade", "Preço", "Qtd", "Mín.", "Valor Total", "Status")
        frame, self.tree = _tabela(self, cols)
        frame.pack(fill="both", expand=True, padx=20)
        larguras = [40, 200, 120, 60, 80, 60, 60, 100, 80]
        for col, larg in zip(cols, larguras):
            self.tree.heading(col, text=col, command=lambda c=col: self._ordenar(c))
            self.tree.column(col, width=larg, anchor="center" if col not in ("Nome", "Categoria") else "w")
        self.tree.tag_configure("baixo", foreground=COR_ALERTA)
        self.tree.tag_configure("ok", foreground=COR_OK)

    def _resumo(self):
        self.frame_resumo = tk.Frame(self, bg=COR_HEADER)
        self.frame_resumo.pack(fill="x", padx=20, pady=8)
        self.lbl_resumo = tk.Label(self.frame_resumo, text="", bg=COR_HEADER,
                                   fg=COR_BRANCO, font=FONTE_BOLD, pady=6)
        self.lbl_resumo.pack()

    def _carregar(self):
        busca = self.var_busca.get()
        cat = self.var_cat.get()
        cat = "" if cat == "Todas" else cat
        produtos = ProdutoService.listar(busca, cat)
        self.tree.delete(*self.tree.get_children())
        for p in produtos:
            tag = "baixo" if p.estoque_baixo else "ok"
            status = "⚠ BAIXO" if p.estoque_baixo else "✔ OK"
            self.tree.insert("", "end", iid=str(p.id), tags=(tag,), values=(
                p.id, p.nome, p.categoria, p.unidade,
                formatar_moeda(p.preco), p.quantidade, p.estoque_minimo,
                formatar_moeda(p.valor_total), status
            ))
        r = ProdutoService.resumo()
        total = r["total_produtos"] or 0
        itens = r["total_itens"] or 0
        valor = r["valor_total"] or 0
        self.lbl_resumo.config(
            text=f"Produtos: {total}   |   Total de unidades: {itens}   |   Valor em estoque: {formatar_moeda(valor)}"
        )

    def _atualizar_cats(self):
        cats = ["Todas"] + ProdutoService.categorias()
        self.cb_cat["values"] = cats

    def _novo(self):
        FormProduto(self, self.app)

    def _editar(self):
        sel = self.tree.focus()
        if not sel:
            messagebox.showwarning("Aviso", "Selecione um produto.")
            return
        FormProduto(self, self.app, produto_id=int(sel))

    def _remover(self):
        sel = self.tree.focus()
        if not sel:
            messagebox.showwarning("Aviso", "Selecione um produto.")
            return
        p = ProdutoService.buscar_por_id(int(sel))
        if messagebox.askyesno("Confirmar", f"Remover '{p.nome}'?"):
            try:
                ProdutoService.remover(int(sel))
                self._carregar()
                self._atualizar_cats()
            except Exception as e:
                messagebox.showerror("Erro", str(e))

    def _ordenar(self, col):
        pass  # extensível


# ═══════════════════════════════════════════════════════════════════════════════
#  Formulário Produto (novo / editar)
# ═══════════════════════════════════════════════════════════════════════════════
class FormProduto(tk.Toplevel):
    def __init__(self, parent_frame, app, produto_id=None):
        super().__init__()
        self.app = app
        self.parent_frame = parent_frame
        self.produto_id = produto_id
        self.title("Editar Produto" if produto_id else "Novo Produto")
        self.resizable(False, False)
        self.configure(bg=COR_BRANCO)
        self.grab_set()
        self._build()
        if produto_id:
            self._preencher()

    def _build(self):
        f = tk.Frame(self, bg=COR_BRANCO, padx=20, pady=16)
        f.pack()
        self.v_nome  = _label_entry(f, "Nome *",            0, width=32)
        self.v_cat   = _label_entry(f, "Categoria",         1, width=32)
        self.v_un    = _label_entry(f, "Unidade *",         2, width=10, valor="UN")
        self.v_preco = _label_entry(f, "Preço (R$) *",      3, width=16)
        self.v_qtd   = _label_entry(f, "Quantidade inicial",4, width=10, valor="0")
        self.v_min   = _label_entry(f, "Estoque mínimo",    5, width=10, valor="5")

        tk.Label(f, text="* obrigatório", fg=COR_SUBTEXTO,
                 bg=COR_BRANCO, font=("Segoe UI", 8)).grid(
            row=6, column=0, columnspan=2, sticky="e", pady=(4, 0))

        bar = tk.Frame(f, bg=COR_BRANCO)
        bar.grid(row=7, column=0, columnspan=2, pady=12)
        _btn(bar, "Salvar", self._salvar).pack(side="left", padx=6)
        _btn(bar, "Cancelar", self.destroy, "#718096").pack(side="left")

    def _preencher(self):
        p = ProdutoService.buscar_por_id(self.produto_id)
        self.v_nome.set(p.nome)
        self.v_cat.set(p.categoria)
        self.v_un.set(p.unidade)
        self.v_preco.set(str(p.preco).replace(".", ","))
        self.v_qtd.set(str(p.quantidade))
        self.v_min.set(str(p.estoque_minimo))

    def _salvar(self):
        try:
            preco = float(self.v_preco.get().replace(",", "."))
            qtd   = int(self.v_qtd.get())
            mn    = int(self.v_min.get())
            if self.produto_id:
                ProdutoService.editar(
                    self.produto_id,
                    self.v_nome.get(), self.v_cat.get(),
                    self.v_un.get(), preco, mn
                )
            else:
                ProdutoService.criar(
                    self.v_nome.get(), self.v_cat.get(),
                    self.v_un.get(), preco, qtd, mn
                )
            self.parent_frame._carregar()
            self.parent_frame._atualizar_cats()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Erro", str(e), parent=self)


# ═══════════════════════════════════════════════════════════════════════════════
#  Aba Entrada
# ═══════════════════════════════════════════════════════════════════════════════
class EntradaFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=COR_BG)
        self.app = app
        _titulo(self, "🔽  Registrar Entrada")
        self._build()

    def _build(self):
        card = tk.Frame(self, bg=COR_BRANCO, padx=24, pady=20,
                        relief="groove", bd=1)
        card.pack(padx=40, pady=20, anchor="nw")

        tk.Label(card, text="Produto *", bg=COR_BRANCO, font=FONTE).grid(
            row=0, column=0, sticky="e", padx=8, pady=8)
        self.var_prod = tk.StringVar()
        self.cb_prod = ttk.Combobox(card, textvariable=self.var_prod,
                                    width=36, state="readonly")
        self.cb_prod.grid(row=0, column=1, sticky="w", pady=8)
        self._carregar_produtos()

        self.v_qtd  = _label_entry(card, "Quantidade *", 1, width=12)
        self.v_resp = _label_entry(card, "Responsável",  2, width=30)
        self.v_obs  = _label_entry(card, "Observação",   3, width=36)

        _btn(card, "✔ Confirmar Entrada", self._salvar, COR_OK).grid(
            row=4, column=0, columnspan=2, pady=14)

    def _carregar_produtos(self):
        prods = ProdutoService.listar()
        self._mapa = {f"[{p.id}] {p.nome}": p.id for p in prods}
        self.cb_prod["values"] = list(self._mapa.keys())

    def _salvar(self):
        chave = self.var_prod.get()
        if not chave:
            messagebox.showwarning("Aviso", "Selecione um produto.")
            return
        try:
            produto_id = self._mapa[chave]
            qtd = int(self.v_qtd.get())
            MovimentacaoService.entrada(
                produto_id, qtd,
                self.v_resp.get(), self.v_obs.get()
            )
            messagebox.showinfo("Sucesso", f"Entrada de {qtd} unidade(s) registrada.")
            self.v_qtd.set(""); self.v_resp.set(""); self.v_obs.set("")
        except Exception as e:
            messagebox.showerror("Erro", str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  Aba Saída
# ═══════════════════════════════════════════════════════════════════════════════
class SaidaFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=COR_BG)
        self.app = app
        _titulo(self, "🔼  Registrar Saída")
        self._build()

    def _build(self):
        card = tk.Frame(self, bg=COR_BRANCO, padx=24, pady=20,
                        relief="groove", bd=1)
        card.pack(padx=40, pady=20, anchor="nw")

        tk.Label(card, text="Produto *", bg=COR_BRANCO, font=FONTE).grid(
            row=0, column=0, sticky="e", padx=8, pady=8)
        self.var_prod = tk.StringVar()
        self.cb_prod = ttk.Combobox(card, textvariable=self.var_prod,
                                    width=36, state="readonly")
        self.cb_prod.grid(row=0, column=1, sticky="w", pady=8)
        self._carregar_produtos()

        self.v_qtd  = _label_entry(card, "Quantidade *", 1, width=12)
        self.v_resp = _label_entry(card, "Responsável",  2, width=30)
        self.v_obs  = _label_entry(card, "Observação",   3, width=36)

        _btn(card, "✔ Confirmar Saída", self._salvar, COR_ALERTA).grid(
            row=4, column=0, columnspan=2, pady=14)

    def _carregar_produtos(self):
        prods = ProdutoService.listar()
        self._mapa = {f"[{p.id}] {p.nome}": p.id for p in prods}
        self.cb_prod["values"] = list(self._mapa.keys())

    def _salvar(self):
        chave = self.var_prod.get()
        if not chave:
            messagebox.showwarning("Aviso", "Selecione um produto.")
            return
        try:
            produto_id = self._mapa[chave]
            qtd = int(self.v_qtd.get())
            MovimentacaoService.saida(
                produto_id, qtd,
                self.v_resp.get(), self.v_obs.get()
            )
            messagebox.showinfo("Sucesso", f"Saída de {qtd} unidade(s) registrada.")
            self.v_qtd.set(""); self.v_resp.set(""); self.v_obs.set("")
        except Exception as e:
            messagebox.showerror("Erro", str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  Aba Histórico
# ═══════════════════════════════════════════════════════════════════════════════
class HistoricoFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=COR_BG)
        self.app = app
        _titulo(self, "📋  Histórico de Movimentações")
        self._filtros()
        self._tabela()
        self._carregar()

    def _filtros(self):
        bar = tk.Frame(self, bg=COR_BG)
        bar.pack(fill="x", padx=20, pady=(0, 8))
        tk.Label(bar, text="Produto:", bg=COR_BG, font=FONTE).pack(side="left")
        self.var_prod = tk.StringVar(value="Todos")
        self.cb_prod = ttk.Combobox(bar, textvariable=self.var_prod, width=28, state="readonly")
        self.cb_prod.pack(side="left", padx=6)
        self._carregar_prods()
        tk.Label(bar, text="Tipo:", bg=COR_BG, font=FONTE).pack(side="left", padx=(12, 4))
        self.var_tipo = tk.StringVar(value="Todos")
        ttk.Combobox(bar, textvariable=self.var_tipo, width=12, state="readonly",
                     values=["Todos", "entrada", "saida"]).pack(side="left")
        _btn(bar, "🔍 Filtrar", self._carregar).pack(side="left", padx=12)

    def _carregar_prods(self):
        prods = ProdutoService.listar()
        self._mapa = {"Todos": None}
        self._mapa.update({f"[{p.id}] {p.nome}": p.id for p in prods})
        self.cb_prod["values"] = list(self._mapa.keys())

    def _tabela(self):
        cols = ("ID", "Produto", "Tipo", "Qtd", "Responsável", "Observação", "Data")
        frame, self.tree = _tabela(self, cols, alturas=18)
        frame.pack(fill="both", expand=True, padx=20)
        larguras = [40, 200, 80, 60, 140, 200, 140]
        for col, larg in zip(cols, larguras):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=larg, anchor="w" if col in ("Produto", "Responsável", "Observação") else "center")
        self.tree.tag_configure("entrada", foreground=COR_OK)
        self.tree.tag_configure("saida",   foreground=COR_ALERTA)

    def _carregar(self):
        chave = self.var_prod.get()
        pid = self._mapa.get(chave)
        tipo = self.var_tipo.get()
        tipo = None if tipo == "Todos" else tipo
        movs = MovimentacaoService.historico(pid, tipo)
        self.tree.delete(*self.tree.get_children())
        for m in movs:
            self.tree.insert("", "end", tags=(m["tipo"],), values=(
                m["id"], m["produto_nome"], m["tipo"].capitalize(),
                m["quantidade"], m["responsavel"], m["observacao"], m["data"]
            ))


# ═══════════════════════════════════════════════════════════════════════════════
#  Aba Alertas
# ═══════════════════════════════════════════════════════════════════════════════
class AlertasFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=COR_BG)
        self.app = app
        _titulo(self, "⚠   Produtos com Estoque Baixo")
        self._build()

    def _build(self):
        cols = ("ID", "Nome", "Categoria", "Unidade", "Qtd Atual", "Estoque Mín.")
        frame, self.tree = _tabela(self, cols, alturas=18)
        frame.pack(fill="both", expand=True, padx=20, pady=10)
        larguras = [40, 220, 140, 70, 100, 120]
        for col, larg in zip(cols, larguras):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=larg, anchor="center" if col not in ("Nome", "Categoria") else "w")
        self.tree.tag_configure("alerta", foreground=COR_ALERTA, font=FONTE_BOLD)
        prods = ProdutoService.estoque_baixo()
        for p in prods:
            self.tree.insert("", "end", tags=("alerta",),
                             values=(p.id, p.nome, p.categoria, p.unidade,
                                     p.quantidade, p.estoque_minimo))
        if not prods:
            tk.Label(self, text="✔  Todos os produtos estão com estoque adequado.",
                     bg=COR_BG, fg=COR_OK, font=FONTE_BOLD).pack(pady=20)


# ═══════════════════════════════════════════════════════════════════════════════
#  Aba Relatórios
# ═══════════════════════════════════════════════════════════════════════════════
class RelatoriosFrame(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=COR_BG)
        self.app = app
        _titulo(self, "📊  Exportar Relatórios")
        self._build()
        self.lbl_status = tk.Label(self, text="", bg=COR_BG, fg=COR_OK, font=FONTE_BOLD)
        self.lbl_status.pack(pady=8)

    def _build(self):
        cards = [
            ("📋  Estoque Completo",
             "Todos os produtos com preços, quantidades e status.",
             self._rel_completo),
            ("⚠   Estoque Baixo",
             "Apenas produtos abaixo do mínimo.",
             self._rel_baixo),
            ("🔄  Movimentações",
             "Histórico completo de entradas e saídas.",
             self._rel_movs),
            ("📂  Resumo por Categoria",
             "Totalizadores agrupados por categoria.",
             self._rel_cat),
        ]
        grid = tk.Frame(self, bg=COR_BG)
        grid.pack(padx=30, pady=10, anchor="nw")
        for i, (titulo, desc, cmd) in enumerate(cards):
            card = tk.Frame(grid, bg=COR_BRANCO, relief="groove", bd=1,
                            padx=20, pady=16, width=220)
            card.grid(row=i // 2, column=i % 2, padx=12, pady=10, sticky="nsew")
            tk.Label(card, text=titulo, bg=COR_BRANCO, font=FONTE_BOLD,
                     fg=COR_HEADER).pack(anchor="w")
            tk.Label(card, text=desc, bg=COR_BRANCO, font=("Segoe UI", 9),
                     fg=COR_SUBTEXTO, wraplength=200, justify="left").pack(anchor="w", pady=6)
            _btn(card, "⬇ Exportar CSV", cmd).pack(anchor="w")

    def _mostrar(self, caminho):
        self.lbl_status.config(
            text=f"✔ Relatório salvo em:\n{caminho}", fg=COR_OK)
        if messagebox.askyesno("Abrir pasta?",
                               "Deseja abrir a pasta onde o arquivo foi salvo?"):
            pasta = os.path.dirname(caminho)
            os.startfile(pasta) if os.name == "nt" else os.system(f'xdg-open "{pasta}"')

    def _rel_completo(self):
        self._mostrar(relatorio_estoque_completo())

    def _rel_baixo(self):
        self._mostrar(relatorio_estoque_baixo())

    def _rel_movs(self):
        self._mostrar(relatorio_movimentacoes())

    def _rel_cat(self):
        self._mostrar(relatorio_resumo_por_categoria())
