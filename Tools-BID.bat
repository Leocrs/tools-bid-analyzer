@echo off
echo 🚀 Criando estrutura TOOLS BID Analyzer...

cd /d "C:\Users\Leonardo\Projetos"

echo 📁 Criando diretórios...
mkdir tools-bid-analyzer
cd tools-bid-analyzer
mkdir src\utils
mkdir src\assets

echo 📝 Criando arquivos...

:: Criando app.py
(
echo import streamlit as st
echo import os
echo from pathlib import Path
echo from utils.file_utils import handle_uploaded_files, validate_file_type
echo.
echo # Configuração da página
echo st.set_page_config^(
echo     page_title="TOOLS - Análise de BID",
echo     page_icon="🔨",
echo     layout="wide",
echo     initial_sidebar_state="collapsed"
echo ^)
echo.
echo # CSS customizado para o layout da TOOLS
echo st.markdown^("""
echo ^<style^>
echo     .main-header {
echo         background: linear-gradient^(90deg, #009e3c 0%%, #00b347 100%%^);
echo         padding: 1rem 2rem;
echo         border-radius: 10px;
echo         margin-bottom: 2rem;
echo         box-shadow: 0 4px 6px rgba^(0, 0, 0, 0.1^);
echo     }
echo     .main-header h1 {
echo         color: white;
echo         margin: 0;
echo         font-size: 2rem;
echo         font-weight: 700;
echo     }
echo ^</style^>
echo """, unsafe_allow_html=True^)
echo.
echo # Header principal
echo st.markdown^("""
echo ^<div class="main-header"^>
echo     ^<h1^>🔨 TOOLS Engenharia^</h1^>
echo     ^<h3^>Agente de Suprimentos - Análise de BID^</h3^>
echo ^</div^>
echo """, unsafe_allow_html=True^)
echo.
echo # Upload de arquivos
echo uploaded_files = st.file_uploader^(
echo     "Envie o mapa de concorrência:",
echo     type=["pdf", "xlsx", "xls"],
echo     accept_multiple_files=True
echo ^)
echo.
echo if uploaded_files:
echo     if st.button^("🔍 Solicitar Análise"^):
echo         result = handle_uploaded_files^(uploaded_files^)
echo         st.success^("Análise iniciada!"^)
) > src\app.py

:: Criando file_utils.py
(
echo import pandas as pd
echo import streamlit as st
echo from pathlib import Path
echo.
echo def validate_file_type^(file^):
echo     """Valida tipo de arquivo"""
echo     allowed = ['.pdf', '.xlsx', '.xls']
echo     return Path^(file.name^).suffix.lower^(^) in allowed
echo.
echo def handle_uploaded_files^(files^):
echo     """Processa arquivos enviados"""
echo     if not files:
echo         return {"success": False}
echo     
echo     validations = []
echo     for file in files:
echo         if validate_file_type^(file^):
echo             validations.append^(f"✅ {file.name} validado"^)
echo         else:
echo             validations.append^(f"❌ {file.name} inválido"^)
echo     
echo     return {
echo         "success": True,
echo         "validations": validations
echo     }
) > src\utils\file_utils.py

:: Criando requirements.txt
(
echo streamlit==1.29.0
echo pandas==2.1.4
echo openpyxl==3.1.2
echo pathlib
) > requirements.txt

:: Criando README.md
(
echo # TOOLS BID Analyzer
echo.
echo Aplicação Streamlit para análise de BID da TOOLS Engenharia.
echo.
echo ## Instalação
echo ```bash
echo pip install -r requirements.txt
echo streamlit run src/app.py
echo ```
) > README.md

:: Criando .gitignore
(
echo __pycache__/
echo *.pyc
echo .env
echo .DS_Store
echo uploads/
echo .streamlit/
) > .gitignore

echo 🔧 Inicializando Git...
git init
git add .
git commit -m "feat: estrutura inicial TOOLS BID Analyzer"

echo 🌐 Criando repositório no GitHub...
gh repo create tools-bid-analyzer --public --source=. --remote=origin --push

echo ✅ Projeto criado e enviado para o GitHub!
echo 📂 Abrindo no VS Code...
code .

cd Tools-Bid-Analyzer
.\Tools-BID.bat

pause