import streamlit as st
import pandas as pd
from openai import OpenAI
import json
import os
from datetime import datetime
import zoneinfo

# 1. Configuração da Página
st.set_page_config(page_title="Simulado - Salesforce Administrator", page_icon="🛡️", layout="wide")

# 2. Autenticação Segura
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- REQUISITOS DA PROVA SALESFORCE ADMIN (CRT-101) ---
MODULOS_ADMIN = [
    "Configuração e Objetos (20%)",
    "Segurança e Acesso (14%)",
    "Automação de Processos/Flow (16%)",
    "Relatórios e Dashboards (10%)",
    "Guia Geral do Administrador"
]

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
    novo_registro = pd.DataFrame([[data_atual, tema, dificuldade, pontos, total, f"{score}%"]], 
                                columns=['Data', 'Tema', 'Dificuldade', 'Acertos', 'Total', 'Score %'])
    df_atual = carregar_dados()
    df_final = pd.concat([df_atual, novo_registro], ignore_index=True)
    df_final.to_csv(arquivo, index=False)
    return score

def gerar_questoes_ia(tema, nivel):
    prompt = f"""
    Gere exatamente 15 perguntas de múltipla escolha sobre o módulo de Salesforce: {tema}, focado no nível {nivel}.
    Os cenários devem ser práticos, realistas e alinhados com a prova oficial de certificação Salesforce Certified Administrator (CRT-101).
    Responda EXCLUSIVAMENTE em formato JSON estruturado:
    {{
      "perguntas": [
        {{
          "pergunta": "Texto completo do cenário ou questão", 
          "opcoes": ["A) Opção 1", "B) Opção 2", "C) Opção 3", "D) Opção 4"], 
          "correta": "A",
          "explicacao": "Explicação detalhada do porquê esta alternativa está correta conforme as boas práticas da Salesforce."
        }}
      ]
    }}
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini", 
        messages=[{"role": "system", "content": "Você é um instrutor e avaliador sênior especialista em certificações Salesforce."},
                  {"role": "user", "content": prompt}],
        response_format={ "type": "json_object" }
    )
    dados = json.loads(response.choices[0].message.content)
    return dados.get('perguntas', [])[:15]

# --- DESIGN PRINCIPAL ---
st.markdown('<h2 style="font-size: 24px; margin-bottom: 15px;">🎓 Simulado - Salesforce Administrator</h2>', unsafe_allow_html=True)

aba_config, aba_simulado, aba_progresso = st.tabs(["⚙️ Configurar", "🔥 Simulado", "📊 Meu Progresso"])

# --- ABA 1: CONFIGURAÇÃO ---
with aba_config:
    topico_selecionado = st.selectbox("Escolha o Tópico do Exame:", MODULOS_ADMIN)
    nivel = st.selectbox("Escolha o Nível de Dificuldade:", ["Iniciante", "Intermediário", "Especialista"])
    
    if st.button("🚀 Gerar Simulado Completo"):
        with st.spinner("Construindo caderno com 15 questões exclusivas..."):
            st.session_state.questoes = gerar_questoes_ia(topico_selecionado, nivel)
            st.session_state.respostas_usuario = {}
            st.session_state.corrigido = False
            st.session_state.simulado_ativo = True
            st.session_state.topico_atual = topico_selecionado
            st.session_state.nivel_atual = nivel
            st.success("Simulado pronto! Vá para a aba '🔥 Simulado'.")

# --- ABA 2: O SIMULADO ---
with aba_simulado:
    if st.session_state.get('simulado_ativo'):
        st.markdown(f"### 📝 Desafio Iniciado: {st.session_state.get('topico_atual')}")
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
                    st.success("🏆 INCRÍVEL! Parabéns, você gabaritou com 100% de aproveitamento!")
                elif score_final >= 65:
                    st.balloons()
                    st.info("🎉 Você foi muito bem até aqui, mas pode melhorar ainda mais!")
                else:
                    st.warning("Treino concluído! Revise as justificativas técnicas para alcançar os 65% na próxima tentativa.")
                st.rerun()
    else:
        st.info("Nenhum simulado ativo. Monte a configuração na primeira aba para iniciar!")

# --- ABA 3: PROGRESSO OTIMIZADA ---
with aba_progresso:
    df = carregar_dados()
    
    if not df.empty:
        df['Score_Num'] = df['Score %'].str.replace('%','').astype(int)
        
        # Resumo de Status Principal
        media_geral = int(df['Score_Num'].mean())
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric(label="🎯 Sua Média Geral", value=f"{media_geral}%")
        with col_m2:
            status_aprovacao = "Aprovada 🎉" if media_geral >= 65 else "Abaixo da Meta (Focar 65%)"
            st.metric(label="🛡️ Previsão p/ Certificação", value=status_aprovacao)
            
        st.write("---")
        
        # --- TABELA 1: SCORE POR MÓDULO ---
        st.write("### 🏷️ Desempenho Médio por Módulo:")
        df_modulos = df.groupby('Tema')['Score_Num'].mean().reset_index()
        df_modulos.columns = ['Módulo Acadêmico', 'Média de Acertos (%)']
        df_modulos['Média de Acertos (%)'] = df_modulos['Média de Acertos (%)'].round(1).astype(str) + '%'
        st.dataframe(df_modulos, use_container_width=True, hide_index=True)
        
        st.write("---")
        
        # --- SEÇÃO CRÍTICA (FOCAR MAIS) ---
        st.write("### 🔍 Módulos que precisam de Atenção Urgente:")
        medias_por_tema = df.groupby('Tema')['Score_Num'].mean().to_dict()
        
        recomendacoes_criticas = []
        
        for tema, media in medias_por_tema.items():
            if media < 65:
                recomendacoes_criticas.append(f"🔴 **{tema}** (Média Atual: {int(media)}%): Está abaixo do mínimo exigido. Revise os conceitos fundamentais.")
                
        if recomendacoes_criticas:
            for item in recomendacoes_criticas:
                st.write(item)
        else:
            st.success("🔥 Ótimo sinal! Nenhum dos módulos testados está abaixo da linha crítica de corte.")

        st.write("---")
        
        # --- TABELA 2: HISTÓRICO DE SIMULADOS COMPACTO ---
        st.write("### 📋 Detalhes dos Testes Realizados:")
        
        df_visual = df.copy()
        df_visual['Status'] = df_visual['Score_Num'].apply(lambda x: "💚 Aprovado" if x >= 65 else "❤️ Revisar")
        df_visual = df_visual[['Data', 'Tema', 'Dificuldade', 'Score %', 'Status']]
        df_visual.columns = ['Data/Hora', 'Módulo Concluído', 'Dificuldade', 'Aproveitamento', 'Resultado']
        
        st.dataframe(df_visual.iloc[::-1], use_container_width=True, hide_index=True)
        
    else:
        st.info("O histórico de evolução está vazio. Finalize o seu primeiro teste para alimentar o painel!")
