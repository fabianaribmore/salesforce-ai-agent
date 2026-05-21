import streamlit as st
import pandas as pd
from openai import OpenAI
import json
import os
from datetime import datetime
import zoneinfo
import re

# 1. Configuração da Página
st.set_page_config(page_title="Simulado - Salesforce Administrator", page_icon="🛡️", layout="wide")

# --- CSS ULTRA-COMPACTO E ESTILIZAÇÃO DOS CARDS RESPONSIVOS ---
st.markdown(
    """
    <style>
    div[data-testid="stTable"] {
        width: 100% !important;
        overflow-x: hidden !important;
    }
    .reportview-container .main .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
    
    /* Caixa de feedback de Erro Neutra e Adaptável (Preto no Light / Branco no Dark) */
    .feedback-erro-container {
        padding: 14px;
        margin: 12px 0px;
        border-radius: 8px;
        background-color: rgba(128, 128, 128, 0.1);
        border: 1.5px solid rgba(128, 128, 128, 0.4);
        color: var(--text-color);
        font-size: 14px;
        font-weight: 500;
    }
    .feedback-erro-destaque {
        color: #E65100;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 2. Autenticação Secura
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- SEGURANÇA: EVITAR ATTRIBUTE ERROR POR CHAVES ANTIGAS ---
if 'simulado_ativo' not in st.session_state:
    st.session_state.clear()
    st.session_state.simulado_ativo = False
    st.session_state.corrigido = False
    st.session_state.respostas_usuario = {}
    st.session_state.questoes = []
    st.session_state.confirmou_salvamento = False

# --- REQUISITOS DA PROVA SALESFORCE ADMIN (CRT-101) ---
MODULOS_ADMIN = [
    "Configuração e Objetos",
    "Segurança e Acesso",
    "Automação de Processos/Flow",
    "Relatórios e Dashboards",
    "Guia Geral do Administrador"
]

# --- FUNÇÕES DE APOIO ---
def carregar_dados():
    arquivo = 'historico_simulados.csv'
    if os.path.exists(arquivo):
        return pd.read_csv(arquivo)
    return pd.DataFrame(columns=['Data', 'Tema', 'Dificuldade', 'Acertos', 'Total', 'Score %'])

def salvar_no_historico(tema, difficulty, pontos, total):
    arquivo = 'historico_simulados.csv'
    fuso_brasil = zoneinfo.ZoneInfo("America/Sao_Paulo")
    data_atual = datetime.now(fuso_brasil).strftime("%d/%m/%Y %H:%M")
    
    score = int((pontos / total) * 100)
    novo_registro = pd.DataFrame([[data_atual, tema, difficulty, pontos, total, f"{score}%"]], 
                                columns=['Data', 'Tema', 'Dificuldade', 'Acertos', 'Total', 'Score %'])
    df_atual = carregar_dados()
    df_final = pd.concat([df_atual, novo_registro], ignore_index=True)
    df_final.to_csv(arquivo, index=False)
    return score

def gerar_questoes_ia(tema, nivel):
    prompt = f"""
    Gere um caderno de testes COMPLETAMENTE ALEATÓRIO e INÉDITO contendo exatamente 10 perguntas de múltikla escolha sobre o módulo: {tema}.
    Nível de complexidade exigido: {nivel}.
    Mecânica de Alinhamento: Exame oficial Salesforce Certified Administrator (CRT-101).
    Importante: Varie os cenários de negócios, use diferentes objetos e requisitos práticos a cada execução para que o aluno nunca estude com o mesmo padrão.
    
    Certifique-se de preencher rigorosamente todos os 10 objetos no array JSON.
    Responda EXCLUSIVAMENTE no formato JSON estruturado abaixo:
    {{
      "perguntas": [
        {{
          "pergunta": "Texto dinâmico e prático do cenário ou questão", 
          "opcoes": ["A) Opção 1", "B) Opção 2", "C) Opção 3", "D) Opção 4"], 
          "correta": "A/B/C/D",
          "explicacao": "Análise técnica justificando a alternativa correta baseada nas regras de arquitetura da Salesforce."
        }}
      ]
    }}
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini", 
        messages=[{"role": "system", "content": "Você é um avaliador Salesforce dinâmico. Sua meta é criar 10 questões originais, variadas e nunca repetidas dentro do bloco JSON."},
                  {"role": "user", "content": prompt}],
        response_format={ "type": "json_object" },
        temperature=0.9
    )
    dados = json.loads(response.choices[0].message.content)
    return dados.get('perguntas', [])[:10]

# --- DESIGN PRINCIPAL ---
st.markdown('<h2 style="font-size: 20px; margin-bottom: 12px; font-weight: 700; color: #1E88E5;">🛡️ Simulado - Salesforce Administrator</h2>', unsafe_allow_html=True)

