import pandas as pd
import streamlit as st
from pathlib import Path
import logging
import openai
import os
from dotenv import load_dotenv
import PyPDF2
from io import BytesIO

# Carrega variáveis de ambiente
load_dotenv()

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuração OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

def validate_file_type(file):
    """Valida o tipo de arquivo enviado"""
    allowed_extensions = ['.pdf', '.xlsx', '.xls', '.docx']
    file_extension = Path(file.name).suffix.lower()
    return file_extension in allowed_extensions

def extract_text_from_pdf(file):
    """Extrai texto de arquivo PDF"""
    try:
        file.seek(0)
        reader = PyPDF2.PdfReader(BytesIO(file.getvalue()))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        logger.error(f"Erro ao extrair texto do PDF: {e}")
        return ""

def extract_text_from_excel(file):
    """Extrai dados de arquivo Excel em formato texto"""
    try:
        file.seek(0)
        df = pd.read_excel(file)
        # Converte DataFrame para texto estruturado
        text = f"Arquivo Excel com {len(df)} linhas e {len(df.columns)} colunas:\n\n"
        text += f"Colunas: {', '.join(df.columns)}\n\n"
        text += df.to_string(index=False)
        return text
    except Exception as e:
        logger.error(f"Erro ao extrair dados do Excel: {e}")
        return ""

def analyze_with_openai(documents_text, file_types):
    """Analisa documentos usando OpenAI GPT"""
    try:
        # Prompt específico para análise de BID
        system_prompt = """
        Você é um agente de suprimentos da Tools Engenharia especializado em análise de BID.

        ⚠️ NÃO DEVE iniciar nenhuma análise automaticamente.

        📌 Seu trabalho é seguir estas etapas:

        **Primeira Parte:**
        - Avaliar se o mapa em Excel está igual às propostas
        - Verificar se as propostas estão equalizadas

        **Segunda Etapa:**
        - Avaliar se as propostas estão aderentes ao projeto
        - Identificar inconsistências ou omissões

        **Terceira Etapa:**
        - Montar uma base histórica com serviços já contratados para servir como referência
        - Comparar com dados históricos quando disponível

        🔎 Para cada análise:
        1. Confirme que o mapa foi recebido
        2. Valide se contém:
           • Itens e quantidades
           • Empresas participantes
           • Valores unitários
        3. Compare valores unitários entre fornecedores
        4. Identifique o menor preço por item
        5. Avalie viabilidade de contratação por mix ou fornecedor único
        6. Aponte inconsistências ou omissões

        ✅ Sua linguagem deve ser técnica e objetiva
        ❌ Nunca assuma dados não fornecidos
        """

        user_content = f"""
        Documentos recebidos para análise:
        Tipos de arquivo: {', '.join(file_types)}

        Conteúdo dos documentos:
        {documents_text}

        Por favor, realize a análise completa seguindo as três etapas definidas.
        """

        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            max_tokens=1500,
            temperature=0.3
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Erro na análise OpenAI: {e}")
        return f"❌ Erro ao processar análise com IA: {str(e)}"

def analyze_excel_content(file):
    """Analisa conteúdo de arquivo Excel para identificar mapa de concorrência"""
    try:
        df = pd.read_excel(file)
        
        # Verifica se parece com um mapa de concorrência
        columns = df.columns.str.lower()
        
        # Palavras-chave que indicam mapa de concorrência
        keywords = ['item', 'descrição', 'quantidade', 'preço', 'valor', 'fornecedor', 'empresa']
        found_keywords = [kw for kw in keywords if any(kw in col for col in columns)]
        
        validations = []
        
        if len(found_keywords) >= 3:
            validations.append("✅ Estrutura de mapa de concorrência identificada")
            validations.append(f"✅ Colunas relevantes encontradas: {', '.join(found_keywords)}")
            validations.append(f"✅ Total de itens/linhas: {len(df)}")
            
            # Verifica se há dados numéricos (valores)
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                validations.append(f"✅ Colunas com valores numéricos: {len(numeric_cols)}")
            else:
                validations.append("⚠️ Poucas colunas numéricas identificadas")
                
            return True, validations
        else:
            validations.append("⚠️ Estrutura de mapa de concorrência não clara")
            validations.append(f"⚠️ Apenas {len(found_keywords)} palavras-chave encontradas")
            return False, validations
            
    except Exception as e:
        logger.error(f"Erro ao analisar Excel: {e}")
        return False, [f"❌ Erro ao processar arquivo Excel: {str(e)}"]

