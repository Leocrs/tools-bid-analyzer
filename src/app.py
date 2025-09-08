import streamlit as st
import os
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
</style>
""", unsafe_allow_html=True^)

# Header principal
st.markdown("""
<div class="main-header">
    <h1>🔨 TOOLS Engenharia</h1>
    <h3>Agente de Suprimentos - Análise de BID</h3>
</div>
""", unsafe_allow_html=True^)

# Upload de arquivos
uploaded_files = st.file_uploader(
    "Envie o mapa de concorrência:",
    type=["pdf", "xlsx", "xls"],
    accept_multiple_files=True
)

if uploaded_files:
    if st.button("🔍 Solicitar Análise"):
        result = handle_uploaded_files(uploaded_files)
        st.success("Análise iniciada!")
