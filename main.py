import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog, ttk
import sqlite3
import bcrypt
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import requests
from dateutil.relativedelta import relativedelta  # pip install python-dateutil se necessário
import logging

logging.basicConfig(level=logging.INFO)

# Inicializar banco de dados
conn = sqlite3.connect('financas_pessoais.db')
cursor = conn.cursor()

# Criar tabela de usuários se não existir
cursor.execute('''
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash BLOB NOT NULL
)
''')

# Criar tabela de transações se não existir
cursor.execute('''
CREATE TABLE IF NOT EXISTS transacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    tipo TEXT NOT NULL,  -- 'receita' ou 'despesa'
    valor REAL NOT NULL,
    categoria TEXT NOT NULL,
    descricao TEXT,
    data TEXT NOT NULL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
)
''')

# Tabela para orçamentos
cursor.execute('''
CREATE TABLE IF NOT EXISTS orcamentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    categoria TEXT NOT NULL,
    limite REAL NOT NULL,
    mes_ano TEXT NOT NULL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
    UNIQUE(usuario_id, categoria, mes_ano)
)
''')

# Tabela para investimentos
cursor.execute('''
CREATE TABLE IF NOT EXISTS investimentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL,
    simbolo TEXT NOT NULL,
    quantidade REAL NOT NULL,
    custo_medio REAL NOT NULL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
    UNIQUE(usuario_id, simbolo)
)
''')

# Tabela para chave API (persistida por usuário)
cursor.execute('''
CREATE TABLE IF NOT EXISTS config_api (
    usuario_id INTEGER PRIMARY KEY,
    api_key TEXT,
    FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
)
''')

# Adicionar índice para data
cursor.execute('CREATE INDEX IF NOT EXISTS idx_data ON transacoes(data)')

conn.commit()

# Função para hash de senha
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

# Função para cadastrar usuário
def cadastrar_usuario(username, password):
    try:
        password_hash = hash_password(password)
        cursor.execute('INSERT INTO usuarios (username, password_hash) VALUES (?, ?)',
                       (username, password_hash))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    except sqlite3.Error as e:
        logging.error(f"Erro ao cadastrar usuário: {e}")
        return False

# Função para login
def login(username, password):
    try:
        cursor.execute('SELECT id, password_hash FROM usuarios WHERE username = ?', (username,))
        result = cursor.fetchone()
        if result and bcrypt.checkpw(password.encode(), result[1]):
            return result[0]
        return None
    except sqlite3.Error as e:
        logging.error(f"Erro no login: {e}")
        return None

# Função para obter ou definir chave API
def get_api_key(usuario_id):
    try:
        cursor.execute('SELECT api_key FROM config_api WHERE usuario_id = ?', (usuario_id,))
        result = cursor.fetchone()
        if result:
            return result[0]
        return None
    except sqlite3.Error as e:
        logging.error(f"Erro ao obter API key: {e}")
        return None

def set_api_key(usuario_id, api_key):
    try:
        cursor.execute('INSERT OR REPLACE INTO config_api (usuario_id, api_key) VALUES (?, ?)',
                       (usuario_id, api_key))
        conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Erro ao definir API key: {e}")

# Função para adicionar transação
def adicionar_transacao(usuario_id, tipo, valor, categoria, descricao):
    try:
        data = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
        INSERT INTO transacoes (usuario_id, tipo, valor, categoria, descricao, data)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (usuario_id, tipo, valor, categoria, descricao, data))
        conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Erro ao adicionar transação: {e}")

# Função para listar transações
def listar_transacoes(usuario_id):
    try:
        df = pd.read_sql_query(
            'SELECT id, tipo, valor, categoria, descricao, data FROM transacoes WHERE usuario_id = ? ORDER BY data DESC',
            conn, params=(usuario_id,), parse_dates={'data': '%Y-%m-%d %H:%M:%S'}
        )
        return df
    except pd.io.sql.DatabaseError as e:
        logging.error(f"Erro ao listar transações: {e}")
        return pd.DataFrame()

