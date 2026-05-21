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
    /* Força o container da tabela padrão a sumir caso ainda seja chamado */
    div[data-testid="stTable"] {
        width: 100% !important;
        overflow-x: hidden !important;
    }
    /* Estilização para garantir que os blocos de Markdown usem o espaço ideal */
    .reportview-container .main .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 2. Autenticação Segura
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

# Criação correta das abas na raiz do script
aba_config, aba_simulado, aba_progresso = st.tabs(["⚙️ Configurar", "🔥 Simulado", "📊 Meu Progresso"])

# --- ABA 1: CONFIGURAÇÃO ---
with aba_config:
    topico_selecionado = st.selectbox("Escolha o Tópico do Exame:", MODULOS_ADMIN)
    nivel = st.selectbox("Escolha o Nível de Dificuldade:", ["Iniciante", "Intermediário", "Especialista"])
    
    if st.button("🚀 Gerar Simulado Completo"):
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
            
            resp = st.radio(f"Selecione a resposta para a Q{i+1}:", q['opcoes'], key=f"q_{i}", index=None, disabled=st.session_state.get('corrigido', False))
            
            if resp:
                st.session_state.respostas_usuario[i] = resp[0]

            if st.session_state.get('corrigido'):
                user_choice = st.session_state.respostas_usuario.get(i
