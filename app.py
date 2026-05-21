import streamlit as st
import pandas as pd
from openai import OpenAI
import json
import os
from datetime import datetime
import zoneinfo
import re

# ─────────────────────────────────────────────
# 1. CONFIGURAÇÃO DA PÁGINA
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="SF Admin Simulator",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─────────────────────────────────────────────
# 2. CSS GLOBAL — INSPIRADO NO TRAILHEAD
#    Tokens adaptativos: nunca usa cor fixa em texto.
#    Funciona em Light e Dark Mode do Streamlit.
# ─────────────────────────────────────────────
st.markdown("""
<style>
/* ── PALETA TRAILHEAD ───────────────────────────── */
:root {
    --sf-blue:         #00A1E0;
    --sf-blue-dark:    #0070D2;
    --sf-navy:         #032D60;
    --sf-orange:       #FF6B35;
    --sf-green:        #2E7D32;
    --sf-yellow:       #F4C430;

    /* Tokens adaptativos — herdam do tema Streamlit */
    --bg-card:         rgba(0, 161, 224, 0.07);
    --border-subtle:   rgba(0, 161, 224, 0.22);
    --border-left-q:   #00A1E0;
}

/* ── HEADER ─────────────────────────────────────── */
.sf-header {
    background: linear-gradient(135deg, #00A1E0 0%, #0070D2 55%, #032D60 100%);
    border-radius: 14px;
    padding: 22px 28px;
    margin-bottom: 22px;
    display: flex;
    align-items: center;
    gap: 16px;
    box-shadow: 0 6px 24px rgba(0, 112, 210, 0.30);
}
.sf-header-icon  { font-size: 38px; line-height: 1; }
.sf-header-title { font-size: 22px; font-weight: 800; color: #FFFFFF; margin: 0; letter-spacing: -0.3px; }
.sf-header-sub   { font-size: 13px; color: rgba(255,255,255,0.72); margin: 3px 0 0 0; }

/* ── TABS ────────────────────────────────────────── */
div[data-testid="stTabs"] > div:first-child {
    gap: 4px;
    border-bottom: 2px solid var(--border-subtle);
}
div[data-testid="stTabs"] button {
    border-radius: 8px 8px 0 0 !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    padding: 8px 20px !important;
    border: none !important;
    transition: background 0.18s, color 0.18s;
}
div[data-testid="stTabs"] button[aria-selected="true"] {
    background: var(--sf-blue) !important;
    color: #FFFFFF !important;
    box-shadow: 0 -3px 10px rgba(0,161,224,0.28);
}

/* ── CARD DE QUESTÃO ─────────────────────────────── */
.questao-card {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-left: 4px solid var(--sf-blue);
    border-radius: 10px;
    padding: 18px 20px;
    margin-bottom: 6px;
}
.questao-numero {
    font-size: 11px;
    font-weight: 700;
    color: var(--sf-blue);
    text-transform: uppercase;
    letter-spacing: 1.2px;
    margin-bottom: 6px;
}
.questao-texto {
    font-size: 15px;
    font-weight: 500;
    line-height: 1.55;
    color: inherit;        /* herda do tema — não quebra dark/light */
}

/* ── FEEDBACK DE RESPOSTA ────────────────────────── */
/* CERTO — verde com borda, fundo translúcido */
.feedback-certo {
    background: rgba(46, 125, 50, 0.12);
    border: 1px solid rgba(46, 125, 50, 0.35);
    border-left: 4px solid #2E7D32;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 14px;
    font-weight: 600;
    color: inherit;        /* adapta ao dark/light */
    margin: 6px 0 4px 0;
}
/* ERRADO — neutro com borda laranja, sem vermelho */
.feedback-errado {
    background: rgba(128, 128, 128, 0.09);
    border: 1px solid rgba(128, 128, 128, 0.22);
    border-left: 4px solid var(--sf-orange);
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 14px;
    color: inherit;        /* adapta ao dark/light */
    margin: 6px 0 4px 0;
}

/* ── BADGES DE DESEMPENHO ────────────────────────── */
.badge {
    display: inline-block;
    padding: 4px 13px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.3px;
}
/* Laranja — fundo sólido escuro o suficiente para branco legível */
.badge-alta   { background: var(--sf-orange); color: #FFFFFF; }
/* Amarelo — fundo claro, usa texto escuro fixo (contraste garantido) */
.badge-ajuste { background: var(--sf-yellow); color: #1a1a1a; }
/* Azul Trailhead — texto branco sempre legível */
.badge-meta   { background: var(--sf-blue);   color: #FFFFFF; }
/* Verde escuro — texto branco sempre legível */
.badge-top    { background: var(--sf-green);   color: #FFFFFF; }

/* ── KPI BOX ─────────────────────────────────────── */
.kpi-box {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 14px;
    padding: 24px 20px;
    text-align: center;
}
.kpi-valor {
    font-size: 48px;
    font-weight: 900;
    color: var(--sf-blue);
    line-height: 1;
}
.kpi-label {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.9px;
    color: inherit;
    opacity: 0.55;
    margin-top: 5px;
}
.kpi-status {
    font-size: 14px;
    font-weight: 700;
    margin-top: 10px;
    color: inherit;
}

/* ── TABELA DE PROGRESSO ─────────────────────────── */
.sf-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0 5px;
    margin-top: 10px;
}
.sf-table th {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--sf-blue);
    padding: 6px 14px;
    border-bottom: 2px solid var(--border-subtle);
    background: transparent;
}
.sf-table td {
    padding: 12px 14px;
    font-size: 14px;
    background: var(--bg-card);
    color: inherit;        /* adapta ao dark/light */
    border-top: 1px solid var(--border-subtle);
    border-bottom: 1px solid var(--border-subtle);
}
.sf-table td:first-child {
    border-left: 3px solid var(--sf-blue);
    border-radius: 8px 0 0 8px;
}
.sf-table td:last-child {
    border-right: 1px solid var(--border-subtle);
    border-radius: 0 8px 8px 0;
    text-align: right;
}

/* ── GRADE DE REVISÃO ────────────────────────────── */
.grade-container { display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0 4px 0; }
.grade-item {
    width: 38px; height: 38px;
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 14px; color: #FFFFFF;
    transition: transform 0.15s;
}
.grade-item:hover { transform: scale(1.08); }
.grade-ok    { background: var(--sf-green); }
.grade-vazio { background: #757575; }

/* ── BOTÕES ──────────────────────────────────────── */
div[data-testid="stButton"] > button {
    border-radius: 8px !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    transition: filter 0.18s, transform 0.1s !important;
}
div[data-testid="stButton"] > button:hover {
    filter: brightness(1.08) !important;
    transform: translateY(-1px) !important;
}

/* ── DIVIDER PERSONALIZADO ───────────────────────── */
.sf-divider {
    height: 1px;
    background: var(--border-subtle);
    margin: 18px 0;
    border: none;
}

/* ── MOBILE ──────────────────────────────────────── */
@media (max-width: 640px) {
    .sf-header { padding: 14px 16px; gap: 12px; }
    .sf-header-title { font-size: 17px; }
    .sf-header-icon  { font-size: 28px; }
    .questao-texto   { font-size: 14px; }
    .kpi-valor       { font-size: 36px; }
    div[data-testid="stTabs"] button {
        padding: 6px 12px !important;
        font-size: 12px !important;
    }
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# 3. AUTENTICAÇÃO — OpenAI (sem alteração)
# ─────────────────────────────────────────────
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


# ─────────────────────────────────────────────
# 4. SESSION STATE SEGURO
# ─────────────────────────────────────────────
if "simulado_ativo" not in st.session_state:
    st.session_state.clear()
    st.session_state.simulado_ativo      = False
    st.session_state.corrigido           = False
    st.session_state.respostas_usuario   = {}
    st.session_state.questoes            = []
    st.session_state.confirmou_salvamento = False


# ─────────────────────────────────────────────
# 5. MÓDULOS DO EXAME CRT-101
#    Pesos oficiais do Exam Guide Salesforce.
#    Subtópicos guiam o GPT para gerar questões
#    alinhadas ao que realmente cai na prova.
# ─────────────────────────────────────────────
MODULOS_ADMIN = {
    "Configuração e Objetos": {
        "peso": 20,
        "subtopicos": [
            "custom objects e custom fields",
            "page layouts e compact layouts",
            "record types",
            "apps e AppExchange",
            "global picklists",
        ],
    },
    "Segurança e Acesso": {
        "peso": 15,
        "subtopicos": [
            "profiles e permission sets",
            "roles e role hierarchy",
            "OWD (Organization-Wide Defaults)",
            "sharing rules e manual sharing",
            "field-level security",
        ],
    },
    "Automação de Processos/Flow": {
        "peso": 16,
        "subtopicos": [
            "Flow Builder (screen flow, record-triggered flow)",
            "approval processes",
            "validation rules",
            "formula fields",
            "flow best practices e quando usar cada automação",
        ],
    },
    "Relatórios e Dashboards": {
        "peso": 13,
        "subtopicos": [
            "tipos de relatório (tabular, summary, matrix, joined)",
            "report filters e cross-filters",
            "componentes de dashboard",
            "subscriptions e agendamento",
            "folders e compartilhamento de relatórios",
        ],
    },
    "Guia Geral do Administrador": {
        "peso": 36,
        "subtopicos": [
            "data management (import wizard, data loader)",
            "change sets e sandbox",
            "Chatter e collaboration",
            "mobile e Salesforce app",
            "service cloud basics (cases, queues, escalation rules)",
            "sales cloud basics (leads, opportunities, forecasting)",
            "duplicate management",
        ],
    },
}


# ─────────────────────────────────────────────
# 6. FUNÇÕES — sem alteração de lógica
# ─────────────────────────────────────────────
def carregar_dados():
    arquivo = "historico_simulados.csv"
    if os.path.exists(arquivo):
        return pd.read_csv(arquivo)
    return pd.DataFrame(columns=["Data", "Tema", "Dificuldade", "Acertos", "Total", "Score %"])


def salvar_no_historico(tema, difficulty, pontos, total):
    arquivo = "historico_simulados.csv"
    fuso_brasil = zoneinfo.ZoneInfo("America/Sao_Paulo")
    data_atual = datetime.now(fuso_brasil).strftime("%d/%m/%Y %H:%M")
    score = int((pontos / total) * 100)
    novo_registro = pd.DataFrame(
        [[data_atual, tema, difficulty, pontos, total, f"{score}%"]],
        columns=["Data", "Tema", "Dificuldade", "Acertos", "Total", "Score %"],
    )
    df_atual = carregar_dados()
    df_final = pd.concat([df_atual, novo_registro], ignore_index=True)
    df_final.to_csv(arquivo, index=False)
    return score


def carregar_banco_questoes(tema: str) -> list:
    """Carrega questões do banco local (questions.json) filtrando pelo tema."""
    arquivo = "questions.json"
    if not os.path.exists(arquivo):
        return []
    with open(arquivo, "r", encoding="utf-8") as f:
        banco = json.load(f)
    # Filtra por tema (comparação flexível, case-insensitive)
    return [q for q in banco if tema.lower() in q.get("tema", "").lower()]


def gerar_questoes_ia(tema: str, nivel: str) -> list:
    """
    Gera questões via GPT-4o-mini com dois aprimoramentos:
    1. Usa os pesos e subtópicos oficiais do CRT-101 para direcionar a geração.
    2. Injeta exemplos do banco local (questions.json) como referência de estilo.
    """
    modulo = MODULOS_ADMIN[tema]
    peso = modulo["peso"]
    subtopicos_str = "\n".join(f"  - {s}" for s in modulo["subtopicos"])

    # Monta contexto do banco local se houver questões cadastradas
    exemplos_banco = carregar_banco_questoes(tema)
    contexto_banco = ""
    if exemplos_banco:
        exemplos_str = "\n".join(
            f'  Pergunta: {q["pergunta"]}\n  Resposta correta: {q["correta"]}'
            for q in exemplos_banco[:3]  # máximo 3 exemplos para não sobrecarregar o prompt
        )
        contexto_banco = f"""
Banco de questões de referência (use como inspiração de estilo e profundidade, NÃO repita estas perguntas):
{exemplos_str}
"""

    prompt = f"""
Você é um examinador oficial da Salesforce para a certificação Certified Administrator (CRT-101).

Módulo: {tema}
Peso real no exame oficial: {peso}% das questões da prova
Nível de dificuldade exigido: {nivel}

Subtópicos prioritários deste módulo (cubra o máximo possível de subtópicos diferentes):
{subtopicos_str}
{contexto_banco}
Instruções:
- Gere exatamente 10 perguntas de múltipla escolha INÉDITAS e ALEATÓRIAS.
- Varie os cenários de negócio (empresas diferentes, setores diferentes, tamanhos de org diferentes).
- Cada questão deve cobrir um subtópico diferente — não repita o mesmo conceito.
- Nível {nivel}: {"foque em conceitos básicos e definições" if nivel == "Iniciante" else "use cenários práticos com decisões de configuração" if nivel == "Intermediário" else "use cenários complexos com múltiplas restrições e decisões de arquitetura"}.
- A resposta correta deve ser apenas a letra (A, B, C ou D).

Responda EXCLUSIVAMENTE no formato JSON abaixo:
{{
  "perguntas": [
    {{
      "pergunta": "Texto do cenário ou questão",
      "opcoes": ["A) Opção 1", "B) Opção 2", "C) Opção 3", "D) Opção 4"],
      "correta": "A",
      "explicacao": "Justificativa técnica baseada nas regras da Salesforce.",
      "subtopico": "nome do subtópico coberto"
    }}
  ]
}}
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "Você é um examinador Salesforce sênior. "
                    "Gere sempre questões originais, práticas e alinhadas ao exame real CRT-101. "
                    "Responda somente com JSON válido, sem texto adicional."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.9,
    )
    dados = json.loads(response.choices[0].message.content)
    return dados.get("perguntas", [])[:10]