# Função para editar transação
def editar_transacao(transacao_id, valor, categoria, descricao):
    try:
        cursor.execute('''
        UPDATE transacoes SET valor = ?, categoria = ?, descricao = ? WHERE id = ?
        ''', (valor, categoria, descricao, transacao_id))
        conn.commit()
        return True
    except sqlite3.Error as e:
        logging.error(f"Erro ao editar transação: {e}")
        return False

# Função para deletar transação
def deletar_transacao(transacao_id):
    try:
        cursor.execute('DELETE FROM transacoes WHERE id = ?', (transacao_id,))
        conn.commit()
        return True
    except sqlite3.Error as e:
        logging.error(f"Erro ao deletar transação: {e}")
        return False

# Função para definir orçamento
def definir_orcamento(usuario_id, categoria, limite, mes_ano=None):
    if mes_ano is None:
        mes_ano = datetime.now().strftime('%Y-%m')
    try:
        cursor.execute('''
        INSERT OR REPLACE INTO orcamentos (usuario_id, categoria, limite, mes_ano)
        VALUES (?, ?, ?, ?)
        ''', (usuario_id, categoria, limite, mes_ano))
        conn.commit()
        return True
    except sqlite3.Error as e:
        logging.error(f"Erro ao definir orçamento: {e}")
        return False

# Função para obter gastos por categoria no mês atual
def obter_gastos_mes(usuario_id, mes_ano):
    try:
        df = pd.read_sql_query(
            'SELECT categoria, SUM(valor) as gasto FROM transacoes WHERE usuario_id = ? AND tipo = "despesa" AND substr(data, 1, 7) = ? GROUP BY categoria',
            conn, params=(usuario_id, mes_ano)
        )
        return df.set_index('categoria')['gasto'].to_dict()
    except pd.io.sql.DatabaseError as e:
        logging.error(f"Erro ao obter gastos: {e}")
        return {}

# Função para status de orçamento
def status_orcamento(usuario_id, mes_ano):
    try:
        orcamentos = pd.read_sql_query(
            'SELECT categoria, limite FROM orcamentos WHERE usuario_id = ? AND mes_ano = ?',
            conn, params=(usuario_id, mes_ano)
        ).set_index('categoria')['limite'].to_dict()
        
        gastos = obter_gastos_mes(usuario_id, mes_ano)
        
        status = {}
        for categoria, limite in orcamentos.items():
            gasto = gastos.get(categoria, 0)
            status[categoria] = {
                'gasto': gasto,
                'limite': limite,
                'percentual': (gasto / limite * 100) if limite > 0 else 0,
                'status': '⚠️ Ultrapassado' if gasto > limite else f'✅ Dentro do limite ({gasto:.2f}/{limite:.2f})'
            }
        return status
    except pd.io.sql.DatabaseError as e:
        logging.error(f"Erro no status de orçamento: {e}")
        return {}

# Função para adicionar investimento
def adicionar_investimento(usuario_id, simbolo, quantidade, custo_medio):
    try:
        cursor.execute('''
        INSERT OR REPLACE INTO investimentos (usuario_id, simbolo, quantidade, custo_medio)
        VALUES (?, ?, ?, ?)
        ''', (usuario_id, simbolo.upper(), quantidade, custo_medio))
        conn.commit()
        return True
    except sqlite3.Error as e:
        logging.error(f"Erro ao adicionar investimento: {e}")
        return False

# Função para obter cotação via Polygon API
def obter_cotacao_polygon(simbolo, api_key):
    if not api_key:
        return None
    url = f"https://api.polygon.io/v2/last/trade/{simbolo}?apikey={api_key}"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        if 'results' in data:
            return data['results']['p']  # Preço atual
    except requests.RequestException as e:
        logging.error(f"Erro na API Polygon: {e}")
    return None

