import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from datetime import datetime
import urllib.parse
import unicodedata
import cloudinary
import cloudinary.uploader

# ==========================================
# 1. CONFIGURAÇÃO ÚNICA DA PÁGINA E CLOUDINARY
# ==========================================
st.set_page_config(
    page_title="🧪 TESTE - Sweet Home", 
    page_icon="logo_sweet_teste.png", 
    layout="wide"
)

# Inicialização das Memórias de Sessão
if 'autenticado' not in st.session_state: st.session_state['autenticado'] = False
if 'historico_sessao' not in st.session_state: st.session_state['historico_sessao'] = []
if 'historico_estoque' not in st.session_state: st.session_state['historico_estoque'] = []   

def limpar_v(v):
    if pd.isna(v) or v == "": return 0.0
    numero = pd.to_numeric(str(v).replace('R$', '').replace('.', '').replace(',', '.').strip(), errors='coerce') or 0.0
    return round(numero, 2)

def limpar_texto(texto):
    if not isinstance(texto, str): return ""
    texto_sem_acento = unicodedata.normalize('NFD', texto).encode('ascii', 'ignore').decode("utf-8")
    return texto_sem_acento.lower().strip()

# ==========================================
# 🔒 2. FASE DE LOGIN
# ==========================================
if not st.session_state['autenticado']:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        try: st.image("logo_sweet_teste.png", use_container_width=True)
        except: st.warning("🌸 Sweet Home Enxovais")
        st.markdown("<h2 style='text-align: center;'>Gestão Sweet</h2>", unsafe_allow_html=True)
        with st.form("form_login"):
            usuario_input = st.text_input("Usuário").strip()
            senha_input = st.text_input("Senha", type="password").strip()
            if st.form_submit_button("Entrar no Sistema 🚀", use_container_width=True):
                try:
                    usuarios_permitidos = st.secrets["usuarios"]
                    if usuario_input in usuarios_permitidos and str(usuarios_permitidos[usuario_input]) == senha_input:
                        st.session_state['autenticado'] = True
                        st.session_state['usuario_logado'] = usuario_input
                        st.rerun()
                    else: st.error("❌ Credenciais incorretas.")
                except Exception as e: st.error("Erro no cofre de senhas.")
    st.stop()

# ==========================================
# 🚀 3. CONEXÕES GSPREAD E CLOUDINARY
# ==========================================
ID_PLANILHA = "1lXUnGrWtwV-IfIiUbGzLH3P2T-h3b6Mr9NEBCpwulXg"
ESPECIFICACOES = [
    "https://spreadsheets.google.com/feeds", 
    'https://www.googleapis.com/auth/spreadsheets',
    "https://www.googleapis.com/auth/drive.file"
]

@st.cache_resource
def conectar_google():
    try:
        creds_info = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, ESPECIFICACOES)
        return gspread.authorize(creds).open_by_key(ID_PLANILHA)
    except Exception: return None

planilha_mestre = conectar_google()

# ☁️ Função de Upload Rápido para Cloudinary
def upload_para_cloudinary(file_bytes, file_name, pasta_destino):
    try:
        # Configura as chaves secretas do Cloudinary
        cloudinary.config(
            cloud_name = st.secrets["cloudinary"]["cloud_name"],
            api_key = st.secrets["cloudinary"]["api_key"],
            api_secret = st.secrets["cloudinary"]["api_secret"],
            secure = True
        )
        
        # Faz o upload criando subpastas automaticamente
        caminho_pasta = f"SweetHome/{pasta_destino}"
        
        resposta = cloudinary.uploader.upload(
            file_bytes,
            folder=caminho_pasta,
            public_id=file_name,
            resource_type="auto" # Aceita tanto imagem quanto PDF
        )
        # Retorna o ID único e o link super rápido do CDN
        return resposta.get('public_id'), resposta.get('secure_url')
    except Exception as e:
        st.error(f"Erro no Cloudinary: {e}")
        return None, None