def analyze_pdf_content(file):
    """Analisa conteúdo de arquivo PDF"""
    try:
        text = extract_text_from_pdf(file)
        file_size = len(file.getvalue())
        
        if file_size > 0 and text:
            return True, [
                "✅ Arquivo PDF recebido e processado",
                f"✅ Tamanho: {file_size/1024:.1f} KB",
                f"✅ Texto extraído: {len(text)} caracteres",
                "✅ Pronto para análise com IA"
            ]
        else:
            return False, ["❌ Arquivo PDF está vazio ou não foi possível extrair texto"]
    except Exception as e:
        logger.error(f"Erro ao analisar PDF: {e}")
        return False, [f"❌ Erro ao processar arquivo PDF: {str(e)}"]

def handle_uploaded_files(files):
    """Processa e valida arquivos enviados pelo usuário"""
    if not files:
        return {
            "success": False,
            "message": "Nenhum arquivo enviado",
            "validations": [],
            "ai_analysis": ""
        }
    
    all_validations = []
    has_map = False
    has_proposals = False
    documents_text = ""
    file_types = []
    
    for file in files:
        file_name = file.name.lower()
        file_extension = Path(file.name).suffix.lower()
        file_types.append(f"{file.name} ({file_extension})")
        
        # Reset file pointer
        file.seek(0)
        
        if not validate_file_type(file):
            all_validations.append(f"❌ {file.name}: Tipo de arquivo não suportado")
            continue
        
        all_validations.append(f"📁 Analisando: {file.name}")
        
        # Extração de texto para análise IA
        if file_extension in ['.xlsx', '.xls']:
            text_content = extract_text_from_excel(file)
            is_valid, validations = analyze_excel_content(file)
            all_validations.extend(validations)
            
            # Verifica se é um mapa de concorrência
            if 'mapa' in file_name or 'concorrencia' in file_name or is_valid:
                has_map = True
                all_validations.append("🎯 Identificado como: MAPA DE CONCORRÊNCIA")
            else:
                has_proposals = True
                all_validations.append("📋 Identificado como: PROPOSTA/DOCUMENTO AUXILIAR")
                
        elif file_extension == '.pdf':
            text_content = extract_text_from_pdf(file)
            is_valid, validations = analyze_pdf_content(file)
            all_validations.extend(validations)
            
            if 'mapa' in file_name or 'concorrencia' in file_name:
                has_map = True
                all_validations.append("🎯 Identificado como: MAPA DE CONCORRÊNCIA")
            else:
                has_proposals = True
                all_validations.append("📋 Identificado como: PROPOSTA/DOCUMENTO TÉCNICO")
        
        # Adiciona conteúdo extraído para análise IA
        if text_content:
            documents_text += f"\n\n=== {file.name} ===\n{text_content}\n"
        
        all_validations.append("---")
    
    # Análise com IA
    ai_analysis = ""
    if documents_text and openai.api_key:
        all_validations.append("🤖 Iniciando análise com IA...")
        ai_analysis = analyze_with_openai(documents_text, file_types)
    elif not openai.api_key:
        ai_analysis = "⚠️ Chave da OpenAI não configurada. Adicione sua chave no arquivo .env"
    
    # Validação final
    if not has_map:
        return {
            "success": False,
            "message": "⚠️ MAPA DE CONCORRÊNCIA não identificado. Por favor, envie um arquivo contendo o mapa de concorrência com itens, quantidades e valores.",
            "validations": all_validations,
            "ai_analysis": ai_analysis
        }
    
    # Sucesso na validação
    success_message = "✅ Documentos validados com sucesso!"
    if has_proposals:
        success_message += " Mapa de concorrência e propostas/documentos auxiliares identificados."
    else:
        success_message += " Mapa de concorrência identificado. Você pode enviar propostas comerciais adicionais para análise comparativa."
    
    return {
        "success": True,
        "message": success_message,
        "validations": all_validations,
        "has_map": has_map,
        "has_proposals": has_proposals,
        "ai_analysis": ai_analysis
    }
