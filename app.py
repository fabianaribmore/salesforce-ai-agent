import streamlit as st
import pandas as pd
from openai import OpenAI
import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

# 1. Configuração da Página
st.set_page_config(page_title="Salesforce Admin Exam Prep", page_icon="🛡️", layout="wide")

# 2. Autenticação (Coloque sua chave aqui)
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


# --- BANCO DE LINKS OFICIAIS ---
LINKS_CERTIFICACAO = {
    "Configuração e Objetos (20%)": "https://help.salesforce.com/s/articleView?id=sf.dev_object_overview.htm&type=5",
    "Segurança e Acesso (14%)": "https://help.salesforce.com/s/articleView?id=sf.security_overview.htm&type=5",
    "Automação de Processos/Flow (16%)": "https://help.salesforce.com/s/articleView?id=sf.flow.htm&type=5",
    "Relatórios e Dashboards (10%)": "https://help.salesforce.com/s/articleView?id=sf.reports_overview.htm&type=5",
    "Guia Geral do Administrador": "https://help.salesforce.com/s/articleView?id=sf.admin_setup_guide.htm&type=5",
    "Personalizado (Usar link do campo abaixo)": "Personalizado"
}

# --- FUNÇÕES DE APOIO ---
def carregar_dados():
    arquivo = 'historico_simulados.csv'
    if os.path.exists(arquivo):
        return pd.read_csv(arquivo)
    return pd.DataFrame(columns=['Data', 'Tema', 'Dificuldade', 'Acertos', 'Total', 'Score %'])

def salvar_no_historico(tema, dificuldade, pontos, total):
    arquivo = 'historico_simulados.csv'
    data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")
    score = int((pontos / total) * 100)
    novo_registro = pd.DataFrame([[data_atual, tema, dificuldade, pontos, total, f"{score}%"]], 
                                columns=['Data', 'Tema', 'Dificuldade', 'Acertos', 'Total', 'Score %'])
    df_atual = carregar_dados()
    df_final = pd.concat([df_atual, novo_registro], ignore_index=True)
    df_final.to_csv(arquivo, index=False)

def extrair_texto_url(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        for script in soup(["script", "style"]):
            script.extract()
        texto = soup.get_text(separator=' ')
        return " ".join(texto.split())[:5000] # Limite para não estourar tokens
    except Exception as e:
        st.error(f"Erro ao acessar a documentação: {e}")
        return None

def gerar_questoes_ia(tema, nivel, contexto_web):
    # Correção do erro de variável NameError: contexto_web agora é usado corretamente
    base_info = f"Baseie-se neste conteúdo oficial da Salesforce: {contexto_web}" if contexto_web else "Use seu conhecimento geral de Salesforce."
    
    prompt = f"""
    {base_info}
    Gere exatamente 10 perguntas de múltipla escolha sobre Salesforce {tema}, nível {nivel}.
    Foque em cenários de prova de certificação Administrator (CRT-101).
    Responda EXCLUSIVAMENTE em formato JSON:
    {{
      "perguntas": [
        {{
          "pergunta": "Texto da pergunta", 
          "opcoes": ["A) ", "B) ", "C) ", "D) "], 
          "correta": "A",
          "explicacao": "Explicação técnica baseada na documentação."
        }}
      ]
    }}
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini", # Modelo mais rápido e econômico
        messages=[{"role": "system", "content": "Você é um instrutor Salesforce certificado."},
                  {"role": "user", "content": prompt}],
        response_format={ "type": "json_object" }
    )
    dados = json.loads(response.choices[0].message.content)
    return dados.get('perguntas', [])[:10]

# --- INTERFACE ---
st.sidebar.title("🛡️ Admin Exam Prep")
aba = st.sidebar.radio("Navegação:", ["🔥 Simulado por Tópico", "📊 Meu Progresso"])

st.sidebar.markdown("---")
topico_selecionado = st.sidebar.selectbox("Tópico do Exame:", list(LINKS_CERTIFICACAO.keys()))

# Gerencia o link personalizado
url_manual = st.sidebar.text_input("🔗 Link Personalizado (opcional):", placeholder="Cole um link do Help Salesforce...")

if aba == "🔥 Simulado por Tópico":
    st.title("🎓 Preparatório Salesforce Administrator")
    st.info(f"Tópico atual: **{topico_selecionado}**")

    nivel = st.selectbox("Nível de dificuldade:", ["Iniciante", "Intermediário", "Especialista"])

    if st.button("🚀 Gerar Simulado Baseado na Documentação"):
        # Define qual URL usar
        url_para_ler = url_manual if topico_selecionado == "Personalizado (Usar link do campo abaixo)" else LINKS_CERTIFICACAO[topico_selecionado]
        
        with st.spinner("Analisando documentação oficial..."):
            conteudo = extrair_texto_url(url_para_ler)
            # Chama a função garantindo que o contexto_web seja enviado
            st.session_state.questoes = gerar_questoes_ia(topico_selecionado, nivel, conteudo)
            st.session_state.respostas_usuario = {}
            st.session_state.corrigido = False
            st.session_state.simulado_ativo = True

    # Exibição das Questões
    if st.session_state.get('simulado_ativo'):
        for i, q in enumerate(st.session_state.questoes):
            st.subheader(f"Questão {i+1}")
            st.write(q['pergunta'])
            
            # index=None para não vir nada marcado
            resp = st.radio(f"Selecione sua resposta para a Q{i+1}:", q['opcoes'], key=f"q_{i}", index=None, disabled=st.session_state.get('corrigido', False))
            
            if resp:
                st.session_state.respostas_usuario[i] = resp[0] # Pega apenas a letra (A, B, C...)

            if st.session_state.get('corrigido'):
                user_choice = st.session_state.respostas_usuario.get(i)
                if user_choice == q['correta']:
                    st.success(f"✅ Correto! Resposta: {q['correta']}")
                else:
                    st.error(f"❌ Incorreto. Você marcou {user_choice if user_choice else 'Vazio'}, a correta era {q['correta']}.")
                
                with st.expander("💡 Explicação Técnica"):
                    st.write(q['explicacao'])
            st.markdown("---")

        if not st.session_state.get('corrigido'):
            if st.button("✅ Finalizar Simulado"):
                acertos = sum(1 for i, q in enumerate(st.session_state.questoes) if st.session_state.respostas_usuario.get(i) == q['correta'])
                st.session_state.corrigido = True
                salvar_no_historico(topico_selecionado, nivel, acertos, len(st.session_state.questoes))
                st.balloons()
                st.rerun()

elif aba == "📊 Meu Progresso":
    st.title("📊 Histórico de Estudos")
    df = carregar_dados()
    if not df.empty:
        st.table(df)
        df['Score_Num'] = df['Score %'].str.replace('%','').astype(int)
        st.line_chart(df.set_index('Data')['Score_Num'])
    else:
        st.info("Complete seu primeiro simulado para ver seu progresso aqui!")