# Criação das abas
aba_config, aba_simulado, aba_progresso = st.tabs(["⚙️ Configurar", "🔥 Simulado", "📊 Meu Progresso"])

# --- ABA 1: CONFIGURAÇÃO ---
with aba_config:
    topico_selecionado = st.selectbox("Escolha o Tópico do Exame:", MODULOS_ADMIN)
    nivel = st.selectbox("Escolha o Nível de Dificuldade:", ["Iniciante", "Intermediário", "Especialista"])
    
    if st.button("🚀 Gerar Simulado"):
        with st.spinner("Sorteando 10 questões inéditas para o seu caderno..."):
            st.session_state.respostas_usuario = {}
            st.session_state.corrigido = False
            st.session_state.confirmou_salvamento = False
            
            st.session_state.questoes = gerar_questoes_ia(topico_selecionado, nivel)
            st.session_state.topico_atual = topico_selecionado
            st.session_state.nivel_atual = nivel
            st.session_state.simulado_ativo = True
            st.success("Simulado pronto! Vá para a aba '🔥 Simulado'.")

# --- ABA 2: O SIMULADO ---
with aba_simulado:
    if st.session_state.get('simulado_ativo') and st.session_state.get('questoes'):
        st.markdown(f"### 📝 Prova Ativa: {st.session_state.get('topico_atual')}")
        st.caption(f"Nível selecionado: {st.session_state.get('nivel_atual')} | Alvo para aprovação: 65%")
        st.write("---")
        
        for i, q in enumerate(st.session_state.questoes):
            st.markdown(f"##### **Questão {i+1} de {len(st.session_state.questoes)}**")
            st.write(q['pergunta'])
            
            resp = st.radio("Selecione a sua resposta alternativa:", q['opcoes'], key=f"q_{i}", index=None, disabled=st.session_state.get('corrigido', False))
            
            if resp:
                st.session_state.respostas_usuario[i] = resp[0]

            if st.session_state.get('corrigido'):
                user_choice = st.session_state.respostas_usuario.get(i)
                if user_choice == q['correta']:
                    st.success(f"✅ Correto! Gabarito: {q['correta']}")
                else:
                    # Caixa de erro neutra que segue a cor do tema do usuário automaticamente
                    html_erro = f"""
                    <div class="feedback-erro-container">
                        <span class="feedback-erro-destaque">⚠️ Incorreto.</span> 
                        Sua escolha: {user_choice if user_choice else 'Nenhuma'} &nbsp;|&nbsp; 
                        Gabarito Correto: <span style="font-weight: 700; color: #4CAF50;">{q['correta']}</span>
                    </div>
                    """
                    st.markdown(html_erro, unsafe_allow_html=True)
                    
                with st.expander("💡 Ver Justificativa Técnica"):
                    st.write(q['explicacao'])
            st.markdown("---")

        if not st.session_state.get('corrigido') and not st.session_state.get('confirmou_salvamento'):
            if st.button("🏁 Finalizar e Corrigir Simulado"):
                total_questoes = len(st.session_state.questoes)
                
                if len(st.session_state.respostas_usuario) < total_questoes:
                    st.error("⚠️ Atenção! Você não respondeu todas as questões do caderno.")
                    st.markdown("<span style='font-size: 14px; font-weight: 700; display:block; margin-bottom:10px;'>📋 Painel de Revisão do Simulado</span>", unsafe_allow_html=True)
                    
                    grid_html = '<div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; justify-content: flex-start;">'
                    for idx in range(total_questoes):
                        respondida = idx in st.session_state.respostas_usuario
                        bg_color = "#2E7D32" if respondida else "#757575"
                        text_color = "#FFFFFF"
                        
                        grid_html += f'<div style="width: 36px; height: 36px; background-color: {bg_color}; color: {text_color}; display: flex; align-items: center; justify-content: center; font-weight: 700; border-radius: 6px; font-size: 14px;">{idx + 1}</div>'
                    grid_html += '</div>'
                    
                    legenda_html = """
                    <div style="display: flex; gap: 15px; font-size: 11px; font-weight: 600; margin-bottom: 15px;">
                        <div style="display: flex; align-items: center; gap: 5px;"><div style="width: 12px; height: 12px; background-color: #2E7D32; border-radius: 3px;"></div> Respondida</div>
                        <div style="display: flex; align-items: center; gap: 5px;"><div style="width: 12px; height: 12px; background-color: #757575; border-radius: 3px;"></div> Em Branco</div>
                    </div>
                    """
                    st.markdown(grid_html, unsafe_allow_html=True)
                    st.markdown(legenda_html, unsafe_allow_html=True)
                else:
                    st.session_state.confirmou_salvamento = True
                    st.rerun()

        if st.session_state.get('confirmou_salvamento'):
            st.markdown("#### 💾 Deseja salvar este progresso no seu histórico?")
            col_btn1, col_btn2 = st.columns(2)
            
            if col_btn1.button("✅ Sim, Salvar e Corrigir"):
                acertos = sum(1 for i, q in enumerate(st.session_state.questoes) if st.session_state.respostas_usuario.get(i) == q['correta'])
                salvar_no_historico(st.session_state.topico_atual, st.session_state.nivel_atual, acertos, len(st.session_state.questoes))
                st.session_state.corrigido = True
                st.session_state.confirmou_salvamento = False
                st.rerun()
                
            if col_btn2.button("❌ Não, Apenas Corrigir Sem Salvar"):
                st.session_state.corrigido = True
                st.session_state.confirmou_salvamento = False
                st.rerun()
    else:
        st.info("Nenhum simulado ativo. Monte a configuração na primeira aba para iniciar!")