@st.cache_resource(ttl=600)
def carregar_dados():
    if not planilha_mestre: return {}, {}, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    def ler_aba_seguro(nome):
        try:
            dados = planilha_mestre.worksheet(nome).get_all_values()
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
    
    banco_prod = {str(r.iloc[0]): {"nome": r.iloc[1], "custo": float(limpar_v(r.iloc[3]))} for _, r in df_inv.iterrows()} if not df_inv.empty else {}
    banco_cli = {str(r.iloc[0]): {"nome": str(r.iloc[1]), "fone": str(r.iloc[2])} for _, r in df_cli.iterrows()} if not df_cli.empty else {}
    return banco_prod, banco_cli, df_inv, df_fin, df_vendas, df_painel, df_cli

banco_de_produtos, banco_de_clientes, df_full_inv, df_financeiro, df_vendas_hist, df_painel_resumo, df_clientes_full = carregar_dados()

# --- BARRA LATERAL ---
with st.sidebar:
    try: st.image("logo_sweet_teste.png", use_container_width=True)
    except: st.write("🌸 **Sweet Home**")
    st.write(f"👋 Olá, **{st.session_state.get('usuario_logado', 'Usuária')}**!")
    st.divider()
    if st.button("Sair do Sistema 🚪", use_container_width=True):
        st.session_state['autenticado'] = False; st.rerun()

    menu_selecionado = st.radio("Navegação", ["🛒 Vendas", "💰 Financeiro", "📦 Estoque", "👥 Clientes", "📂 Documentos"], key="navegacao_principal")
    st.divider()
    modo_teste = st.toggle("🔬 Modo de Teste", value=False)
    if st.button("🔄 Sincronizar Planilha"): st.cache_resource.clear(); st.rerun()

    st.divider()
    with st.expander("🛡️ Backup do Sistema"):
        try:
            if not df_vendas_hist.empty: st.download_button("📥 Vendas", df_vendas_hist.to_csv(index=False).encode('utf-8'), f"Vendas_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", use_container_width=True)
            if not df_full_inv.empty: st.download_button("📥 Estoque", df_full_inv.to_csv(index=False).encode('utf-8'), f"Estoque_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", use_container_width=True)
            if not df_clientes_full.empty: st.download_button("📥 Clientes", df_clientes_full.to_csv(index=False).encode('utf-8'), f"Clientes_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", use_container_width=True)
            if not df_financeiro.empty: st.download_button("📥 Financeiro", df_financeiro.to_csv(index=False).encode('utf-8'), f"Financeiro_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", use_container_width=True)
        except: st.error("Dados indisponíveis para backup.")

