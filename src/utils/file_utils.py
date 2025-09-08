import pandas as pd
import streamlit as st
from pathlib import Path
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_file_type(file):
    """Valida o tipo de arquivo enviado"""
    allowed_extensions = ['.pdf', '.xlsx', '.xls', '.docx']
    file_extension = Path(file.name).suffix.lower()
    return file_extension in allowed_extensions

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
    """Analisa conteúdo de arquivo PDF (placeholder)"""
    try:
        file_size = len(file.getvalue())
        if file_size > 0:
            return True, [
                "✅ Arquivo PDF recebido",
                f"✅ Tamanho: {file_size/1024:.1f} KB",
                "ℹ️ Análise detalhada de PDF será implementada com OCR/extração de texto"
            ]
        else:
            return False, ["❌ Arquivo PDF está vazio"]
    except Exception as e:
        logger.error(f"Erro ao analisar PDF: {e}")
        return False, [f"❌ Erro ao processar arquivo PDF: {str(e)}"]

def handle_uploaded_files(files):
    """Processa e valida arquivos enviados pelo usuário"""
    if not files:
        return {
            "success": False,
            "message": "Nenhum arquivo enviado",
            "validations": []
        }
    
    all_validations = []
    has_map = False
    has_proposals = False
    
    for file in files:
        file_name = file.name.lower()
        file_extension = Path(file.name).suffix.lower()
        
        # Reset file pointer
        file.seek(0)
        
        if not validate_file_type(file):
            all_validations.append(f"❌ {file.name}: Tipo de arquivo não suportado")
            continue
        
        all_validations.append(f"📁 Analisando: {file.name}")
        
        # Análise baseada no tipo de arquivo
        if file_extension in ['.xlsx', '.xls']:
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
            is_valid, validations = analyze_pdf_content(file)
            all_validations.extend(validations)
            
            if 'mapa' in file_name or 'concorrencia' in file_name:
                has_map = True
                all_validations.append("🎯 Identificado como: MAPA DE CONCORRÊNCIA")
            else:
                has_proposals = True
                all_validations.append("📋 Identificado como: PROPOSTA/DOCUMENTO TÉCNICO")
        
        all_validations.append("---")
    
    # Validação final
    if not has_map:
        return {
            "success": False,
            "message": "⚠️ MAPA DE CONCORRÊNCIA não identificado. Por favor, envie um arquivo contendo o mapa de concorrência com itens, quantidades e valores.",
            "validations": all_validations
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
        "has_proposals": has_proposals
    }
