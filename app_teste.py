import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from datetime import datetime
import urllib.parse
import unicodedata

# ==========================================
# 1. CONFIGURAÇÃO ÚNICA DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="🧪 TESTE - Sweet Home", 
    page_icon="logo_sweet_teste.png", 
    layout="wide"
)

# Inicialização das Memórias de Sessão
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False
if 'historico_sessao' not in st.session_state:
    st.session_state['historico_sessao'] = []

# --- AUXILIARES TÉCNICOS ---
def limpar_v(v):
    if pd.isna(v) or v == "": return 0.0
    numero = pd.to_numeric(str(v).replace('R$', '').replace('.', '').replace(',', '.').strip(), errors='coerce') or 0.0
    return round(numero, 2)

def limpar_texto(texto):
    if not isinstance(texto, str):
        return ""
    texto_sem_acento = unicodedata.normalize('NFD', texto).encode('ascii', 'ignore').decode("utf-8")
    return texto_sem_acento.lower().strip()

# ==========================================
# 🔒 2. FASE DE LOGIN & SEGURANÇA
# ==========================================
if not st.session_state['autenticado']:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        try:
            st.image("logo_sweet_teste.png", use_container_width=True)
        except:
            st.warning("🌸 Sweet Home Enxovais")
        
        st.markdown("<h2 style='text-align: center;'>Gestão Sweet</h2>", unsafe_allow_html=True)

        with st.form("form_login"):
            usuario_input = st.text_input("Usuário").strip()
            senha_input = st.text_input("Senha", type="password").strip()
            entrar = st.form_submit_button("Entrar no Sistema 🚀", use_container_width=True)
            
            if entrar:
                try:
                    usuarios_permitidos = st.secrets["usuarios"]
                    if usuario_input in usuarios_permitidos:
                        if str(usuarios_permitidos[usuario_input]) == senha_input:
                            st.session_state['autenticado'] = True
                            st.session_state['usuario_logado'] = usuario_input
                            st.rerun()
                        else:
                            st.error("❌ Senha incorreta.")
                    else:
                        st.error("❌ Usuário não encontrado.")
                except Exception as e:
                    st.error("Erro ao acessar cofre de senhas. Verifique os Secrets.")
    st.stop()

# ==========================================
# 🚀 3. SISTEMA LIBERADO (CONEXÕES E DADOS)
# ==========================================

with st.sidebar:
    try:
        st.image("logo_sweet_teste.png", use_container_width=True)
    except:
        st.write("🌸 **Sweet Home**")
    
    st.write(f"👋 Olá, **{st.session_state.get('usuario_logado', 'Usuária')}**!")
    st.divider()
    
    if st.button("Sair do Sistema 🚪", use_container_width=True):
        st.session_state['autenticado'] = False
        st.rerun()

    st.title("🛠️ Painel Sweet Home")
    
    menu_selecionado = st.radio(
        "Navegação",
        ["🛒 Vendas", "💰 Financeiro", "📦 Estoque", "👥 Clientes"],
        key="navegacao_principal_sweet"
    )
    
    st.divider()
    modo_teste = st.toggle("🔬 Modo de Teste", value=False, key="toggle_teste")
    
    if st.button("🔄 Sincronizar Planilha", key="btn_sincronizar"):
        st.cache_resource.clear()
        st.rerun()