# ==========================================
# --- SEÇÃO 1: VENDAS (INTACTA) ---
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
                    dt = st.date_input(f"{i+1}ª Parc.", datetime.now(), format="DD/MM/YYYY", key=f"vd_dp_{i}")
                    detalhes_p.append(dt.strftime("%d/%m/%Y"))

        col_esq, col_dir = st.columns(2)
        with col_esq:
            c_sel = st.selectbox("Cliente", ["*** NOVO CLIENTE ***"] + [f"{k} - {v['nome']}" for k, v in banco_de_clientes.items()])
            c_nome_novo = st.text_input("Nome (se novo)")
            c_zap = st.text_input("WhatsApp", value="" if c_sel == "*** NOVO CLIENTE ***" else banco_de_clientes.get(c_sel.split(" - ")[0], {}).get('fone', ""))

        with col_dir:
            p_sel = st.selectbox("Produto", [f"{k} - {v['nome']}" for k, v in banco_de_produtos.items()])
            cc1, cc2, cc3 = st.columns(3)
            qtd_v = cc1.number_input("Qtd", 1)
            val_v = cc2.number_input("Preço Un.", 0.0)
            desc_v = cc3.number_input("Desc (R$)", 0.0)
            vendedor = st.text_input("Vendedor(a)", value="Bia")

        if st.form_submit_button("Finalizar Venda 🚀"):
            if c_sel == "*** NOVO CLIENTE ***" and (not c_nome_novo or not c_zap): st.error("⚠️ Preencha Nome e Zap!"); st.stop()
            nome_cli = c_nome_novo.strip() if c_sel == "*** NOVO CLIENTE ***" else banco_de_clientes[c_sel.split(" - ")[0]]['nome']
            cod_cli = "CLI-TESTE" if (modo_teste or c_sel == "*** NOVO CLIENTE ***") else c_sel.split(" - ")[0]
            
            v_bruto = qtd_v * val_v; t_liq = v_bruto - desc_v
            cod_p = p_sel.split(" - ")[0]; nome_p = p_sel.split(" - ")[1].strip()
            custo_un = float(banco_de_produtos[cod_p].get('custo', 0.0)) if cod_p in banco_de_produtos else 0.0
            
            if not modo_teste:
                try:
                    aba_v = planilha_mestre.worksheet("VENDAS")
                    eh_parc = "Sim" if metodo == "Sweet Flex" else "Não"
                    f_atraso = '=SE(OU(INDIRETO("W"&LIN())="Pago"; INDIRETO("W"&LIN())="Em dia"); 0; MÁXIMO(0; HOJE() - INDIRETO("V"&LIN())))'
                    f_k = '=SE(INDIRETO("I"&LIN())=""; ""; ARRED(INDIRETO("I"&LIN()) * (1 - INDIRETO("J"&LIN())); 2))'
                    f_l = '=SE(INDIRETO("H"&LIN())=""; ""; ARRED(INDIRETO("H"&LIN()) * INDIRETO("K"&LIN()); 2))'
                    f_m = '=SE(INDIRETO("L"&LIN())=""; ""; ARRED(INDIRETO("L"&LIN()) - (INDIRETO("H"&LIN()) * INDIRETO("G"&LIN())); 2))'
                    f_n = '=SE(INDIRETO("L"&LIN())=""; ""; SEERRO(INDIRETO("M"&LIN()) / INDIRETO("L"&LIN()); ""))'
                    f_r = '=SE(INDIRETO("L"&LIN())=""; ""; SE(INDIRETO("P"&LIN())="Não"; INDIRETO("L"&LIN()); 0))'
                    
                    linha = ["", datetime.now().strftime("%d/%m/%Y"), cod_cli, nome_cli, cod_p, nome_p, custo_un, qtd_v, val_v, (desc_v/v_bruto if v_bruto>0 else 0), f_k, f_l, f_m, f_n, metodo, eh_parc, n_p, f_r, t_liq/n_p if eh_parc=="Sim" else 0, t_liq if eh_parc=="Não" else 0, t_liq if eh_parc=="Sim" else 0, detalhes_p[0] if eh_parc=="Sim" else "", "Pendente" if eh_parc=="Sim" else "Pago", f_atraso]
                    aba_v.insert_row(linha, index=aba_v.find("TOTAIS").row, value_input_option='USER_ENTERED')
                    st.success("✅ Venda registrada!"); st.cache_resource.clear()
                except Exception as e: st.error(f"Erro: {e}")
            
            st.session_state['historico_sessao'].insert(0, {"Data": datetime.now().strftime("%d/%m %H:%M"), "Cliente": nome_cli, "Produto": nome_p, "Total": f"R$ {t_liq:.2f}"})

    if st.session_state['historico_sessao']:
        st.write("### 📝 Histórico de Registros")
        st.dataframe(st.session_state['historico_sessao'], use_container_width=True, hide_index=True)

