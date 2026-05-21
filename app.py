import streamlit as st
import pandas as pd
from openai import OpenAI
import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import zoneinfo

# 1. Configuração da Página
st.set_page_config(page_title="Simulado - Salesforce Admin", page_icon="🛡️", layout="wide")

# 2. Autenticação Segura
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- REQUISITOS DA PROVA SALESFORCE ADMIN (CRT-101) ---
PESOS_MODULOS = {
    "Configuração e Objetos (20%)": 20,
    "Segurança e Acesso (14%)": 14,
    "Automação de Processos/Flow (16%)": 16,
    "Relatórios e Dashboards (10%)": 10,
    "Guia Geral do Administrador": 40  
}

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
    fuso_brasil = zoneinfo.ZoneInfo("America/Sao_Paulo")
    data_atual = datetime.now(fuso_brasil).strftime("%d/%m/%Y %H:%M")
    
    score = int((pontos / total) * 100)
    novo_registro = pd.DataFrame([[data_atual, tema, difficulty if 'difficulty' in locals() else dificuldade, pontos, total, f"{score}%"]], 
                                columns=['Data', 'Tema', 'Dificuldade', 'Acertos', 'Total', 'Score %'])
    # Pequena correção preventiva caso o nome antigo escape
    novo_registro.columns = ['Data', 'Tema', 'Dificuldade', 'Acertos', 'Total', 'Score %']
    df_atual = carregar_dados()
    df_final = pd.concat([df_atual, novo_registro], ignore_index=True)
    df_final.to_csv(arquivo, index=False)
    return score