# Função para calcular portfólio
def calcular_portfolio(usuario_id, api_key):
    try:
        df = pd.read_sql_query('SELECT simbolo, quantidade, custo_medio FROM investimentos WHERE usuario_id = ?', conn, params=(usuario_id,))
        if df.empty:
            return "Nenhum investimento registrado.", None, None
        
        portfolio = {}
        valor_total_custo = 0
        valor_total_atual = 0
        for _, row in df.iterrows():
            cotacao = obter_cotacao_polygon(row['simbolo'], api_key)
            valor_custo = row['quantidade'] * row['custo_medio']
            valor_atual = row['quantidade'] * (cotacao if cotacao is not None else row['custo_medio'])
            variacao = ((valor_atual / valor_custo) - 1) * 100 if valor_custo > 0 else 0
            portfolio[row['simbolo']] = {
                'quantidade': row['quantidade'],
                'custo': valor_custo,
                'atual': valor_atual,
                'variacao': variacao
            }
            valor_total_custo += valor_custo
            valor_total_atual += valor_atual
        
        resumo = f"=== PORTFÓLIO DE INVESTIMENTOS ===\n"
        resumo += f"Valor Total (Custo): R${valor_total_custo:.2f}\n"
        resumo += f"Valor Total (Atual): R${valor_total_atual:.2f}\n"
        resumo += f"Variação Geral: {((valor_total_atual / valor_total_custo) - 1) * 100:.2f}%\n\n"
        for simbolo, info in portfolio.items():
            status = "📈 Ganho" if info['variacao'] > 0 else ("📉 Perda" if info['variacao'] < 0 else "➖ Estável")
            resumo += f"- {simbolo}: {info['quantidade']} un. | Atual: R${info['atual']:.2f} | Variação: {info['variacao']:.2f}% ({status})\n"
        
        # Dados para gráfico de barras (distribuição por ativo)
        labels = list(portfolio.keys())
        valores = [info['atual'] for info in portfolio.values()]
        
        return resumo, labels, valores
    except pd.io.sql.DatabaseError as e:
        logging.error(f"Erro ao calcular portfolio: {e}")
        return "Erro ao calcular portfólio.", None, None