# ==========================================
# --- SEÇÃO 2: FINANCEIRO (INTACTA) ---
# ==========================================
elif menu_selecionado == "💰 Financeiro":
    st.markdown("### 📈 Resumo Geral Sweet Home")
    if not df_vendas_hist.empty:
        try:
            vendas_brutas = df_vendas_hist.iloc[:, 11].apply(limpar_v).sum()
            lucro_bruto = df_vendas_hist.iloc[:, 12].apply(limpar_v).sum()
            saldo_devedor = df_vendas_hist.iloc[:, 20].apply(limpar_v).sum()
            percentual_pendente = (saldo_devedor / vendas_brutas) * 100 if vendas_brutas > 0 else 0
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Vendas Totais", f"R$ {vendas_brutas:,.2f}")
            c2.metric("Lucro Bruto", f"R$ {lucro_bruto:,.2f}")
            c3.metric("Total Recebido", f"R$ {vendas_brutas - saldo_devedor:,.2f}")
            c4.metric("Saldo Devedor", f"R$ {saldo_devedor:,.2f}", delta=f"{percentual_pendente:.1f}%")

            st.progress(min(percentual_pendente/100, 1.0)) 

            with st.expander("📊 Análise de Desempenho", expanded=False):
                t_fat, t_pag = st.tabs(["📈 Diário", "💳 Meios"])
                with t_fat:
                    df_graf = df_vendas_hist.copy()
                    df_graf['DATA'] = pd.to_datetime(df_graf['DATA DA VENDA'], format='%d/%m/%Y', errors='coerce')
                    df_graf['VAL'] = df_graf['TOTAL R$'].apply(limpar_v)
                    vendas_dia = df_graf.groupby('DATA')['VAL'].sum().reset_index().set_index('DATA')
                    st.bar_chart(vendas_dia['VAL'], color="#FF69B4")
                with t_pag:
                    st.bar_chart(df_graf.groupby('FORMA DE PAGTO')['VAL'].sum(), color="#C71585")

        except Exception as e: st.warning(f"Erro: {e}")

    st.divider()
    with st.expander("➕ Lançar Novo Abatimento (FIFO)", expanded=False):
        with st.form("f_fifo_novo", clear_on_submit=True):
            c_pg = st.selectbox("Cliente", ["Selecione..."] + sorted([f"{k} - {v['nome']}" for k, v in banco_de_clientes.items()]))
            f1, f2, f3 = st.columns(3)
            v_pg = f1.number_input("Valor Pago (R$)", min_value=0.0)
            meio = f2.selectbox("Meio", ["Pix", "Dinheiro", "Cartão"])
            obs = f3.text_input("Obs", "Abatimento")
            
            if st.form_submit_button("Confirmar Pagamento ✅") and v_pg > 0 and c_pg != "Selecione...":
                try:
                    aba_v = planilha_mestre.worksheet("VENDAS")
                    df_v_viva = pd.DataFrame(aba_v.get_all_records())
                    df_v_viva['S_NUM'] = df_v_viva['SALDO DEVEDOR'].apply(limpar_v)
                    nome_c_alvo = " - ".join(c_pg.split(" - ")[1:])
                    pendentes = df_v_viva[(df_v_viva['CLIENTE'] == nome_c_alvo) & (df_v_viva['S_NUM'] > 0)].copy()
                    sobra = v_pg
                    for idx, row in pendentes.iterrows():
                        if sobra <= 0: break
                        lin = idx + 2; div_l = row['S_NUM']
                        if sobra >= div_l:
                            aba_v.update_acell(f"U{lin}", 0); aba_v.update_acell(f"W{lin}", "Pago"); sobra -= div_l
                        else:
                            aba_v.update_acell(f"U{lin}", div_l - sobra); sobra = 0
                    
                    planilha_mestre.worksheet("FINANCEIRO").append_row([datetime.now().strftime("%d/%m/%Y"), datetime.now().strftime("%H:%M"), c_pg.split(" - ")[0], nome_c_alvo, 0, v_pg, "PAGO", f"{meio}: {obs}"], value_input_option='USER_ENTERED')
                    st.success("✅ Recebido processado!"); st.cache_resource.clear(); st.rerun()
                except Exception as e: st.error(f"Erro FIFO: {e}")