def extrair_texto_url(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        for script in soup(["script", "style"]):
            script.extract()
        texto = soup.get_text(separator=' ')
        return " ".join(texto.split())[:5000]
    except Exception as e:
        st.error(f"Erro ao acessar a documentação: {e}")
        return None

def gerar_questoes_ia(tema, nivel, contexto_web):
    base_info = f"Baseie-se neste conteúdo oficial da Salesforce: {contexto_web}" if contexto_web else "Use seu conhecimento geral de Salesforce."
    
    # Alterado o prompt explicitamente para pedir 15 questões
    prompt = f"""
    {base_info}
    Gere exatamente 15 perguntas de múltipla escolha sobre Salesforce {tema}, nível {nivel}.
    Foque em cenários práticos e realistas de prova de certificação Administrator (CRT-101).
    Responda EXCLUSIVAMENTE em formato JSON estruturado:
    {{
      "perguntas": [
        {{
          "pergunta": "Texto completa do cenário ou questão", 
          "opcoes": ["A) Opção 1", "B) Opção 2", "C) Opção 3", "D) Opção 4"], 
          "correta": "A",
          "explicacao": "Explicação detalhada do porquê esta alternativa está correta."
        }}
      ]
    }}
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini", 
        messages=[{"role": "system", "content": "Você é um instrutor e avaliador sênior de certificações Salesforce."},
                  {"role": "user", "content": prompt}],
        response_format={ "type": "json_object" }
    )
    dados = json.loads(response.choices[0].message.content)
    return dados.get('perguntas', [])[:15]

# --- DESIGN PRINCIPAL ---
st.markdown('<h2 style="font-size: 24px; margin-bottom: 10px;">🎓 Simulado - Salesforce Admin</h2>', unsafe_allow_html=True)

aba_config, aba_simulado, aba_progresso = st.tabs(["⚙️ Configurar", "🔥 Simulado", "📊 Meu Progresso"])

# --- ABA 1: CONFIGURAÇÃO ---
with aba_config:
    st.write("### 🛠️ Configurar Novo Teste (15 Questões)")
    
    topico_selecionado = st.selectbox("Escolha o Tópico do Exame:", list(LINKS_CERTIFICACAO.keys()))
    nivel = st.selectbox("Escolha o Nível de Dificuldade:", ["Iniciante", "Intermediário", "Especialista"])
    url_manual = st.text_input("🔗 Link Avançado (Opcional):", placeholder="Cole um link do Help Salesforce...")
    
    if st.button("🚀 Gerar Simulado Completo"):
        url_para_ler = url_manual if topico_selecionado == "Personalizado (Usar link do campo abaixo)" else LINKS_CERTIFICACAO[topico_selecionado]
        
        with st.spinner("Construindo caderno com 15 questões exclusivas..."):
            conteudo = extrair_texto_url(url_para_ler)
            st.session_state.questoes = gerar_questoes_ia(topico_selecionado, nivel, conteudo)
            st.session_state.respostas_usuario = {}
            st.session_state.corrigido = False
            st.session_state.simulado_ativo = True
            st.session_state.topico_atual = topico_selecionado
            st.session_state.nivel_atual = nivel
            st.success("Simulado pronto! Vá para a aba '🔥 Simulado'.")

# --- ABA 2: O SIMULADO ---
with aba_simulado:
    if st.session_state.get('simulado_ativo'):
        st.write(f"### 📝 Prova Ativa: {st.session_state.get('topico_atual')}")
        st.caption(f"Nível selecionado: {st.session_state.get('nivel_atual')} | Alvo para aprovação: 65%")
        st.write("---")
        
        for i, q in enumerate(st.session_state.questoes):
            st.markdown(f"##### **Questão {i+1} de {len(st.session_state.questoes)}**")
            st.write(q['pergunta'])
            
            resp = st.radio(f"Selecione a resposta para a Q{i+1}:", q['opcoes'], key=f"q_{i}", index=None, disabled=st.session_state.get('corrigido', False))
            
            if resp:
                st.session_state.respostas_usuario[i] = resp[0]

            if st.session_state.get('corrigido'):
                user_choice = st.session_state.respostas_usuario.get(i)
                if user_choice == q['correta']:
                    st.success(f"✅ Correto! Gabarito: {q['correta']}")
                else:
                    st.error(f"❌ Errado. Sua resposta: {user_choice if user_choice else 'Nenhuma'}. Resposta Certa: {q['correta']}.")
                with st.expander("💡 Ver Justificativa Técnica"):
                    st.write(q['explicacao'])
            st.markdown("---")

        if not st.session_state.get('corrigido'):
            if st.button("🏁 Finalizar e Corrigir Simulado"):
                acertos = sum(1 for i, q in enumerate(st.session_state.questoes) if st.session_state.respostas_usuario.get(i) == q['correta'])
                st.session_state.corrigido = True
                score_final = salvar_no_historico(st.session_state.topico_atual, st.session_state.nivel_atual, acertos, len(st.session_state.questoes))
                
                if score_final == 100:
                    st.balloons()
                    st.toast("🏆 INCRÍVEL! Desempenho perfeito de 100%!", icon="🔥")
                elif score_final >= 65:
                    st.balloons()
                    st.toast("🎉 Parabéns! Você atingiu a meta de aprovação de 65%!", icon="✅")
                else:
                    st.toast("Treino concluído! Revise as justificativas para melhorar no próximo.", icon="📚")
                st.rerun()
    else:
        st.info("Nenhum simulado ativo. Monte a configuração na primeira aba para iniciar!")

# --- ABA 3: PROGRESSO OTIMIZADA (MOBILE-FIRST) ---
with aba_progresso:
    st.write("### 📊 Gráficos de Evolução e Diagnóstico")
    df = carregar_dados()
    
    if not df.empty:
        df['Score_Num'] = df['Score %'].str.replace('%','').astype(int)
        
        media_geral = int(df['Score_Num'].mean())
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric(label="🎯 Sua Média Atual", value=f"{media_geral}%")
        with col_m2:
            status_aprovacao = "Aprovada 🎉" if media_geral >= 65 else "Abaixo da Meta (Focar 65%)"
            st.metric(label="🛡️ Status p/ Certificação", value=status_aprovacao)
            
        st.write("**Histórico de Rendimento por Prova:**")
        st.line_chart(df.set_index('Data')['Score_Num'], height=200)
        
        st.write("---")
        
        st.write("### 🔍 Onde você precisa focar mais?")
        medias_por_tema = df.groupby('Tema')['Score_Num'].mean().to_dict()
        
        recomendacoes_criticas = []
        recomendacoes_boas = []
        
        for tema, media in medias_por_tema.items():
            if media < 65:
                recomendacoes_criticas.append(f"🔴 **{tema}** (Média: {int(media)}%): Está abaixo dos 65% mínimos da prova. Priorize a leitura do guia oficial desse módulo!")
            else:
                recomendacoes_boas.append(f"🟢 **{tema}** (Média: {int(media)}%): Excelente! Você está mantendo a meta de aprovação.")
                
        if recomendacoes_criticas:
            st.error("⚠️ **Módulos que precisam de Atenção Urgente:**")
            for item in recomendacoes_criticas:
                st.write(item)
        else:
            st.success("🔥 Impressionante! Todos os módulos testados até agora estão dentro ou acima da média de aprovação oficial!")
            
        if recomendacoes_boas:
            st.write("**Módulos sob Controle:**")
            for item in recomendacoes_boas:
                st.write(item)

        st.write("---")
        
        st.write("**📋 Detalhes dos Testes Realizados (Estilo Mobile):**")
        for _, row in df.iloc[::-1].iterrows():
            cor_borda = "💚" if int(row['Score %'].replace('%','')) >= 65 else "❤️"
            with st.container():
                st.markdown(f"""
                {cor_borda} **{row['Tema']}**
                * **Data/Hora:** {row['Data']} | **Dificuldade:** {row['Dificuldade']}
                * **Pontuação:** {row['Acertos']} de {row['Total']} ({row['Score %']} de acertos)
                """)
                st.markdown("---")
    else:
        st.info("O histórico está vazio. Faça seu primeiro simulado para gerar os dados de evolução!")