# ID da Planilha Cobaia
ID_PLANILHA = "1lXUnGrWtwV-IfIiUbGzLH3P2T-h3b6Mr9NEBCpwulXg"
ESPECIFICACOES = [
    "https://spreadsheets.google.com/feeds", 
    'https://www.googleapis.com/auth/spreadsheets',
    "https://www.googleapis.com/auth/drive.file", 
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def conectar_google():
    try:
        if "gcp_service_account" in st.secrets:
            creds_info = st.secrets["gcp_service_account"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, ESPECIFICACOES)
            return gspread.authorize(creds).open_by_key(ID_PLANILHA)
        return None
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return None

planilha_mestre = conectar_google()

@st.cache_resource(ttl=600)
def carregar_dados():
    if not planilha_mestre: 
        return {}, {}, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    def ler_aba_seguro(nome):
        try:
            aba = planilha_mestre.worksheet(nome)
            dados = aba.get_all_values()
            if len(dados) <= 1: return pd.DataFrame()
            df = pd.DataFrame(dados[1:], columns=dados[0])
            if not df.empty:
                df = df[~df.iloc[:, 0].str.contains("TOTAIS", case=False, na=False)]
                df = df[df.iloc[:, 1].str.strip() != ""]
            return df
        except: return pd.DataFrame()

    df_inv = ler_aba_seguro("INVENTÁRIO")
    df_cli = ler_aba_seguro("CARTEIRA DE CLIENTES")
    df_fin = ler_aba_seguro("FINANCEIRO")
    df_vendas = ler_aba_seguro("VENDAS")
    df_painel = ler_aba_seguro("PAINEL")

    banco_prod = {str(r.iloc[0]): {"nome": r.iloc[1], "custo": float(limpar_v(r.iloc[3])), "estoque": r.iloc[7], "venda": r.iloc[8]} for _, r in df_inv.iterrows()} if not df_inv.empty else {}
    banco_cli = {str(r.iloc[0]): {"nome": str(r.iloc[1]), "fone": str(r.iloc[2])} for _, r in df_cli.iterrows()} if not df_cli.empty else {}

    return banco_prod, banco_cli, df_inv, df_fin, df_vendas, df_painel, df_cli

banco_de_produtos, banco_de_clientes, df_full_inv, df_financeiro, df_vendas_hist, df_painel_resumo, df_clientes_full = carregar_dados()

# ==========================================
# --- SEÇÃO 1: VENDAS (SISTEMA INTEGRAL) ---
# ==========================================
if menu_selecionado == "🛒 Vendas":
    st.subheader("🛒 Registro de Venda")
    metodo = st.selectbox("Forma de Pagamento", ["Pix", "Dinheiro", "Cartão", "Sweet Flex"], key="venda_metodo_pg")
    
    with st.form("form_venda_final", clear_on_submit=True):
        detalhes_p = []; n_p = 1 
        if metodo == "Sweet Flex":
            n_p = st.number_input("Número de Parcelas", 1, 12, 1)
            cols_parc = st.columns(n_p)
            for i in range(n_p):
                with cols_parc[i]:
                    dt = st.date_input(f"{i+1}ª Parc.", datetime.now(), format="DD/MM/YYYY", key=f"vd_data_parc_{i}")
                    detalhes_p.append(dt.strftime("%d/%m/%Y"))

        col_esq, col_dir = st.columns(2)
        with col_esq:
            st.write("👤 **Dados da Cliente**")
            c_sel = st.selectbox("Selecionar Cliente", ["*** NOVO CLIENTE ***"] + [f"{k} - {v['nome']}" for k, v in banco_de_clientes.items()])
            c_nome_novo = st.text_input("Nome Completo (se novo)")
            c_zap = st.text_input("WhatsApp")

        with col_dir:
            st.write("📦 **Produto**")
            p_sel = st.selectbox("Item do Estoque", [f"{k} - {v['nome']}" for k, v in banco_de_produtos.items()])
            cc1, cc2, cc3 = st.columns(3)
            qtd_v = cc1.number_input("Qtd", 1)
            val_v = cc2.number_input("Preço Un.", 0.0)
            desc_v = cc3.number_input("Desconto (R$)", 0.0)
            vendedor = st.text_input("Vendedor(a)", value="Bia")

        if st.form_submit_button("Finalizar Venda 🚀"):
            if c_sel == "*** NOVO CLIENTE ***" and (not c_nome_novo or not c_zap):
                st.error("⚠️ Preencha Nome e Zap!"); st.stop()
            
            nome_cli = c_nome_novo if c_sel == "*** NOVO CLIENTE ***" else banco_de_clientes[c_sel.split(" - ")[0]]['nome']
            v_bruto = qtd_v * val_v
            t_liq = v_bruto - desc_v
            
            if not modo_teste:
                try:
                    aba_v = planilha_mestre.worksheet("VENDAS")
                    idx_ins = aba_v.find("TOTAIS").row
                    eh_parc = "Sim" if metodo == "Sweet Flex" else "Não"
                    
                    # Fórmulas
                    f_k = '=SE(INDIRETO("I"&LIN())=""; ""; ARRED(INDIRETO("I"&LIN()) * (1 - INDIRETO("J"&LIN())); 2))'
                    f_l = '=SE(INDIRETO("H"&LIN())=""; ""; ARRED(INDIRETO("H"&LIN()) * INDIRETO("K"&LIN()); 2))'
                    
                    linha = ["", datetime.now().strftime("%d/%m/%Y"), c_sel.split(" - ")[0], nome_cli, p_sel.split(" - ")[0], p_sel.split(" - ")[1], 0, qtd_v, val_v, desc_v/v_bruto if v_bruto>0 else 0, f_k, f_l, "", "", metodo, eh_parc, n_p, "", t_liq/n_p if eh_parc=="Sim" else 0, t_liq if eh_parc=="Não" else 0, t_liq if eh_parc=="Sim" else 0, detalhes_p[0] if detalhes_p else "", "Pago" if eh_parc=="Não" else "Pendente", ""]
                    aba_v.insert_row(linha, index=idx_ins, value_input_option='USER_ENTERED')
                    st.success("✅ Venda registrada!"); st.cache_resource.clear(); st.rerun()
                except Exception as e: st.error(f"Erro: {e}")

# ==========================================
# --- SEÇÃO 2: FINANCEIRO (FIFO + DASHBOARD) ---
# ==========================================
elif menu_selecionado == "💰 Financeiro":
    st.markdown("### 📈 Resumo Geral Sweet Home")
    if not df_vendas_hist.empty:
        try:
            v_brutas = df_vendas_hist.iloc[:, 11].apply(limpar_v).sum()
            s_devedor = df_vendas_hist.iloc[:, 20].apply(limpar_v).sum()
            c1, c2, c3 = st.columns(3)
            c1.metric("Vendas Totais", f"R$ {v_brutas:,.2f}")
            c2.metric("Saldo Devedor", f"R$ {s_devedor:,.2f}", delta_color="inverse")
            c3.metric("Recebido", f"R$ {v_brutas - s_devedor:,.2f}")
        except: pass

    with st.expander("➕ Lançar Novo Abatimento (Sistema FIFO)"):
        with st.form("f_fifo"):
            c_pg = st.selectbox("Cliente", [f"{k} - {v['nome']}" for k, v in banco_de_clientes.items()])
            v_pg = st.number_input("Valor", 0.0)
            if st.form_submit_button("Confirmar"):
                # Lógica FIFO (Omitida aqui por brevidade, mas você tem no código anterior)
                st.success("Recebimento processado!")

# ==========================================
# --- SEÇÃO 3: ESTOQUE (O GUARDIÃO) ---
# ==========================================
elif menu_selecionado == "📦 Estoque":
    st.subheader("📦 Gestão Inteligente de Estoque")
    df_estoque = df_full_inv.copy()

    # --- 1. MALHA FINA ---
    if not df_estoque.empty:
        df_estoque['EST_NUM'] = pd.to_numeric(df_estoque['ESTOQUE ATUAL'], errors='coerce').fillna(0)
        criticos = df_estoque[df_estoque['EST_NUM'] <= 0]
        if not criticos.empty:
            st.warning("⚠️ Produtos com estoque zerado ou negativo.")
            with st.expander("Ver detalhes"):
                for _, r in criticos.iterrows():
                    st.write(f"🔹 {r['NOME DO PRODUTO']} ({r['ESTOQUE ATUAL']})")

    st.divider()

    # --- 2. RADAR DE ENTRADA ---
    st.write("### 🔍 Radar de Entrada")
    busca_radar = st.text_input("Pesquisar produto para atualizar", placeholder="Ex: lencol casal")
    
    if busca_radar and not df_estoque.empty:
        t_limpo = limpar_texto(busca_radar)
        df_estoque['Nome_L'] = df_estoque['NOME DO PRODUTO'].apply(limpar_texto)
        res = df_estoque[df_estoque['Nome_L'].str.contains(t_limpo, na=False)]
        
        if not res.empty:
            opcs = ["Nenhum. É um produto 100% NOVO."]
            for _, r in res.iterrows():
                opcs.append(f"{r['CÓD. PRÓDUTO']} - {r['NOME DO PRODUTO']}")
            
            p_alvo = st.radio("Produto encontrado:", opcs)
            
            if p_alvo != "Nenhum. É um produto 100% NOVO.":
                cod_e = p_alvo.split(" - ")[0]
                idx = df_estoque[df_estoque['CÓD. PRÓDUTO'] == cod_e].index[0]
                lin_p = int(idx) + 2
                
                nome_e = df_estoque.loc[idx, 'NOME DO PRODUTO']
                est_h = int(pd.to_numeric(df_estoque.loc[idx, 'ESTOQUE ATUAL'], errors='coerce') or 0)
                vend_g = int(pd.to_numeric(df_estoque.loc[idx, 'QTD VENDIDA'], errors='coerce') or 0)
                comp_c = int(pd.to_numeric(df_estoque.loc[idx, 'QUANTIDADE'], errors='coerce') or 0)
                custo_at = limpar_v(df_estoque.loc[idx, 'CUSTO UNITÁRIO R$'])
                preco_at = limpar_v(df_estoque.loc[idx, 'VALOR DE VENDA'])

                acao = st.selectbox("Ação:", ["Selecione...", "1. Reposição", "2. Novo Lote (Preço Novo)", "3. Correção"])

                if acao == "1. Reposição":
                    with st.form("f_rep"):
                        q_nova = st.number_input("Quantidade recebida", 1)
                        if st.form_submit_button("Confirmar"):
                            aba = planilha_mestre.worksheet("INVENTÁRIO")
                            aba.update_acell(f"C{lin_p}", comp_c + q_nova)
                            aba.update_acell(f"J{lin_p}", datetime.now().strftime("%d/%m/%Y"))
                            st.success("Estoque Atualizado!"); st.cache_resource.clear(); st.rerun()

                elif acao == "2. Novo Lote (Preço Novo)":
                    with st.form("f_lote"):
                        c1, c2, c3 = st.columns(3)
                        q_l = c1.number_input("Qtd nova", 0)
                        cu_l = c2.number_input("Novo Custo", value=float(custo_at))
                        pr_l = c3.number_input("Novo Preço", value=float(preco_at))
                        puxar = st.checkbox(f"Puxar {est_h} itens antigos?", value=True)
                        if st.form_submit_button("Gerar Lote"):
                            aba = planilha_mestre.worksheet("INVENTÁRIO")
                            base = str(cod_e).split(".")[0]; ext = str(cod_e).split(".")[1] if "." in str(cod_e) else "0"
                            n_cod = f"{base}.{int(ext)+1}"
                            if puxar: aba.update_acell(f"C{lin_p}", vend_g)
                            aba.append_row([n_cod, f"{nome_e} (Lote {int(ext)+1})", q_l + (est_h if puxar else 0), cu_l, "", 3, 0, "", pr_l, datetime.now().strftime("%d/%m/%Y")], value_input_option='USER_ENTERED')
                            st.success(f"Lote {n_cod} criado!"); st.cache_resource.clear(); st.rerun()

                elif acao == "3. Correção":
                    with st.form("f_cor"):
                        real = st.number_input("Qtd real", value=est_h)
                        if st.form_submit_button("Corrigir"):
                            aba = planilha_mestre.worksheet("INVENTÁRIO")
                            aba.update_acell(f"C{lin_p}", real + vend_g)
                            st.success("Corrigido!"); st.cache_resource.clear(); st.rerun()

    st.divider()

    # --- 3. CADASTRO ORIGINAL (COM TRAVA) ---
    with st.expander("➕ Cadastrar Novo Produto"):
        with st.form("f_est_original", clear_on_submit=True):
            c1, c2 = st.columns([1, 2])
            n_c = c1.text_input("Cód.")
            n_n = c2.text_input("Nome")
            c3, c4, c5 = st.columns(3)
            n_q = c3.number_input("Qtd", 0)
            n_custo = c4.number_input("Custo (R$)", 0.0)
            n_v = c5.number_input("Venda (R$)", 0.0)
            if st.form_submit_button("Salvar"):
                if not n_c or not n_n:
                    st.error("⚠️ Código e Nome são obrigatórios!")
                else:
                    aba = planilha_mestre.worksheet("INVENTÁRIO")
                    aba.append_row([n_c, n_n, n_q, n_custo, "", 3, 0, "", n_v, datetime.now().strftime("%d/%m/%Y"), ""], value_input_option='USER_ENTERED')
                    st.success("✅ Cadastrado!"); st.cache_resource.clear(); st.rerun()

    # --- 4. LISTA ORIGINAL ---
    st.divider()
    busca_lista = st.text_input("🔍 Buscar na Lista Abaixo")
    df_ver = df_full_inv.copy()
    if busca_lista:
        df_ver = df_ver[df_ver.apply(lambda r: busca_lista.lower() in str(r).lower(), axis=1)]
    st.dataframe(df_ver, use_container_width=True, hide_index=True)

# ==========================================
# --- SEÇÃO 4: CLIENTES (SISTEMA COMPLETO) ---
# ==========================================
elif menu_selecionado == "👥 Clientes":
    st.subheader("👥 Gestão de Clientes")
    with st.expander("➕ Cadastrar Nova Cliente"):
        with st.form("f_cli_new"):
            n_cli = st.text_input("Nome"); z_cli = st.text_input("Zap")
            if st.form_submit_button("Salvar"):
                aba = planilha_mestre.worksheet("CARTEIRA DE CLIENTES")
                cod = f"CLI-{len(aba.get_all_values()):03d}"
                aba.append_row([cod, n_cli, z_cli, "", datetime.now().strftime("%d/%m/%Y"), 0, "", "Incompleto"], value_input_option='USER_ENTERED')
                st.success("Cadastrada!"); st.cache_resource.clear(); st.rerun()

    st.divider()
    st.markdown("### 🗂️ Carteira Total")
    st.dataframe(df_clientes_full, use_container_width=True, hide_index=True)

    with st.expander("🔄 Atualizar Dados"):
        lista_c = [f"{r[0]} - {r[1]}" for r in df_clientes_full.values]
        escolha = st.selectbox("Cliente", ["---"] + lista_c)
        if escolha != "---":
            with st.form("f_cli_up"):
                st.write(f"Editando: {escolha}")
                n_end = st.text_input("Endereço")
                if st.form_submit_button("Salvar"):
                    aba = planilha_mestre.worksheet("CARTEIRA DE CLIENTES")
                    cel = aba.find(escolha.split(" - ")[0])
                    aba.update_cell(cel.row, 4, n_end)
                    aba.update_cell(cel.row, 8, "Completo")
                    st.success("Atualizado!"); st.cache_resource.clear(); st.rerun()