# ==========================================
# --- SEÇÃO 3: ESTOQUE (INTACTA) ---
# ==========================================
elif menu_selecionado == "📦 Estoque":
    st.subheader("📦 Gestão de Estoque")
    df_estoque = df_full_inv.copy()
    if not df_estoque.empty:
        df_estoque['EST_NUM'] = pd.to_numeric(df_estoque['ESTOQUE ATUAL'], errors='coerce').fillna(0)
        c1, c2 = st.columns(2)
        c1.metric("Itens Catálogo", len(df_estoque))
        c2.metric("Esgotados", len(df_estoque[df_estoque['EST_NUM'] <= 0]))
        
        with st.expander("📊 Malha Fina e Curva ABC", expanded=False):
            criticos = df_estoque[df_estoque['EST_NUM'] <= 3]
            st.dataframe(criticos[['CÓD. PRÓDUTO', 'NOME DO PRODUTO', 'ESTOQUE ATUAL']], hide_index=True)

    st.divider()
    busca_radar = st.text_input("🔍 Pesquisar produto", placeholder="Código ou nome")
    if busca_radar and not df_estoque.empty:
        tl = limpar_texto(busca_radar)
        df_estoque['N_L'] = df_estoque['NOME DO PRODUTO'].apply(limpar_texto)
        df_estoque['C_L'] = df_estoque['CÓD. PRÓDUTO'].astype(str).str.lower().str.strip()
        res = df_estoque[df_estoque['N_L'].str.contains(tl, na=False) | df_estoque['C_L'].str.contains(tl, na=False)]
        
        if not res.empty:
            p_alvo = st.radio("Produto:", ["Novo..."] + [f"{r['CÓD. PRÓDUTO']} - {r['NOME DO PRODUTO']}" for _, r in res.iterrows()])
            if p_alvo != "Novo...":
                idx = df_estoque[df_estoque['CÓD. PRÓDUTO'] == p_alvo.split(" - ")[0]].index[0]
                acao = st.selectbox("Ação:", ["Selecione...", "1. Reposição", "2. Novo Lote", "3. Correção"])
                if acao == "1. Reposição":
                    with st.form("fr"):
                        qn = st.number_input("Qtd", 1)
                        if st.form_submit_button("Confirmar"):
                            aba = planilha_mestre.worksheet("INVENTÁRIO")
                            aba.update_acell(f"C{int(idx)+2}", int(pd.to_numeric(df_estoque.loc[idx, 'QUANTIDADE']) or 0) + qn)
                            st.success("Estoque Atualizado!"); st.cache_resource.clear(); st.rerun()

    with st.expander("➕ Cadastrar Novo Produto"):
        with st.form("f_est_original", clear_on_submit=True):
            n_c = st.text_input("Cód."); n_n = st.text_input("Nome"); n_q = st.number_input("Qtd", 0)
            n_custo = st.number_input("Custo (R$)", 0.0); n_v = st.number_input("Venda (R$)", 0.0)
            if st.form_submit_button("Salvar") and n_c and n_n:
                aba = planilha_mestre.worksheet("INVENTÁRIO")
                fe = '=SE(INDIRETO("C"&LIN())=""; ""; ARRED(INDIRETO("C"&LIN()) * INDIRETO("D"&LIN()); 2))'
                fh = '=SE(INDIRETO("C"&LIN())=""; ""; INDIRETO("C"&LIN()) - INDIRETO("G"&LIN()))'
                ln = [n_c, n_n, n_q, n_custo, fe, 3, 0, fh, n_v, datetime.now().strftime("%d/%m/%Y"), ""]
                cel = aba.find("TOTAIS")
                if cel: aba.insert_row(ln, index=cel.row, value_input_option='USER_ENTERED')
                else: aba.append_row(ln, value_input_option='USER_ENTERED')
                st.success("Cadastrado!"); st.cache_resource.clear(); st.rerun()

# ==========================================
# --- SEÇÃO 4: CLIENTES (INTACTA CRM) ---
# ==========================================
elif menu_selecionado == "👥 Clientes":
    st.subheader("👥 Gestão e CRM")
    if not df_vendas_hist.empty and not df_clientes_full.empty:
        df_v_crm = df_vendas_hist.copy()
        df_v_crm['DT'] = pd.to_datetime(df_v_crm['DATA DA VENDA'], format='%d/%m/%Y', errors='coerce')
        ult = df_v_crm.groupby('CÓD. CLIENTE')['DT'].max().reset_index()
        ult['DIAS'] = (pd.to_datetime(datetime.now().date()) - ult['DT']).dt.days
        sumidas = ult[ult['DIAS'] >= 60]
        
        with st.expander(f"🎯 CRM: {len(sumidas)} clientes sumidas", expanded=False):
            if not sumidas.empty:
                df_c = df_clientes_full.rename(columns={df_clientes_full.columns[0]: 'C', df_clientes_full.columns[1]: 'N', df_clientes_full.columns[2]: 'Z'})
                full_s = sumidas.merge(df_c[['C', 'N', 'Z']], left_on='CÓD. CLIENTE', right_on='C', how='left')
                for _, r in full_s.iterrows():
                    st.write(f"👤 **{r['N']}** (Ausente {int(r['DIAS'])} dias)")
    
    with st.expander("➕ Nova Cliente"):
        with st.form("f_cli"):
            n = st.text_input("Nome"); z = st.text_input("Zap"); e = st.text_input("Endereço")
            if st.form_submit_button("Salvar") and n and z:
                aba = planilha_mestre.worksheet("CARTEIRA DE CLIENTES")
                aba.append_row([f"CLI-{len(aba.get_all_values()):03d}", n, z, e, datetime.now().strftime("%d/%m/%Y"), 0, "", "Completo" if e else "Incompleto"], value_input_option='USER_ENTERED')
                st.success("Cadastrada!"); st.cache_resource.clear(); st.rerun()