# Função para relatório de saldo (corrigida com inicialização de variáveis)
def relatorio_saldo(usuario_id):
    api_key = get_api_key(usuario_id)
    mes_ano_atual = datetime.now().strftime('%Y-%m')
    try:
        df_trans = pd.read_sql_query(
            'SELECT tipo, categoria, SUM(valor) as total FROM transacoes WHERE usuario_id = ? GROUP BY tipo, categoria ORDER BY tipo, total DESC',
            conn, params=(usuario_id,)
        )
    except pd.io.sql.DatabaseError as e:
        logging.error(f"Erro ao gerar relatório: {e}")
        df_trans = pd.DataFrame()
    
    # Inicialização de variáveis para gráficos
    categorias_despesas = None
    valores_despesas = None
    explode_despesas = None
    
    if df_trans.empty:
        transacoes_resumo = "Nenhuma transação registrada ainda."
    else:
        receitas_df = df_trans[df_trans['tipo'] == 'receita']
        despesas_df = df_trans[df_trans['tipo'] == 'despesa']
        
        receitas_total = receitas_df['total'].sum() if not receitas_df.empty else 0
        despesas_total = despesas_df['total'].sum() if not despesas_df.empty else 0
        saldo = receitas_total - despesas_total
        
        transacoes_resumo = f"=== RELATÓRIO DE SALDO ===\n\n"
        transacoes_resumo += f"Receitas Totais: R${receitas_total:.2f}\n"
        transacoes_resumo += f"Despesas Totais: R${despesas_total:.2f}\n"
        transacoes_resumo += f"Saldo Atual: R${saldo:.2f}\n\n"
        
        if not receitas_df.empty:
            transacoes_resumo += "=== DETALHAMENTO DE RECEITAS POR CATEGORIA ===\n"
            for _, row in receitas_df.iterrows():
                transacoes_resumo += f"- {row['categoria']}: R${row['total']:.2f}\n"
        else:
            transacoes_resumo += "Nenhuma receita registrada.\n"
        
        transacoes_resumo += "\n=== DETALHAMENTO DE DESPESAS POR CATEGORIA ===\n"
        if not despesas_df.empty:
            for _, row in despesas_df.iterrows():
                transacoes_resumo += f"- {row['categoria']}: R${row['total']:.2f}\n"
            # Configurar gráfico de pizza para despesas
            categorias_despesas = despesas_df['categoria'].tolist()
            valores_despesas = despesas_df['total'].tolist()
            explode_despesas = [0.1 if i == 0 else 0 for i in range(len(categorias_despesas))]
        else:
            transacoes_resumo += "Nenhuma despesa registrada.\n"
        
        # Orçamentos
        status = status_orcamento(usuario_id, mes_ano_atual)
        if status:
            transacoes_resumo += f"\n=== STATUS DE ORÇAMENTOS ({mes_ano_atual}) ===\n"
            for categoria, info in status.items():
                transacoes_resumo += f"- {categoria}: {info['status']} ({info['percentual']:.1f}%)\n"
        else:
            transacoes_resumo += f"\n=== STATUS DE ORÇAMENTOS ({mes_ano_atual}) ===\nNenhum orçamento definido.\n"
    
    # Portfólio (sempre calculado)
    portfolio_resumo, labels_portfolio, valores_portfolio = calcular_portfolio(usuario_id, api_key)
    
    relatorio_completo = transacoes_resumo + "\n" + portfolio_resumo if portfolio_resumo.startswith("=== PORTFÓLIO") else transacoes_resumo
    
    return relatorio_completo, categorias_despesas, valores_despesas, explode_despesas, labels_portfolio, valores_portfolio