# ─────────────────────────────────────────────
# 7. HEADER GLOBAL
# ─────────────────────────────────────────────
st.markdown("""
<div class="sf-header">
    <div class="sf-header-icon">⚡</div>
    <div>
        <p class="sf-header-title">Salesforce Admin Simulator</p>
        <p class="sf-header-sub">Prepare-se para a certificação CRT-101 com questões geradas por IA</p>
    </div>
</div>
""", unsafe_allow_html=True)

aba_config, aba_simulado, aba_progresso = st.tabs(
    ["⚙️  Configurar", "🔥  Simulado", "📊  Meu Progresso"]
)


# ─────────────────────────────────────────────
# ABA 1 — CONFIGURAÇÃO
# ─────────────────────────────────────────────
with aba_config:
    st.markdown("#### Escolha o Módulo e a Dificuldade")

    col_a, col_b = st.columns([2, 1])
    with col_a:
        topico_selecionado = st.selectbox(
            "Módulo do Exame CRT-101:",
            list(MODULOS_ADMIN.keys()),
            help="Cada módulo cobre uma área específica da certificação Salesforce Admin.",
        )
    with col_b:
        nivel = st.selectbox(
            "Nível de Dificuldade:",
            ["Iniciante", "Intermediário", "Especialista"],
        )

    # ── CARD DO MÓDULO: PESO E SUBTÓPICOS ──
    modulo_info  = MODULOS_ADMIN[topico_selecionado]
    peso_modulo  = modulo_info["peso"]
    subtopicos_html = "".join(
        f"<span style='display:inline-block; background:var(--bg-card); "
        f"border:1px solid var(--border-subtle); border-radius:20px; "
        f"padding:3px 10px; font-size:12px; margin:3px 4px 3px 0; color:inherit;'>{s}</span>"
        for s in modulo_info["subtopicos"]
    )
    st.markdown(
        f"""
        <div style='background:var(--bg-card); border:1px solid var(--border-subtle);
                    border-left:4px solid var(--sf-blue); border-radius:10px;
                    padding:16px 20px; margin:12px 0 10px 0;'>
            <div style='display:flex; align-items:center; gap:12px; margin-bottom:12px;'>
                <span style='font-size:12px; font-weight:700; color:var(--sf-blue);
                             text-transform:uppercase; letter-spacing:1px;'>
                    Peso no exame oficial
                </span>
                <span style='font-size:24px; font-weight:900; color:var(--sf-blue);'>{peso_modulo}%</span>
                <div style='flex:1; background:rgba(0,161,224,0.15); border-radius:4px; height:8px;'>
                    <div style='width:{peso_modulo}%; background:var(--sf-blue);
                                border-radius:4px; height:8px; transition:width 0.4s;'></div>
                </div>
            </div>
            <div style='font-size:11px; font-weight:700; opacity:0.55;
                        text-transform:uppercase; letter-spacing:0.8px; margin-bottom:8px;'>
                Subtópicos cobertos pela IA
            </div>
            <div>{subtopicos_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── INDICADOR DO BANCO LOCAL ──
    banco_do_tema = carregar_banco_questoes(topico_selecionado)
    if banco_do_tema:
        st.markdown(
            f"<div style='font-size:13px; opacity:0.70; margin-bottom:6px;'>"
            f"📚 Banco local: <b>{len(banco_do_tema)} questão(ões)</b> de referência encontradas "
            f"— a IA usará como exemplo de estilo.</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div style='font-size:13px; opacity:0.55; margin-bottom:6px;'>"
            "📂 Nenhuma questão local para este módulo ainda. "
            "Adicione em <code>questions.json</code> para enriquecer a geração.</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div class='sf-divider'></div>", unsafe_allow_html=True)

    if st.button("🚀  Gerar Simulado Completo", use_container_width=True, type="primary"):
        with st.spinner(f"Gerando 10 questões de '{topico_selecionado}' alinhadas ao CRT-101…"):
            st.session_state.respostas_usuario    = {}
            st.session_state.corrigido            = False
            st.session_state.confirmou_salvamento = False
            st.session_state.questoes             = gerar_questoes_ia(topico_selecionado, nivel)
            st.session_state.topico_atual         = topico_selecionado
            st.session_state.nivel_atual          = nivel
            st.session_state.simulado_ativo       = True
        st.success("✅  Simulado pronto! Acesse a aba **🔥 Simulado** para começar.")


# ─────────────────────────────────────────────
# ABA 2 — SIMULADO
# ─────────────────────────────────────────────
with aba_simulado:
    if st.session_state.get("simulado_ativo") and st.session_state.get("questoes"):
        topico = st.session_state.get("topico_atual", "")
        nivel_ativo = st.session_state.get("nivel_atual", "")

        col_h1, col_h2 = st.columns([3, 1])
        col_h1.markdown(f"### 📝 {topico}")
        col_h2.markdown(
            f"<div style='text-align:right; padding-top:6px; font-size:13px; opacity:0.7;'>"
            f"Nível: <b>{nivel_ativo}</b> &nbsp;|&nbsp; Meta: <b>65%</b></div>",
            unsafe_allow_html=True,
        )
        st.markdown("<div class='sf-divider'></div>", unsafe_allow_html=True)

        for i, q in enumerate(st.session_state.questoes):
            # Card visual da questão
            st.markdown(
                f"""<div class="questao-card">
                    <div class="questao-numero">Questão {i+1} de {len(st.session_state.questoes)}</div>
                    <div class="questao-texto">{q['pergunta']}</div>
                </div>""",
                unsafe_allow_html=True,
            )

            resp = st.radio(
                "Selecione sua resposta:",
                q["opcoes"],
                key=f"q_{i}",
                index=None,
                disabled=st.session_state.get("corrigido", False),
                label_visibility="collapsed",
            )

            if resp:
                st.session_state.respostas_usuario[i] = resp[0]

            if st.session_state.get("corrigido"):
                user_choice = st.session_state.respostas_usuario.get(i)
                if user_choice == q["correta"]:
                    st.markdown(
                        f"<div class='feedback-certo'>✅ Correto! &nbsp; Gabarito: <b>{q['correta']}</b></div>",
                        unsafe_allow_html=True,
                    )
                else:
                    resposta_dada = user_choice if user_choice else "Nenhuma"
                    st.markdown(
                        f"<div class='feedback-errado'>❌ Incorreto &nbsp;|&nbsp; "
                        f"Sua resposta: <b>{resposta_dada}</b> &nbsp;|&nbsp; "
                        f"Correta: <b>{q['correta']}</b></div>",
                        unsafe_allow_html=True,
                    )
                with st.expander("💡 Ver Justificativa Técnica"):
                    st.write(q["explicacao"])

            st.markdown("<div class='sf-divider'></div>", unsafe_allow_html=True)

        # ── BOTÃO FINALIZAR ──
        if not st.session_state.get("corrigido") and not st.session_state.get("confirmou_salvamento"):
            if st.button("🏁  Finalizar e Corrigir Simulado", use_container_width=True, type="primary"):
                total_questoes = len(st.session_state.questoes)

                if len(st.session_state.respostas_usuario) < total_questoes:
                    st.warning("⚠️ Você ainda tem questões sem resposta. Confira abaixo:")

                    grade_html = "<div class='grade-container'>"
                    for idx in range(total_questoes):
                        css = "grade-ok" if idx in st.session_state.respostas_usuario else "grade-vazio"
                        grade_html += f"<div class='grade-item {css}'>{idx + 1}</div>"
                    grade_html += "</div>"
                    st.markdown(grade_html, unsafe_allow_html=True)

                    st.markdown(
                        "<div style='font-size:12px; opacity:0.65;'>"
                        "<span style='background:#2E7D32; color:#fff; padding:2px 8px; border-radius:4px;'>Verde</span>"
                        " Respondida &nbsp;&nbsp;"
                        "<span style='background:#757575; color:#fff; padding:2px 8px; border-radius:4px;'>Cinza</span>"
                        " Em branco</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.session_state.confirmou_salvamento = True
                    st.rerun()

        # ── CONFIRMAÇÃO DE SALVAMENTO ──
        if st.session_state.get("confirmou_salvamento"):
            st.markdown("#### 💾 Deseja salvar este resultado no histórico?")
            col_btn1, col_btn2 = st.columns(2)

            if col_btn1.button("✅  Sim, Salvar e Corrigir", use_container_width=True, type="primary"):
                acertos = sum(
                    1
                    for i, q in enumerate(st.session_state.questoes)
                    if st.session_state.respostas_usuario.get(i) == q["correta"]
                )
                salvar_no_historico(
                    st.session_state.topico_atual,
                    st.session_state.nivel_atual,
                    acertos,
                    len(st.session_state.questoes),
                )
                st.session_state.corrigido = True
                st.session_state.confirmou_salvamento = False
                st.rerun()

            if col_btn2.button("❌  Não, Só Corrigir", use_container_width=True):
                st.session_state.corrigido = True
                st.session_state.confirmou_salvamento = False
                st.rerun()

    else:
        st.info("Nenhum simulado ativo. Configure e gere um na aba **⚙️ Configurar**.")


# ─────────────────────────────────────────────
# ABA 3 — PROGRESSO
# ─────────────────────────────────────────────
with aba_progresso:
    df = carregar_dados()

    if not df.empty:
        # Limpeza de dados
        df["Tema"] = df["Tema"].apply(lambda x: re.sub(r"\s*\(\d+%\)\s*", "", str(x)).strip())
        df["Score_Num"] = df["Score %"].astype(str).str.replace("%", "").astype(int)

        media_geral = int(df["Score_Num"].mean())
        aprovado = media_geral >= 65

        # ── KPI ──
        status_text  = "✅ Aprovado" if aprovado else "⚠️ Abaixo da Meta (65%)"
        status_color = "var(--sf-green)" if aprovado else "var(--sf-orange)"
        total_provas = len(df)

        col_k1, col_k2, col_k3 = st.columns(3)

        with col_k1:
            st.markdown(
                f"""<div class='kpi-box'>
                    <div class='kpi-valor'>{media_geral}%</div>
                    <div class='kpi-label'>Média Geral</div>
                    <div class='kpi-status' style='color:{status_color};'>{status_text}</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with col_k2:
            st.markdown(
                f"""<div class='kpi-box'>
                    <div class='kpi-valor'>{total_provas}</div>
                    <div class='kpi-label'>Simulados Realizados</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with col_k3:
            melhor = int(df["Score_Num"].max())
            st.markdown(
                f"""<div class='kpi-box'>
                    <div class='kpi-valor'>{melhor}%</div>
                    <div class='kpi-label'>Melhor Score</div>
                </div>""",
                unsafe_allow_html=True,
            )

        st.markdown("<div class='sf-divider'></div>", unsafe_allow_html=True)
        st.markdown(
            "<span style='font-size:15px; font-weight:700; color:var(--sf-blue);'>"
            "📋 Diagnóstico por Módulo</span>",
            unsafe_allow_html=True,
        )

        # ── TABELA DE DESEMPENHO ──
        df_mod = df.groupby("Tema").agg({"Acertos": "sum", "Total": "sum"}).reset_index()
        df_mod.columns = ["Módulo", "Acertos", "Total"]
        df_mod["Pct"] = ((df_mod["Acertos"] / df_mod["Total"]) * 100).astype(int)
        df_mod = df_mod.sort_values("Pct", ascending=True)

        def badge(pct):
            if pct < 50:
                return "<span class='badge badge-alta'>Prioridade Alta</span>"
            elif pct < 65:
                return "<span class='badge badge-ajuste'>Ajustes Finais</span>"
            elif pct < 80:
                return "<span class='badge badge-meta'>Meta Atingida</span>"
            return "<span class='badge badge-top'>Excelente ⭐</span>"

        rows = ""
        for _, row in df_mod.iterrows():
            # Busca o peso oficial do módulo (se existir no dicionário)
            peso_oficial = MODULOS_ADMIN.get(row["Módulo"], {}).get("peso", "—")
            peso_str = f"{peso_oficial}%" if isinstance(peso_oficial, int) else peso_oficial
            rows += (
                f"<tr>"
                f"<td>{row['Módulo']}</td>"
                f"<td style='text-align:center; font-weight:700; opacity:0.6;'>{peso_str}</td>"
                f"<td style='text-align:center; font-weight:700; color:var(--sf-blue);'>{row['Pct']}%</td>"
                f"<td>{badge(row['Pct'])}</td>"
                f"</tr>"
            )

        tabela_html = f"""
        <table class='sf-table'>
            <thead>
                <tr>
                    <th>Módulo</th>
                    <th style='text-align:center;'>Peso no Exame</th>
                    <th style='text-align:center;'>Seu Rendimento</th>
                    <th style='text-align:right;'>Status</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
        """
        st.markdown(tabela_html, unsafe_allow_html=True)

        st.markdown("<div class='sf-divider'></div>", unsafe_allow_html=True)

        # ── HISTÓRICO DETALHADO ──
        with st.expander("📅 Ver Histórico Completo de Simulados"):
            df_exib = df[["Data", "Tema", "Dificuldade", "Acertos", "Total", "Score %"]].copy()
            df_exib = df_exib.sort_index(ascending=False).reset_index(drop=True)
            st.dataframe(df_exib, use_container_width=True, hide_index=True)

    else:
        st.info("O histórico está vazio. Faça um simulado para ativar o painel de progresso!")