# ==========================================
# 🌟 SEÇÃO 5: DOCUMENTOS & FILA ODOO (CLOUDINARY) 🌟
# ==========================================
elif menu_selecionado == "📂 Documentos":
    st.subheader("📂 Cofre Digital & Fila Odoo")

    # Tenta ler a aba de documentos
    try:
        dados_doc = planilha_mestre.worksheet("DOCUMENTOS").get_all_values()
        df_docs = pd.DataFrame(dados_doc[1:], columns=dados_doc[0]) if len(dados_doc) > 1 else pd.DataFrame()
    except: df_docs = pd.DataFrame()

    # 🚀 O MOTOR ODOO (Linha de Montagem)
    with st.expander("🚀 Linha de Montagem Odoo (Site)", expanded=True):
        t_falta, t_pronto = st.tabs(["🔴 1. Falta Foto (Bia)", "🟢 2. Pronto p/ Site (Você)"])
        
        with t_falta:
            st.write("**Produtos no estoque aguardando foto para o site:**")
            if not df_full_inv.empty:
                prods_com_foto = []
                if not df_docs.empty and 'VINCULO' in df_docs.columns:
                    fotos = df_docs[df_docs['TIPO'] == "Foto de Produto"]
                    prods_com_foto = [str(p).split(" - ")[0].strip() for p in fotos['VINCULO'].dropna() if " - " in str(p)]
                
                df_falta = df_full_inv[~df_full_inv['CÓD. PRÓDUTO'].astype(str).str.strip().isin(prods_com_foto)]
                if not df_falta.empty:
                    st.dataframe(df_falta[['CÓD. PRÓDUTO', 'NOME DO PRODUTO', 'ESTOQUE ATUAL']], hide_index=True)
                else: st.success("🎉 Nenhuma pendência! O estoque inteiro tem foto.")

        with t_pronto:
            st.write("**Fotos tiradas! Coloque no site e marque como publicado:**")
            if not df_docs.empty and 'STATUS_ODOO' in df_docs.columns:
                prontos = df_docs[(df_docs['TIPO'] == "Foto de Produto") & (df_docs['STATUS_ODOO'] == "Pronto para Site")]
                if not prontos.empty:
                    for idx, r in prontos.iterrows():
                        c1, c2, c3 = st.columns([3, 1, 1])
                        c1.write(f"📦 **{r['VINCULO']}**")
                        c2.link_button("🖼️ Ver Foto", r['LINK_DRIVE'], use_container_width=True)
                        if c3.button("✅ Publicado", key=f"btn_odoo_{idx}"):
                            aba_doc = planilha_mestre.worksheet("DOCUMENTOS")
                            cell = aba_doc.find(r['ID_ARQUIVO'])
                            aba_doc.update_cell(cell.row, 7, "Publicado no Odoo")
                            st.success("Atualizado!"); st.cache_resource.clear(); st.rerun()
                        st.divider()
                else: st.info("Sua fila de trabalho está limpa.")

    st.divider()

    # 📤 ÁREA DE UPLOAD (Nomenclatura Automática + Cloudinary)
    st.write("### 📤 Enviar Arquivo")
    
    lista_categorias = ["Foto de Produto", "Nota Fiscal", "Comprovante", "Recibo / Pgto", "Contrato", "Outros"]
    cat_escolhida = st.selectbox("1️⃣ Categoria do Documento", lista_categorias)
    
    with st.form("form_upload_cloudinary", clear_on_submit=True):
        st.write("2️⃣ **Detalhes e Arquivo**")
        
        vinc_cli = "Nenhum"
        vinc_prod = "Nenhum"
        nome_livre = ""
        
        if cat_escolhida in ["Foto de Produto", "Nota Fiscal"]:
            st.info("📦 O sistema dará o nome do arquivo automaticamente com base no produto.")
            opcoes_prod = ["Nenhum"] + [f"{k} - {v['nome']}" for k, v in banco_de_produtos.items()]
            vinc_prod = st.selectbox("Selecione o Produto:", opcoes_prod)
        
        elif cat_escolhida in ["Comprovante", "Recibo / Pgto"]:
            st.info("👤 O sistema dará o nome do arquivo automaticamente com base na cliente.")
            opcoes_cli = ["Nenhum"] + [f"{k} - {v['nome']}" for k, v in banco_de_clientes.items()]
            vinc_cli = st.selectbox("Selecione a Cliente:", opcoes_cli)
        
        else:
            nome_livre = st.text_input("Nome/Descrição Breve")

        arquivo_subido = st.file_uploader("3️⃣ Escolha o arquivo (Imagem/PDF)", type=['png', 'jpg', 'jpeg', 'pdf'])
        
        if st.form_submit_button("Salvar no Cofre 🔒"):
            erro = False
            if not arquivo_subido:
                st.error("⚠️ Você esqueceu de anexar o arquivo!"); erro = True
            elif cat_escolhida in ["Foto de Produto", "Nota Fiscal"] and vinc_prod == "Nenhum":
                st.error("⚠️ Para esta categoria, você deve selecionar um produto."); erro = True
            elif cat_escolhida in ["Comprovante", "Recibo / Pgto"] and vinc_cli == "Nenhum":
                st.error("⚠️ Para esta categoria, você deve selecionar uma cliente."); erro = True
            elif cat_escolhida in ["Contrato", "Outros"] and not nome_livre:
                st.error("⚠️ Por favor, digite um nome para o documento."); erro = True

            if not erro:
                if vinc_prod != "Nenhum":
                    nome_gerado = f"[{cat_escolhida.upper()}] {vinc_prod}"
                    vinculo_final = vinc_prod
                elif vinc_cli != "Nenhum":
                    nome_gerado = f"[{cat_escolhida.upper()}] {vinc_cli}"
                    vinculo_final = vinc_cli
                else:
                    nome_gerado = f"[{cat_escolhida.upper()}] {nome_livre}"
                    vinculo_final = "-"
                
                # Cloudinary não precisa da extensão no public_id, mas a gente formata pra ficar bonito no link
                nome_limpo = nome_gerado.replace("/", "-").replace(":", "")

                with st.spinner(f"Subindo para o servidor seguro... ⏳"):
                    f_id, f_link = upload_para_cloudinary(arquivo_subido.getvalue(), nome_limpo, cat_escolhida)
                    
                    if f_id:
                        try:
                            aba_doc = planilha_mestre.worksheet("DOCUMENTOS")
                            if len(aba_doc.get_all_values()) == 0:
                                aba_doc.append_row(["DATA", "TIPO", "NOME", "ID_ARQUIVO", "LINK_DRIVE", "VINCULO", "STATUS_ODOO"])
                            
                            status_odoo = "Pronto para Site" if cat_escolhida == "Foto de Produto" else "-"
                            
                            aba_doc.append_row([
                                datetime.now().strftime("%d/%m/%Y %H:%M"),
                                cat_escolhida, nome_limpo, f_id, f_link, vinculo_final, status_odoo
                            ], value_input_option='USER_ENTERED')
                            st.success(f"✅ Arquivado com sucesso!"); st.cache_resource.clear(); st.rerun()
                        except Exception as e: st.error(f"Erro na planilha: {e}")

    st.divider()
    st.write("### 🗂️ Histórico Geral de Documentos")
    
    if not df_docs.empty:
        busca_doc = st.text_input("🔍 Pesquisar (Ex: código, nome, categoria...)")
        if busca_doc:
            df_docs = df_docs[df_docs.apply(lambda r: busca_doc.lower() in str(r).lower(), axis=1)]

        for _, r in df_docs.sort_index(ascending=False).iterrows():
            with st.container():
                col_a, col_b, col_c = st.columns([1, 3, 1])
                col_a.write(f"📅 {str(r['DATA']).split(' ')[0]}")
                col_b.write(f"**{r['TIPO']}**\n\n<small>{r['NOME']}</small>", unsafe_allow_html=True)
                col_c.link_button("👁️ Abrir", r['LINK_DRIVE'], use_container_width=True)
                st.divider()
    else:
        st.info("O cofre geral está vazio. Comece a enviar arquivos!")