# --- ABA 3: PROGRESSO COM LEITURA ADAPTÁVEL BASEADA NO TEMA ---
with aba_progresso:
    df = carregar_dados()
    
    if not df.empty:
        df['Tema'] = df['Tema'].apply(lambda x: re.sub(r'\s*\(\d+%\)\s*', '', str(x)).strip())
        df['Score_Num'] = df['Score %'].astype(str).str.replace('%','').astype(int)
        
        media_geral = int(df['Score_Num'].mean())
        status_aprovacao = "Aprovado 🎉" if media_geral >= 65 else "Abaixo da Meta"
        
        col_kpi1, col_kpi2 = st.columns([1, 2])
        with col_kpi1:
            st.metric(label="Média Geral de Acertos", value=f"{media_geral}%", delta=status_aprovacao, delta_color="normal" if media_geral >= 65 else "inverse")
        
        st.write("---")
        
        st.markdown('<span style="font-size: 16px; font-weight: 700; color: #1E88E5; display: block; margin-bottom: 16px;">📋 Diagnóstico de Desempenho por Tópico</span>', unsafe_allow_html=True)
        
        df_modulos = df.groupby('Tema').agg({'Acertos': 'sum', 'Total': 'sum'}).reset_index()
        df_modulos.columns = ['Módulo', 'Total Acertos', 'Total Questões']
        df_modulos['Porcentagem_Valor'] = ((df_modulos['Total Acertos'] / df_modulos['Total Questões']) * 100).astype(int)
        
        df_modulos = df_modulos.sort_values(by='Porcentagem_Valor', ascending=True)
        
        for idx, row in df_modulos.iterrows():
            pct = row['Porcentagem_Valor']
            modulo_nome = row['Módulo']
            
            # CONFIGURAÇÃO DE CORES: Amarelinho para Prioridade Alta e Verde para Meta Atingida
            if pct < 65:
                texto_acao = "Prioridade Alta"
                cor_fundo_badge = "#FBC02D"  # Amarelo equilibrado e visível
            elif pct < 80:
                texto_acao = "Meta Atingida"
                cor_fundo_badge = "#2E7D32"  # Verde focado em aprovação
            else:
                texto_acao = "Excelente"
                cor_fundo_badge = "#1565C0"  # Azul tecnológico
            
            # HTML Dinâmico: usa var(--text-color) tanto na porcentagem quanto no texto do botão 
            # Garantindo Branco no tema escuro e Preto no tema claro!
            card_html = f"""
            <div style="
                background-color: transparent;
                border-bottom: 1px solid rgba(128, 128, 128, 0.2);
                padding: 14px 4px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 12px;
            ">
                <div style="flex: 1;">
                    <div style="font-size: 15px; font-weight: 600; color: var(--text-color); line-height: 1.3;">
                        {modulo_nome}
                    </div>
                    <div style="font-size: 13px; color: var(--text-color); opacity: 0.9; margin-top: 4px;">
                        Aproveitamento: <strong style="color: var(--text-color); font-size: 14px; font-weight: 700;">{pct}%</strong>
                    </div>
                </div>
                <div style="
                    background-color: {cor_fundo_badge};
                    color: var(--text-color) !important;
                    font-size: 11px;
                    font-weight: 700;
                    padding: 6px 14px;
                    border-radius: 6px;
                    text-transform: uppercase;
                    letter-spacing: 0.6px;
                    white-space: nowrap;
                    text-align: center;
                    box-shadow: 0px 1px 2px rgba(0,0,0,0.15);
                ">
                    {texto_acao}
                </div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)
            
    else:
        st.info("O histórico está vazio. Faça um teste para ativar o painel!")
