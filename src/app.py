import streamlit as st
from pathlib import Path
from utils.file_utils import handle_uploaded_files
from utils.report_generator import BIDReportGenerator
import pandas as pd
import json  # Importado para usar o json.dumps

# Configuração da página
st.set_page_config(
    page_title="TOOLS - Análise de BID",
    page_icon="🔨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS customizado para o layout da TOOLS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #009e3c 0%, #00b347 100%);
        padding: 1rem 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 2rem;
        font-weight: 700;
    }
    .main-header h3 {
        color: #f0f8f0;
        margin: 0;
        font-size: 1.1rem;
        font-weight: 400;
    }
    .ai-analysis {
        background-color: #f8f9fa;
        border-left: 4px solid #009e3c;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
    .download-buttons {
        display: flex;
        gap: 10px;
        margin: 20px 0;
    }
    .report-section {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        margin: 20px 0;
        border: 1px solid #dee2e6;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div style="margin-top: 10px; margin-bottom: 0px; text-align: center;">', unsafe_allow_html=True)
st.image("utils/Logo Verde.png", width=180)
st.markdown('<h3 style="margin-top: 0px; margin-bottom: 0px; color: #0e938e; font-weight: 600;">Agente de Suprimentos - Análise de BID</h3>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
st.markdown('<div style="margin-top: 32px;"></div>', unsafe_allow_html=True)

# Instruções do processo de análise
st.markdown("""
### 📝 Etapas do Processo de Análise

**Primeira Parte:**  
Avaliar se o mapa em Excel ou PDF está igual às propostas e se as propostas estão equalizadas.

**Segunda Etapa:**  
Avaliar se as propostas estão aderentes ao projeto.

**Terceira Etapa:**  
Montar uma base histórica com serviços já contratados para servir como referência.

**🤖 IA utilizada:**  
OpenAI GPT-4 para análise automática e inteligente dos documentos de BID.
""")

# Inicializar variáveis de sessão
if 'analysis_completed' not in st.session_state:
    st.session_state.analysis_completed = False
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None
if 'report_data' not in st.session_state:
    st.session_state.report_data = None

# Upload de arquivos

# NOVO FLUXO: Solicitação clara dos arquivos
st.markdown("""
### 📁 Importação de Documentos
Por favor, envie o mapa de concorrência (PDF ou Excel) e as propostas comerciais associadas para análise comparativa.
""")

uploaded_files = st.file_uploader(
    "Enviar arquivos de mapa e propostas",
    type=["pdf", "xlsx", "xls"],
    accept_multiple_files=True,
)

if uploaded_files:
    st.markdown("#### Arquivos carregados:")
    for file in uploaded_files:
        st.write(f"- **{file.name}** ({file.type}, {file.size/1024:.1f} KB)")

    if st.button("🔍 Solicitar Extração dos Dados", type="primary"):
        with st.spinner("🔄 Extraindo dados dos documentos..."):
            result = handle_uploaded_files(uploaded_files)
            st.session_state.analysis_result = result

            if result["success"]:
                st.success("✅ Extração concluída com sucesso!")
                st.markdown("### 📋 Validação dos Documentos:")
                for validation in result["validations"]:
                    st.markdown(f"- {validation}")

                # Exibe texto extraído dos PDFs para revisão
                st.markdown("### 📄 Texto extraído dos PDFs (pré-IA)")
                for arquivo, texto in result["structured_data"].items():
                    st.markdown(f"**{arquivo}**")
                    st.text(texto[:2000])  # Mostra os primeiros 2000 caracteres do texto extraído

                st.info("Revise os dados extraídos acima. Se estiverem legíveis e completos, clique abaixo para análise com IA.")

                # Botão para enviar para IA após revisão
                if st.button("🚀 Analisar com IA"):
                    with st.spinner("🤖 Realizando análise com IA..."):
                        # Chame a função de análise com IA aqui, usando os dados extraídos
                        # Exemplo: result_ia = analyze_with_openai_structured(result["structured_data"])
                        # Adapte conforme sua função de análise
                        result_ia = BIDReportGenerator().analyze_with_openai_structured(result["structured_data"])
                        st.session_state.analysis_result_ia = result_ia

                        if isinstance(result_ia, dict):
                            st.success("✅ Análise da IA concluída!")
                            st.markdown("### 📊 Relatório Técnico gerado pela IA (OpenAI)")
                            st.json(result_ia)
                        else:
                            st.error("❌ Erro na análise da IA")
                            st.write(result_ia)

                st.session_state.analysis_completed = True
            else:
                st.error(result["message"])
                if result["validations"]:
                    st.markdown("### ⚠️ Detalhes:")
                    for validation in result["validations"]:
                        st.markdown(f"- {validation}")

# Seção de Relatórios (só aparece após análise)

# Rodapé
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9rem;">
    <p>TOOLS Engenharia - Agente de Suprimentos com IA | Versão 2.1 | Ambiente de Produção</p>
</div>
""", unsafe_allow_html=True)
