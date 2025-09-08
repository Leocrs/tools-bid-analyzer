import streamlit as st
from pathlib import Path
from utils.file_utils import handle_uploaded_files, validate_file_type

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
</style>
""", unsafe_allow_html=True)

# Header principal
st.markdown("""
<div class="main-header">
    <h1>🔨 TOOLS Engenharia</h1>
    <h3>Agente de Suprimentos - Análise de BID</h3>
</div>
""", unsafe_allow_html=True)

# Instruções do processo de análise
st.markdown("""
### 📝 Etapas do Processo de Análise

**Primeira Parte:**  
Avaliar se o mapa em Excel está igual às propostas e se as propostas estão equalizadas.

**Segunda Etapa:**  
Avaliar se as propostas estão aderentes ao projeto.

**Terceira Etapa:**  
Montar uma base histórica com serviços já contratados para servir como referência.

---
**🤖 IA utilizada:**  
OpenAI GPT-4 para análise automática e inteligente dos documentos de BID.
""")

# Upload de arquivos
st.markdown("### 📁 Importar Documentos")
uploaded_files = st.file_uploader(
    "Arraste e solte os arquivos aqui ou clique para selecionar (PDF ou Excel):",
    type=["pdf", "xlsx", "xls"],
    accept_multiple_files=True
)

if uploaded_files:
    if st.button("🔍 Solicitar Análise com IA", type="primary"):
        with st.spinner("🤖 Processando documentos e realizando análise com IA..."):
            result = handle_uploaded_files(uploaded_files)
            
            if result["success"]:
                st.success("✅ Análise concluída com sucesso!")
                
                # Exibe validações
                st.markdown("### 📋 Validação dos Documentos:")
                for validation in result["validations"]:
                    st.markdown(f"- {validation}")
                
                # Exibe análise da IA
                if result["ai_analysis"]:
                    st.markdown("### 🤖 Análise Inteligente:")
                    st.markdown(f'<div class="ai-analysis">{result["ai_analysis"]}</div>', unsafe_allow_html=True)
                    
            else:
                st.error(result["message"])
                if result["validations"]:
                    st.markdown("### ⚠️ Detalhes:")
                    for validation in result["validations"]:
                        st.markdown(f"- {validation}")

# Rodapé
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9rem;">
    <p>TOOLS Engenharia - Agente de Suprimentos com IA | Versão 2.0 | Ambiente de Produção</p>
</div>
""", unsafe_allow_html=True)