# Janela de Login/Cadastro (atualizada para chave API)
class LoginWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Login - App de Finanças Pessoais")
        self.root.geometry("300x250")
        self.root.resizable(True, True)
        
        style = ttk.Style()
        style.theme_use('clam')
        
        tk.Label(root, text="Nome de Usuário:", font=("Arial", 10)).pack(pady=5)
        self.username_entry = tk.Entry(root, font=("Arial", 10))
        self.username_entry.pack(pady=5)
        
        tk.Label(root, text="Senha:", font=("Arial", 10)).pack(pady=5)
        self.password_entry = tk.Entry(root, show="*", font=("Arial", 10))
        self.password_entry.pack(pady=5)
        
        tk.Button(root, text="Login", command=self.do_login, font=("Arial", 10)).pack(pady=10)
        tk.Button(root, text="Cadastrar", command=self.do_cadastro, font=("Arial", 10)).pack()
    
    def do_login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        if username and password:
            usuario_id = login(username, password)
            if usuario_id:
                self.verificar_api_key(usuario_id)
                self.root.destroy()
                MainWindow(usuario_id)
            else:
                messagebox.showerror("Erro", "Credenciais inválidas.")
        else:
            messagebox.showwarning("Aviso", "Preencha todos os campos.")
    
    def do_cadastro(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        if username and password:
            if cadastrar_usuario(username, password):
                messagebox.showinfo("Sucesso", "Usuário cadastrado. Faça login.")
            else:
                messagebox.showerror("Erro", "Usuário já existe.")
        else:
            messagebox.showwarning("Aviso", "Preencha todos os campos.")
    
    def verificar_api_key(self, usuario_id):
        api_key = get_api_key(usuario_id)
        if not api_key:
            api_key_input = simpledialog.askstring("Configuração API", "Insira sua chave API da Polygon (obtenha em polygon.io):")
            if api_key_input:
                set_api_key(usuario_id, api_key_input)
            else:
                messagebox.showwarning("Aviso", "Chave API não configurada. Funcionalidades de investimentos limitadas.")

# Janela para Gerenciar Orçamentos
class OrcamentoWindow:
    def __init__(self, root, usuario_id):
        self.root = root
        self.usuario_id = usuario_id
        self.root.title("Gerenciar Orçamentos")
        self.root.geometry("400x300")
        self.root.resizable(True, True)
        
        tk.Label(self.root, text="Definir Orçamento Mensal", font=("Arial", 14, "bold")).pack(pady=10)
        
        tk.Label(self.root, text="Categoria:", font=("Arial", 10)).pack(pady=5)
        self.categoria_entry = tk.Entry(self.root, font=("Arial", 10))
        self.categoria_entry.pack(pady=5)
        
        tk.Label(self.root, text="Limite (R$):", font=("Arial", 10)).pack(pady=5)
        self.limite_entry = tk.Entry(self.root, font=("Arial", 10))
        self.limite_entry.pack(pady=5)
        
        def submit_orcamento():
            try:
                categoria = self.categoria_entry.get().strip()
                limite = float(self.limite_entry.get())
                if categoria and limite > 0:
                    if definir_orcamento(self.usuario_id, categoria, limite):
                        messagebox.showinfo("Sucesso", f"Orçamento para '{categoria}' definido: R${limite:.2f}")
                        self.root.destroy()
                    else:
                        messagebox.showerror("Erro", "Falha ao definir orçamento.")
                else:
                    messagebox.showwarning("Aviso", "Preencha categoria e limite válido (>0).")
            except ValueError:
                messagebox.showerror("Erro", "Limite deve ser um número válido.")
        
        tk.Button(self.root, text="Definir Orçamento", command=submit_orcamento, 
                  font=("Arial", 10), bg="lightyellow", width=20).pack(pady=20)
        
        tk.Button(self.root, text="Fechar", command=self.root.destroy, 
                  font=("Arial", 10), bg="gray", width=20).pack(pady=5)

# Janela para Gerenciar Investimentos
class InvestimentoWindow:
    def __init__(self, root, usuario_id):
        self.root = root
        self.usuario_id = usuario_id
        self.root.title("Gerenciar Investimentos")
        self.root.geometry("400x300")
        self.root.resizable(True, True)
        
        tk.Label(self.root, text="Adicionar/Editar Investimento", font=("Arial", 14, "bold")).pack(pady=10)
        
        tk.Label(self.root, text="Símbolo (ex: AAPL):", font=("Arial", 10)).pack(pady=5)
        self.simbolo_entry = tk.Entry(self.root, font=("Arial", 10))
        self.simbolo_entry.pack(pady=5)
        
        tk.Label(self.root, text="Quantidade:", font=("Arial", 10)).pack(pady=5)
        self.quantidade_entry = tk.Entry(self.root, font=("Arial", 10))
        self.quantidade_entry.pack(pady=5)
        
        tk.Label(self.root, text="Custo Médio por Unidade (R$):", font=("Arial", 10)).pack(pady=5)
        self.custo_entry = tk.Entry(self.root, font=("Arial", 10))
        self.custo_entry.pack(pady=5)
        
        def submit_investimento():
            try:
                simbolo = self.simbolo_entry.get().strip()
                quantidade = float(self.quantidade_entry.get())
                custo_medio = float(self.custo_entry.get())
                if simbolo and quantidade > 0 and custo_medio > 0:
                    if adicionar_investimento(self.usuario_id, simbolo, quantidade, custo_medio):
                        messagebox.showinfo("Sucesso", f"Investimento '{simbolo}' adicionado/editado.")
                        self.root.destroy()
                    else:
                        messagebox.showerror("Erro", "Falha ao adicionar investimento.")
                else:
                    messagebox.showwarning("Aviso", "Preencha todos os campos com valores válidos.")
            except ValueError:
                messagebox.showerror("Erro", "Quantidade e custo devem ser números válidos.")
        
        tk.Button(self.root, text="Adicionar Investimento", command=submit_investimento, 
                  font=("Arial", 10), bg="lightcyan", width=20).pack(pady=20)
        
        tk.Button(self.root, text="Fechar", command=self.root.destroy, 
                  font=("Arial", 10), bg="gray", width=20).pack(pady=5)

# Nova Janela para Gerenciar Transações
class TransacaoWindow:
    def __init__(self, root, usuario_id):
        self.root = root
        self.usuario_id = usuario_id
        self.root.title("Gerenciar Transações")
        self.root.geometry("800x500")
        self.root.resizable(True, True)
        
        # Frame para botões
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)
        
        def refresh_list():
            for item in self.tree.get_children():
                self.tree.delete(item)
            df = listar_transacoes(self.usuario_id)
            for _, row in df.iterrows():
                self.tree.insert('', 'end', values=(row['id'], row['tipo'], f"R${row['valor']:.2f}", row['categoria'], row['descricao'][:30] + '...' if len(row['descricao']) > 30 else row['descricao'], row['data']))
        
        def edit_selected():
            selected = self.tree.selection()
            if selected:
                item = self.tree.item(selected[0])
                transacao_id = item['values'][0]
                df = listar_transacoes(self.usuario_id)
                row = df[df['id'] == transacao_id].iloc[0]
                self.edit_popup(row)
                refresh_list()
            else:
                messagebox.showwarning("Aviso", "Selecione uma transação para editar.")
        
        def delete_selected():
            selected = self.tree.selection()
            if selected:
                item = self.tree.item(selected[0])
                transacao_id = item['values'][0]
                if messagebox.askyesno("Confirmação", f"Deseja deletar a transação ID {transacao_id}?"):
                    if deletar_transacao(transacao_id):
                        messagebox.showinfo("Sucesso", "Transação deletada com sucesso.")
                        refresh_list()
                    else:
                        messagebox.showerror("Erro", "Falha ao deletar transação.")
            else:
                messagebox.showwarning("Aviso", "Selecione uma transação para deletar.")
        
        tk.Button(button_frame, text="Editar Selecionada", command=edit_selected, font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Deletar Selecionada", command=delete_selected, font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Atualizar Lista", command=refresh_list, font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Fechar", command=self.root.destroy, font=("Arial", 10)).pack(side=tk.RIGHT, padx=5)
        
        # Treeview para listar transações
        columns = ('ID', 'Tipo', 'Valor', 'Categoria', 'Descrição', 'Data')
        self.tree = ttk.Treeview(self.root, columns=columns, show='headings', height=20)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120)
        self.tree.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        
        # Scrollbar para Treeview
        scrollbar = ttk.Scrollbar(self.root, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        refresh_list()
    
    def edit_popup(self, row):
        popup = tk.Toplevel(self.root)
        popup.title(f"Editar Transação ID {row['id']}")
        popup.geometry("300x300")
        popup.grab_set()
        
        tk.Label(popup, text="Valor (R$):", font=("Arial", 10)).pack(pady=5)
        valor_entry = tk.Entry(popup, font=("Arial", 10))
        valor_entry.insert(0, row['valor'])
        valor_entry.pack(pady=5)
        
        tk.Label(popup, text="Categoria:", font=("Arial", 10)).pack(pady=5)
        categoria_entry = tk.Entry(popup, font=("Arial", 10))
        categoria_entry.insert(0, row['categoria'])
        categoria_entry.pack(pady=5)
        
        tk.Label(popup, text="Descrição:", font=("Arial", 10)).pack(pady=5)
        descricao_entry = tk.Entry(popup, font=("Arial", 10))
        descricao_entry.insert(0, row['descricao'])
        descricao_entry.pack(pady=5)
        
        def submit_edit():
            try:
                novo_valor = float(valor_entry.get())
                nova_categoria = categoria_entry.get()
                nova_descricao = descricao_entry.get()
                if novo_valor > 0 and nova_categoria and nova_descricao:
                    if editar_transacao(row['id'], novo_valor, nova_categoria, nova_descricao):
                        messagebox.showinfo("Sucesso", "Transação editada com sucesso.")
                        popup.destroy()
                    else:
                        messagebox.showerror("Erro", "Falha ao editar transação.")
                else:
                    messagebox.showwarning("Aviso", "Preencha todos os campos corretamente (valor > 0).")
            except ValueError:
                messagebox.showerror("Erro", "O valor deve ser um número válido.")
        
        tk.Button(popup, text="Salvar Alterações", command=submit_edit, font=("Arial", 10)).pack(pady=10)

# Janela Principal (atualizada com botão para transações)
class MainWindow:
    def __init__(self, usuario_id):
        self.usuario_id = usuario_id
        self.root = tk.Tk()
        self.root.title("App de Finanças Pessoais")
        self.root.geometry("400x450")
        self.root.resizable(True, True)
        
        style = ttk.Style()
        style.theme_use('clam')
        
        # Título
        tk.Label(self.root, text="Menu Principal", font=("Arial", 14, "bold")).pack(pady=20)
        
        tk.Button(self.root, text="Adicionar Receita", command=self.add_receita, 
                  font=("Arial", 12), bg="lightgreen", width=20).pack(pady=5)
        tk.Button(self.root, text="Adicionar Despesa", command=self.add_despesa, 
                  font=("Arial", 12), bg="lightcoral", width=20).pack(pady=5)
        tk.Button(self.root, text="Gerenciar Transações", command=self.gerenciar_transacoes, 
                  font=("Arial", 12), bg="lightgray", width=20).pack(pady=5)
        tk.Button(self.root, text="Gerenciar Orçamentos", command=self.gerenciar_orcamentos, 
                  font=("Arial", 12), bg="lightyellow", width=20).pack(pady=5)
        tk.Button(self.root, text="Gerenciar Investimentos", command=self.gerenciar_investimentos, 
                  font=("Arial", 12), bg="lightcyan", width=20).pack(pady=5)
        tk.Button(self.root, text="Ver Relatório de Saldo", command=self.ver_relatorio, 
                  font=("Arial", 12), bg="lightblue", width=20).pack(pady=5)
        tk.Button(self.root, text="Sair", command=self.root.quit, 
                  font=("Arial", 12), bg="gray", width=20).pack(pady=5)
        
        self.root.mainloop()
    
    def add_receita(self):
        self.add_transacao('receita')
    
    def add_despesa(self):
        self.add_transacao('despesa')
    
    def gerenciar_transacoes(self):
        transacao_window = tk.Toplevel(self.root)
        TransacaoWindow(transacao_window, self.usuario_id)
    
    def gerenciar_orcamentos(self):
        orcamento_window = tk.Toplevel(self.root)
        OrcamentoWindow(orcamento_window, self.usuario_id)
    
    def gerenciar_investimentos(self):
        investimento_window = tk.Toplevel(self.root)
        InvestimentoWindow(investimento_window, self.usuario_id)
    
    def add_transacao(self, tipo):
        popup = tk.Toplevel(self.root)
        popup.title(f"Adicionar {tipo.capitalize()}")
        popup.geometry("300x250")
        popup.grab_set()
        
        tk.Label(popup, text="Valor (R$):", font=("Arial", 10)).pack(pady=5)
        valor_entry = tk.Entry(popup, font=("Arial", 10))
        valor_entry.pack(pady=5)
        
        tk.Label(popup, text="Categoria (ex: Salário):", font=("Arial", 10)).pack(pady=5)
        categoria_entry = tk.Entry(popup, font=("Arial", 10))
        categoria_entry.pack(pady=5)
        
        tk.Label(popup, text="Descrição:", font=("Arial", 10)).pack(pady=5)
        descricao_entry = tk.Entry(popup, font=("Arial", 10))
        descricao_entry.pack(pady=5)
        
        def submit():
            try:
                valor = float(valor_entry.get())
                categoria = categoria_entry.get()
                descricao = descricao_entry.get()
                if valor > 0 and categoria and descricao:
                    adicionar_transacao(self.usuario_id, tipo, valor, categoria, descricao)
                    messagebox.showinfo("Sucesso", f"{tipo.capitalize()} adicionada com sucesso!")
                    popup.destroy()
                else:
                    messagebox.showwarning("Aviso", "Preencha todos os campos corretamente (valor > 0).")
            except ValueError:
                messagebox.showerror("Erro", "O valor deve ser um número válido.")
        
        tk.Button(popup, text="Adicionar", command=submit, font=("Arial", 10)).pack(pady=10)
    
    def ver_relatorio(self):
        relatorio, categorias_despesas, valores_despesas, explode_despesas, labels_portfolio, valores_portfolio = relatorio_saldo(self.usuario_id)
        
        # Janela de relatório expandida
        relatorio_window = tk.Toplevel(self.root)
        relatorio_window.title("Relatório Detalhado de Saldo")
        relatorio_window.geometry("800x700")
        relatorio_window.resizable(True, True)
        
        # Notebook para abas (despesas e portfólio)
        notebook = ttk.Notebook(relatorio_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Aba Gráfico Despesas
        frame_despesas = tk.Frame(notebook)
        notebook.add(frame_despesas, text="Distribuição de Despesas")
        if categorias_despesas and valores_despesas:
            fig_despesas = Figure(figsize=(6, 4), dpi=100)
            ax_despesas = fig_despesas.add_subplot(111)
            ax_despesas.pie(valores_despesas, labels=categorias_despesas, autopct='%1.1f%%', explode=explode_despesas, startangle=90)
            ax_despesas.set_title('Distribuição de Despesas por Categoria')
            canvas_despesas = FigureCanvasTkAgg(fig_despesas, master=frame_despesas)
            canvas_despesas.draw()
            canvas_despesas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        else:
            tk.Label(frame_despesas, text="Nenhuma despesa para visualizar.", font=("Arial", 12)).pack(pady=20)
        
        # Aba Gráfico Portfólio
        frame_portfolio = tk.Frame(notebook)
        notebook.add(frame_portfolio, text="Portfólio de Investimentos")
        if labels_portfolio and valores_portfolio:
            fig_portfolio = Figure(figsize=(6, 4), dpi=100)
            ax_portfolio = fig_portfolio.add_subplot(111)
            ax_portfolio.bar(labels_portfolio, valores_portfolio)
            ax_portfolio.set_title('Valor Atual por Ativo')
            ax_portfolio.set_ylabel('Valor (R$)')
            canvas_portfolio = FigureCanvasTkAgg(fig_portfolio, master=frame_portfolio)
            canvas_portfolio.draw()
            canvas_portfolio.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        else:
            tk.Label(frame_portfolio, text="Nenhum investimento para visualizar.", font=("Arial", 12)).pack(pady=20)
        
        # Área de texto para relatório completo
        text_frame = tk.Frame(relatorio_window)
        text_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        text_area = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, width=80, height=15, font=("Arial", 10))
        text_area.pack(fill=tk.BOTH, expand=True)
        text_area.insert(tk.END, relatorio)
        text_area.config(state=tk.DISABLED)
        
        tk.Button(relatorio_window, text="Fechar", command=relatorio_window.destroy, 
                  font=("Arial", 10)).pack(pady=5)

# Executar o app
if __name__ == "__main__":
    root = tk.Tk()
    app = LoginWindow(root)
    root.mainloop()
    conn.close()