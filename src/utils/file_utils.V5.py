import pandas as pd
import PyPDF2
import json
import openai
import os
from dotenv import load_dotenv
from pathlib import Path
import logging
import re

# Carrega variáveis de ambiente
load_dotenv()

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuração OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

def extract_text_from_pdf_complete(file):
    """Extrai TODO o texto do PDF para análise completa"""
    try:
        file.seek(0)
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    except Exception as e:
        logger.error(f"Erro ao extrair texto do PDF: {e}")
        return ""

def identify_supplier_from_filename(filename):
    """Identifica o fornecedor pelo nome do arquivo"""
    filename_lower = filename.lower()
    if "assistec" in filename_lower:
        return "ASSISTEC"
    elif "sulfrio" in filename_lower:
        return "SULFRIO"
    elif "mapa" in filename_lower:
        return "MAPA_CONCORRENCIA"
    else:
        parts = filename.split(' - ')
        if len(parts) > 0:
            potential_company = parts[0].strip().upper()
            return potential_company
        return "FORNECEDOR_NAO_IDENTIFICADO"

def extract_values_from_text(text):
    """Extrai valores monetários do texto"""
    patterns = [
        r'R\$\s*([\d\.]+,\d{2})',
        r'(\d{1,3}(?:\.\d{3})*,\d{2})',
        r'TOTAL[:\s]*([\d\.]+,\d{2})',
        r'VALOR[:\s]*([\d\.]+,\d{2})'
    ]
    values = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        values.extend(matches)
    return values

def extract_items_from_text(text):
    """Extrai itens/equipamentos do texto"""
    patterns = [
        r'UE-\d+[A-Z]?\s*-[^-\n]+',
        r'SPLIT\s+\d+[.,]?\d*\s*BTU[/H]*',
        r'CASSETE\s+\d+[.,]?\d*\s*BTU[/H]*',
        r'HI\s*WALL\s+\d+[.,]?\d*\s*BTU[/H]*',
        r'DUTO\s+\d+[.,]?\d*\s*BTU[/H]*',
        r'Suite\s*\d+',
        r'Casal',
        r'Ginastica',
        r'Home',
        r'Jantar/Copa',
        r'Escritório',
        r'Cozinha',
        r'Gourmet',
        r'FXEQ\d+AVE',
        r'FXFQ\d+AVM',
        r'FXSQ\d+PAVE',
        r'FXAQ\d+AVM',
        r'Exaustor',
    ]
    items = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        items.extend(matches)
    return list(set(items))

def validar_dados_extraidos(data):
    """Valida os dados extraídos para garantir que estão completos e consistentes."""
    if not data.get('mapa_concorrencia') or not data.get('propostas'):
        return False, "Dados incompletos ou ausentes."
    # Verifica se todos os campos obrigatórios estão presentes nas propostas
    for proposta in data.get('propostas', []):
        # Verifica se há pelo menos um valor e um item
        if not proposta.get('nome_arquivo') or not proposta.get('valores'):
            return False, f"Proposta '{proposta.get('nome_arquivo')}' inválida. Campos obrigatórios ausentes."
    return True, "Dados validados com sucesso."

def extract_structured_data_real(files):
    """Extrai dados reais e estruturados dos arquivos, com validação."""
    data = {
        "mapa_concorrencia": None,
        "propostas": []
    }
    for file in files:
        supplier = identify_supplier_from_filename(file.name)
        ext = Path(file.name).suffix.lower()
        if ext in [".xlsx", ".xls"]:
            try:
                file.seek(0)
                df = pd.read_excel(file)
                content = {
                    "tipo": "excel",
                    "dataframe": df,
                    "texto": df.to_string(),
                    "valores": extract_values_from_text(df.to_string()),
                    "itens": extract_items_from_text(df.to_string())
                }
            except Exception as e:
                logger.error(f"Erro ao processar Excel {file.name}: {e}")
                content = {"tipo": "excel", "erro": str(e)}
        else:
            full_text = extract_text_from_pdf_complete(file)
            content = {
                "tipo": "pdf",
                "texto_completo": full_text,
                "valores": extract_values_from_text(full_text),
                "itens": extract_items_from_text(full_text)
            }
        if supplier == "MAPA_CONCORRENCIA":
            data["mapa_concorrencia"] = {
                "nome_arquivo": file.name,
                "fornecedor": supplier,
                **content
            }
        else:
            data["propostas"].append({
                "nome_arquivo": file.name,
                "fornecedor": supplier,
                **content
            })
    # Validação dos dados extraídos
    validado, mensagem = validar_dados_extraidos(data)
    if not validado:
        return {"erro": True, "mensagem": mensagem}
    return data

def analyze_with_openai_real(data):
    """Análise REAL dos documentos com comparação lado a lado"""
    def limit_text(text, max_chars=2000):
        return text[:max_chars] + "..." if len(text) > max_chars else text
    prompt = f"""
ANÁLISE REAL DE PROPOSTAS - TOOLS ENGENHARIA

Você recebeu documentos REAIS de:
- MAPA: {data['mapa_concorrencia']['nome_arquivo'] if data['mapa_concorrencia'] else 'Não fornecido'}
- FORNECEDORES: {', '.join([p['fornecedor'] for p in data['propostas']])}

TAREFA: Fazer comparação LADO A LADO entre os fornecedores identificados nos documentos.

EXTRAIA dos documentos e COMPARE, item a item, trazendo:
- Quantidade
- Modelo
- Valor unitário
- Valor total
- Forma de pagamento
- Proposta
- Fornecedor
- Especificação técnica
- Para cada item, destaque o fornecedor com o menor valor (Mix de melhor preço)

Organize o relatório em formato tabular ou cards, lado a lado, para facilitar a comparação visual.

Ao final, gere um resumo do "Mix de melhor preço", indicando para cada item o fornecedor ideal e o valor, e o total do mix.

RETORNE em JSON estruturado, com todos os campos encontrados nos documentos.

DADOS DOS DOCUMENTOS REAIS:
"""
    if data['mapa_concorrencia']:
        if data['mapa_concorrencia'].get('texto_completo'):
            prompt += f"\nMAPA DE CONCORRÊNCIA:\n{limit_text(data['mapa_concorrencia']['texto_completo'])}"
        elif data['mapa_concorrencia'].get('texto'):
            prompt += f"\nMAPA DE CONCORRÊNCIA:\n{limit_text(data['mapa_concorrencia']['texto'])}"
    for proposta in data['propostas']:
        prompt += f"\n\n{proposta['fornecedor']} ({proposta['nome_arquivo']}):"
        if proposta.get('texto_completo'):
            prompt += f"\n{limit_text(proposta['texto_completo'])}"
        elif proposta.get('texto'):
            prompt += f"\n{limit_text(proposta['texto'])}"
    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "Você é um analista de suprimentos experiente. Extraia dados REAIS dos documentos fornecidos. NÃO invente valores ou informações. Analise apenas o que está escrito nos documentos. Responda APENAS com JSON válido."
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=2500,
            temperature=0.0
        )
        content = response.choices[0].message.content
        json_start = content.find('{')
        json_end = content.rfind('}') + 1
        if json_start != -1 and json_end > json_start:
            json_str = content[json_start:json_end]
            return json.loads(json_str)
        else:
            return {"erro": "GPT não retornou JSON válido", "resposta_bruta": content}
    except Exception as exc:
        logger.error(f"Erro na análise OpenAI: {exc}")
        return {"erro": f"Erro ao processar análise com IA: {str(exc)}"}

def extract_data_from_excel(file, max_rows=50):
    pass  # Função placeholder
def extract_to_dataframes(files):
    """Extrai dados dos arquivos e organiza em DataFrames estruturados separados"""
    data = {
        "mapa_concorrencia": None,
        "propostas": [],
        "dataframes": {
            "mapa_df": None,
            "propostas_dfs": []
        }
    }
    
    for file in files:
        supplier = identify_supplier_from_filename(file.name)
        ext = Path(file.name).suffix.lower()
        
        # Extrai dados básicos do arquivo
        if ext in [".xlsx", ".xls"]:
            try:
                file.seek(0)
                df_original = pd.read_excel(file)
                texto = df_original.to_string()
                
                # Cria DataFrame estruturado
                df_estruturado = criar_dataframe_estruturado(
                    df_original, supplier, file.name, "excel"
                )
                
                content = {
                    "tipo": "excel",
                    "dataframe_original": df_original,
                    "dataframe_estruturado": df_estruturado,
                    "texto": texto,
                    "valores": extract_values_from_text(texto),
                    "itens": extract_items_from_text(texto)
                }
            except Exception as e:
                logger.error(f"Erro ao processar Excel {file.name}: {e}")
                content = {"tipo": "excel", "erro": str(e)}
        else:
            # Para PDF
            full_text = extract_text_from_pdf_complete(file)
            df_estruturado = criar_dataframe_de_texto(
                full_text, supplier, file.name, "pdf"
            )
            
            content = {
                "tipo": "pdf",
                "dataframe_estruturado": df_estruturado,
                "texto_completo": full_text,
                "valores": extract_values_from_text(full_text),
                "itens": extract_items_from_text(full_text)
            }
        
        # Organiza por tipo (mapa ou proposta)
        if supplier == "MAPA_CONCORRENCIA":
            data["mapa_concorrencia"] = {
                "nome_arquivo": file.name,
                "fornecedor": supplier,
                **content
            }
            data["dataframes"]["mapa_df"] = content.get("dataframe_estruturado")
        else:
            proposta_data = {
                "nome_arquivo": file.name,
                "fornecedor": supplier,
                **content
            }
            data["propostas"].append(proposta_data)
            data["dataframes"]["propostas_dfs"].append(content.get("dataframe_estruturado"))
    
    return data

def criar_dataframe_estruturado(df_original, fornecedor, nome_arquivo, tipo_arquivo):
    """Cria um DataFrame estruturado com todas as colunas obrigatórias"""
    try:
        # Define colunas padrão obrigatórias
        colunas_obrigatorias = [
            'Nome_Proposta', 'Numero_Proposta', 'Empresa_Participante', 
            'Modelo_Produto', 'Item', 'Quantidade', 'Unidade', 
            'Custo_Unitario', 'Custo_Total', 'Status_Equalizacao'
        ]
        
        # Cria DataFrame estruturado
        dados_estruturados = []
        
        # Extrai dados do DataFrame original
        for idx, row in df_original.iterrows():
            linha_estruturada = {
                'Nome_Proposta': nome_arquivo,
                'Numero_Proposta': extrair_numero_proposta(nome_arquivo, str(row.iloc[0]) if len(row) > 0 else ""),
                'Empresa_Participante': fornecedor,
                'Modelo_Produto': extrair_modelo(row),
                'Item': extrair_item_descricao(row),
                'Quantidade': extrair_quantidade(row),
                'Unidade': extrair_unidade(row),
                'Custo_Unitario': extrair_custo_unitario(row),
                'Custo_Total': extrair_custo_total(row),
                'Status_Equalizacao': 'Pendente'
            }
            dados_estruturados.append(linha_estruturada)
        
        return pd.DataFrame(dados_estruturados)
        
    except Exception as e:
        logger.error(f"Erro ao criar DataFrame estruturado: {e}")
        # Retorna DataFrame vazio com as colunas obrigatórias
        return pd.DataFrame(columns=[
            'Nome_Proposta', 'Numero_Proposta', 'Empresa_Participante', 
            'Modelo_Produto', 'Item', 'Quantidade', 'Unidade', 
            'Custo_Unitario', 'Custo_Total', 'Status_Equalizacao'
        ])

def criar_dataframe_de_texto(texto, fornecedor, nome_arquivo, tipo_arquivo):
    """Cria DataFrame estruturado a partir de texto extraído de PDF"""
    try:
        # Divide o texto em linhas e processa cada uma
        linhas = texto.split('\n')
        dados_estruturados = []
        
        for linha in linhas:
            if linha.strip():  # Ignora linhas vazias
                linha_estruturada = {
                    'Nome_Proposta': nome_arquivo,
                    'Numero_Proposta': extrair_numero_proposta(nome_arquivo, linha),
                    'Empresa_Participante': fornecedor,
                    'Modelo_Produto': extrair_modelo_de_texto(linha),
                    'Item': extrair_item_de_texto(linha),
                    'Quantidade': extrair_quantidade_de_texto(linha),
                    'Unidade': extrair_unidade_de_texto(linha),
                    'Custo_Unitario': extrair_custo_unitario_de_texto(linha),
                    'Custo_Total': extrair_custo_total_de_texto(linha),
                    'Status_Equalizacao': 'Pendente'
                }
                dados_estruturados.append(linha_estruturada)
        
        return pd.DataFrame(dados_estruturados)
        
    except Exception as e:
        logger.error(f"Erro ao criar DataFrame de texto: {e}")
        return pd.DataFrame(columns=[
            'Nome_Proposta', 'Numero_Proposta', 'Empresa_Participante', 
            'Modelo_Produto', 'Item', 'Quantidade', 'Unidade', 
            'Custo_Unitario', 'Custo_Total', 'Status_Equalizacao'
        ])

# Funções auxiliares para extração de dados específicos
def extrair_numero_proposta(nome_arquivo, conteudo):
    """Extrai número da proposta do nome do arquivo ou conteúdo"""
    # Procura por padrões como "PROP123", "Proposta 456", números no nome do arquivo
    patterns = [r'PROP\s*(\d+)', r'Proposta\s*(\d+)', r'(\d{3,})']
    texto_busca = f"{nome_arquivo} {conteudo}"
    
    for pattern in patterns:
        match = re.search(pattern, texto_busca, re.IGNORECASE)
        if match:
            return match.group(1)
    return "N/A"

def extrair_modelo(row):
    """Extrai modelo do produto de uma linha do DataFrame"""
    try:
        row_str = str(row.to_string())
        modelos_patterns = [
            r'(FXEQ\d+[A-Z]+)', r'(FXFQ\d+[A-Z]+)', r'(FXSQ\d+[A-Z]+)',
            r'(SPLIT\s+\d+[.,]?\d*)', r'(CASSETE\s+\d+[.,]?\d*)'
        ]
        
        for pattern in modelos_patterns:
            match = re.search(pattern, row_str, re.IGNORECASE)
            if match:
                return match.group(1)
        return "N/A"
    except:
        return "N/A"

def extrair_item_descricao(row):
    """Extrai descrição do item"""
    try:
        # Procura pela coluna que contém a descrição
        for value in row:
            if pd.notna(value) and isinstance(value, str) and len(value) > 10:
                return value.strip()
        return "N/A"
    except:
        return "N/A"

def extrair_quantidade(row):
    """Extrai quantidade da linha"""
    try:
        for value in row:
            if pd.notna(value) and str(value).replace('.', '').replace(',', '').isdigit():
                return float(str(value).replace(',', '.'))
        return 1.0
    except:
        return 1.0

def extrair_unidade(row):
    """Extrai unidade de medida"""
    try:
        unidades = ['UN', 'UNID', 'PÇ', 'PC', 'PEÇA', 'M2', 'M²', 'ML', 'KG']
        row_str = str(row.to_string()).upper()
        
        for unidade in unidades:
            if unidade in row_str:
                return unidade
        return "UN"
    except:
        return "UN"

def extrair_custo_unitario(row):
    """Extrai custo unitário"""
    try:
        valores = extract_values_from_text(str(row.to_string()))
        if valores:
            return valores[0].replace('.', '').replace(',', '.')
        return "0.00"
    except:
        return "0.00"

def extrair_custo_total(row):
    """Extrai custo total"""
    try:
        valores = extract_values_from_text(str(row.to_string()))
        if len(valores) > 1:
            return valores[-1].replace('.', '').replace(',', '.')
        elif valores:
            return valores[0].replace('.', '').replace(',', '.')
        return "0.00"
    except:
        return "0.00"

# Funções equivalentes para texto (PDF)
def extrair_modelo_de_texto(linha):
    """Extrai modelo do produto de uma linha de texto"""
    modelos_patterns = [
        r'(FXEQ\d+[A-Z]+)', r'(FXFQ\d+[A-Z]+)', r'(FXSQ\d+[A-Z]+)',
        r'(SPLIT\s+\d+[.,]?\d*)', r'(CASSETE\s+\d+[.,]?\d*)'
    ]
    
    for pattern in modelos_patterns:
        match = re.search(pattern, linha, re.IGNORECASE)
        if match:
            return match.group(1)
    return "N/A"

def extrair_item_de_texto(linha):
    """Extrai descrição do item de uma linha de texto"""
    if len(linha.strip()) > 10:
        return linha.strip()[:100]  # Limita para não ficar muito longo
    return "N/A"

def extrair_quantidade_de_texto(linha):
    """Extrai quantidade de uma linha de texto"""
    try:
        numeros = re.findall(r'\b\d+[.,]?\d*\b', linha)
        if numeros:
            return float(numeros[0].replace(',', '.'))
        return 1.0
    except:
        return 1.0

def extrair_unidade_de_texto(linha):
    """Extrai unidade de uma linha de texto"""
    unidades = ['UN', 'UNID', 'PÇ', 'PC', 'PEÇA', 'M2', 'M²', 'ML', 'KG']
    linha_upper = linha.upper()
    
    for unidade in unidades:
        if unidade in linha_upper:
            return unidade
    return "UN"

def extrair_custo_unitario_de_texto(linha):
    """Extrai custo unitário de uma linha de texto"""
    valores = extract_values_from_text(linha)
    if valores:
        return valores[0].replace('.', '').replace(',', '.')
    return "0.00"

def extrair_custo_total_de_texto(linha):
    """Extrai custo total de uma linha de texto"""
    valores = extract_values_from_text(linha)
    if len(valores) > 1:
        return valores[-1].replace('.', '').replace(',', '.')
    elif valores:
        return valores[0].replace('.', '').replace(',', '.')
    return "0.00"

def extract_structured_data(files):
    """Extrai dados e organiza em DataFrames separados para mapa e propostas"""
    return extract_to_dataframes(files)

def analyze_with_openai_structured(data):
    """
    Função de análise estruturada: compara DataFrames e gera relatório técnico.
    Agora usa os DataFrames estruturados em vez de texto bruto.
    """
    try:
        # Usa os DataFrames estruturados para análise
        mapa_df = data.get("dataframes", {}).get("mapa_df")
        propostas_dfs = data.get("dataframes", {}).get("propostas_dfs", [])
        
        if mapa_df is None:
            return {
                "erro": True,
                "mensagem": "Mapa de concorrência não encontrado ou não processado corretamente."
            }
        
        # Realiza comparação usando DataFrames
        resultado_comparacao = comparar_dataframes_estruturados(mapa_df, propostas_dfs, data)
        
        return resultado_comparacao
        
    except Exception as e:
        logger.error(f"Erro na análise estruturada: {e}")
        return {
            "erro": True,
            "mensagem": f"Erro na análise: {str(e)}"
        }

def comparar_dataframes_estruturados(mapa_df, propostas_dfs, data_original):
    """Compara DataFrames estruturados e gera relatório de equalização"""
    try:
        resultado = {
            "mapa_concorrencia": {
                "nome_arquivo": data_original.get("mapa_concorrencia", {}).get("nome_arquivo", ""),
                "dataframe": mapa_df,
                "total_itens": len(mapa_df) if mapa_df is not None else 0
            },
            "propostas_analisadas": [],
            "comparacao_lado_a_lado": [],
            "mix_melhor_preco": [],
            "resumo_equalizacao": {
                "total_propostas": len(propostas_dfs),
                "itens_equalizados": 0,
                "itens_nao_equalizados": 0
            }
        }
        
        # Processa cada proposta
        for idx, proposta_df in enumerate(propostas_dfs):
            if proposta_df is not None and not proposta_df.empty:
                proposta_info = data_original["propostas"][idx] if idx < len(data_original["propostas"]) else {}
                
                # Realiza equalização item por item
                proposta_equalizada = equalizar_proposta(mapa_df, proposta_df, proposta_info)
                resultado["propostas_analisadas"].append(proposta_equalizada)
        
        # Gera comparação lado a lado
        resultado["comparacao_lado_a_lado"] = gerar_comparacao_lado_a_lado(
            resultado["mapa_concorrencia"], 
            resultado["propostas_analisadas"]
        )
        
        # Gera mix de melhor preço
        resultado["mix_melhor_preco"] = gerar_mix_melhor_preco(resultado["propostas_analisadas"])
        
        # Atualiza resumo
        for proposta in resultado["propostas_analisadas"]:
            if "dataframe_equalizado" in proposta and proposta["dataframe_equalizado"] is not None:
                equalizados = len(proposta["dataframe_equalizado"][
                    proposta["dataframe_equalizado"]["Status_Equalizacao"] == "Equalizado"
                ])
                nao_equalizados = len(proposta["dataframe_equalizado"][
                    proposta["dataframe_equalizado"]["Status_Equalizacao"] == "Não Equalizado"
                ])
                resultado["resumo_equalizacao"]["itens_equalizados"] += equalizados
                resultado["resumo_equalizacao"]["itens_nao_equalizados"] += nao_equalizados
        
        return resultado
        
    except Exception as e:
        logger.error(f"Erro na comparação de DataFrames: {e}")
        return {
            "erro": True,
            "mensagem": f"Erro na comparação: {str(e)}"
        }

def equalizar_proposta(mapa_df, proposta_df, proposta_info):
    """Equaliza uma proposta específica contra o mapa de concorrência"""
    try:
        resultado_proposta = {
            "nome_arquivo": proposta_info.get("nome_arquivo", ""),
            "fornecedor": proposta_info.get("fornecedor", ""),
            "dataframe_original": proposta_df,
            "dataframe_equalizado": proposta_df.copy(),
            "itens_equalizados": 0,
            "itens_nao_equalizados": 0,
            "observacoes": []
        }
        
        # Para cada item da proposta, verifica equalização
        for idx, item_proposta in proposta_df.iterrows():
            status_equalizacao = verificar_equalizacao_item(item_proposta, mapa_df)
            
            resultado_proposta["dataframe_equalizado"].at[idx, "Status_Equalizacao"] = status_equalizacao["status"]
            
            if status_equalizacao["status"] == "Equalizado":
                resultado_proposta["itens_equalizados"] += 1
            else:
                resultado_proposta["itens_nao_equalizados"] += 1
                resultado_proposta["observacoes"].append({
                    "item": item_proposta.get("Item", "N/A"),
                    "motivo": status_equalizacao["motivo"]
                })
        
        return resultado_proposta
        
    except Exception as e:
        logger.error(f"Erro na equalização da proposta: {e}")
        return {
            "erro": True,
            "mensagem": f"Erro: {str(e)}"
        }

def verificar_equalizacao_item(item_proposta, mapa_df):
    """Verifica se um item específico está equalizado com o mapa"""
    try:
        item_desc = str(item_proposta.get("Item", "")).lower()
        modelo_proposta = str(item_proposta.get("Modelo_Produto", "")).lower()
        
        # Procura item similar no mapa
        for idx, item_mapa in mapa_df.iterrows():
            item_mapa_desc = str(item_mapa.get("Item", "")).lower()
            modelo_mapa = str(item_mapa.get("Modelo_Produto", "")).lower()
            
            # Verifica similaridade (pode ser melhorada com algoritmos mais sofisticados)
            if (similaridade_texto(item_desc, item_mapa_desc) > 0.7 or 
                similaridade_texto(modelo_proposta, modelo_mapa) > 0.8):
                
                # Verifica critérios de equalização
                return verificar_criterios_equalizacao(item_proposta, item_mapa)
        
        return {
            "status": "Não Equalizado",
            "motivo": "Item não encontrado no mapa de concorrência"
        }
        
    except Exception as e:
        return {
            "status": "Erro",
            "motivo": f"Erro na verificação: {str(e)}"
        }

def verificar_criterios_equalizacao(item_proposta, item_mapa):
    """Verifica critérios específicos de equalização entre dois itens"""
    try:
        motivos = []
        
        # Verifica modelo
        modelo_prop = str(item_proposta.get("Modelo_Produto", "")).upper()
        modelo_mapa = str(item_mapa.get("Modelo_Produto", "")).upper()
        
        if modelo_prop != "N/A" and modelo_mapa != "N/A":
            if similaridade_texto(modelo_prop, modelo_mapa) < 0.8:
                motivos.append("Modelo diferente do especificado")
        
        # Verifica quantidade
        qtd_prop = float(str(item_proposta.get("Quantidade", 0)).replace(',', '.'))
        qtd_mapa = float(str(item_mapa.get("Quantidade", 0)).replace(',', '.'))
        
        if abs(qtd_prop - qtd_mapa) > 0.1:
            motivos.append("Quantidade divergente")
        
        # Verifica unidade
        unid_prop = str(item_proposta.get("Unidade", "")).upper()
        unid_mapa = str(item_mapa.get("Unidade", "")).upper()
        
        if unid_prop != unid_mapa and unid_prop != "N/A" and unid_mapa != "N/A":
            motivos.append("Unidade de medida diferente")
        
        if motivos:
            return {
                "status": "Não Equalizado",
                "motivo": "; ".join(motivos)
            }
        else:
            return {
                "status": "Equalizado",
                "motivo": "Atende às especificações do mapa"
            }
            
    except Exception as e:
        return {
            "status": "Erro",
            "motivo": f"Erro na verificação de critérios: {str(e)}"
        }

def similaridade_texto(texto1, texto2):
    """Calcula similaridade entre dois textos (0.0 a 1.0)"""
    try:
        from difflib import SequenceMatcher
        return SequenceMatcher(None, texto1, texto2).ratio()
    except:
        return 0.0

def gerar_comparacao_lado_a_lado(mapa_info, propostas_analisadas):
    """Gera comparação visual lado a lado das propostas"""
    try:
        comparacao = {
            "colunas": ["Item", "Mapa", "Propostas", "Status", "Melhor_Preco"],
            "dados": []
        }
        
        mapa_df = mapa_info.get("dataframe")
        if mapa_df is None or mapa_df.empty:
            return comparacao
        
        # Para cada item do mapa, compara com todas as propostas
        for idx_mapa, item_mapa in mapa_df.iterrows():
            linha_comparacao = {
                "item_mapa": item_mapa.get("Item", "N/A"),
                "modelo_mapa": item_mapa.get("Modelo_Produto", "N/A"),
                "custo_mapa": item_mapa.get("Custo_Total", "0.00"),
                "propostas_comparacao": []
            }
            
            melhor_preco = float('inf')
            melhor_fornecedor = ""
            
            # Compara com cada proposta
            for proposta in propostas_analisadas:
                if "dataframe_equalizado" in proposta and proposta["dataframe_equalizado"] is not None:
                    df_prop = proposta["dataframe_equalizado"]
                    
                    # Procura item equivalente na proposta
                    for idx_prop, item_prop in df_prop.iterrows():
                        if (similaridade_texto(
                            str(item_mapa.get("Item", "")).lower(),
                            str(item_prop.get("Item", "")).lower()
                        ) > 0.7):
                            
                            custo_prop = float(str(item_prop.get("Custo_Total", "0")).replace(',', '.'))
                            
                            linha_comparacao["propostas_comparacao"].append({
                                "fornecedor": proposta.get("fornecedor", "N/A"),
                                "modelo": item_prop.get("Modelo_Produto", "N/A"),
                                "custo": custo_prop,
                                "status": item_prop.get("Status_Equalizacao", "Pendente")
                            })
                            
                            if custo_prop < melhor_preco:
                                melhor_preco = custo_prop
                                melhor_fornecedor = proposta.get("fornecedor", "N/A")
            
            linha_comparacao["melhor_preco"] = melhor_preco if melhor_preco != float('inf') else 0
            linha_comparacao["melhor_fornecedor"] = melhor_fornecedor
            
            comparacao["dados"].append(linha_comparacao)
        
        return comparacao
        
    except Exception as e:
        logger.error(f"Erro na comparação lado a lado: {e}")
        return {"erro": str(e)}

def gerar_mix_melhor_preco(propostas_analisadas):
    """Gera o mix de melhor preço considerando todas as propostas"""
    try:
        mix = {
            "itens": [],
            "total": 0.0,
            "economia": 0.0
        }
        
        # Agrupa todos os itens por categoria/descrição similar
        itens_agrupados = {}
        
        for proposta in propostas_analisadas:
            if "dataframe_equalizado" in proposta and proposta["dataframe_equalizado"] is not None:
                df_prop = proposta["dataframe_equalizado"]
                
                for idx, item in df_prop.iterrows():
                    if item.get("Status_Equalizacao") == "Equalizado":
                        item_key = str(item.get("Item", "")).lower()
                        custo = float(str(item.get("Custo_Total", "0")).replace(',', '.'))
                        
                        if item_key not in itens_agrupados:
                            itens_agrupados[item_key] = []
                        
                        itens_agrupados[item_key].append({
                            "fornecedor": proposta.get("fornecedor", "N/A"),
                            "custo": custo,
                            "item_completo": item
                        })
        
        # Seleciona melhor preço para cada item
        for item_key, opcoes in itens_agrupados.items():
            if opcoes:
                melhor_opcao = min(opcoes, key=lambda x: x["custo"])
                mix["itens"].append({
                    "item": item_key.title(),
                    "fornecedor_selecionado": melhor_opcao["fornecedor"],
                    "custo": melhor_opcao["custo"],
                    "detalhes": melhor_opcao["item_completo"]
                })
                mix["total"] += melhor_opcao["custo"]
        
        return mix
        
    except Exception as e:
        logger.error(f"Erro na geração do mix de melhor preço: {e}")
        return {"erro": str(e)}

# Função global para importação
def comparar_propostas(mapa, propostas):

    """Compara propostas, gera estrutura para relatório colorido, painel horizontal e mix de melhor preço"""
    import difflib
    import pandas as pd
    if not mapa or not mapa.get("itens"):
        return [{
            "erro": True,
            "mensagem": "Por favor inserir o mapa de concorrência para realizar a análise comparativa."
        }]
    itens_mapa = mapa.get("itens", [])
    resultado = []
    painel = []
    mix = []
    def normaliza(texto):
        return re.sub(r"\s+", "", texto).lower()

    fornecedores_lista = [p.get("fornecedor", p.get("nome_arquivo", "Proposta")) for p in propostas]

    for item_nome in itens_mapa:
        fornecedores = {}
        linha_painel = {"item": item_nome}
        item_norm = normaliza(item_nome)
        valores_item = []
        for proposta in propostas:
            nome_forn = proposta.get("fornecedor", proposta.get("nome_arquivo", "Proposta"))
            valores = proposta.get("valores", [])
            itens = proposta.get("itens", [])
            valor = None
            melhor_score = 0
            melhor_idx = None
            for idx, item_prop in enumerate(itens):
                item_prop_norm = normaliza(item_prop)
                score = difflib.SequenceMatcher(None, item_norm, item_prop_norm).ratio()
                if item_norm in item_prop_norm or score > 0.7:
                    if score > melhor_score:
                        melhor_score = score
                        melhor_idx = idx
            if melhor_idx is not None and melhor_idx < len(valores):
                try:
                    valor_str = valores[melhor_idx]
                    valor = float(str(valor_str).replace(".","").replace(",","."))
                except:
                    valor = valor_str
            fornecedores[nome_forn] = {"valor": valor if valor is not None else "-", "especificacao": item_nome}
            linha_painel[nome_forn] = valor if valor is not None else "-"
            valores_item.append(valor if valor is not None else float('inf'))
        valores_validos = [(f, d["valor"]) for f, d in fornecedores.items() if isinstance(d["valor"], (int, float))]
        melhor = min(valores_validos, key=lambda x: x[1])[0] if valores_validos else None
        pior = max(valores_validos, key=lambda x: x[1])[0] if valores_validos else None
        diferenca = None
        recomendacao = ""
        if melhor and pior:
            diferenca = fornecedores[pior]["valor"] - fornecedores[melhor]["valor"]
            if diferenca > 0:
                if diferenca > 1000:
                    recomendacao = f"Grande diferença de preço entre fornecedores. Recomenda-se negociar com {melhor} para o item '{item_nome}' devido ao melhor preço."
                else:
                    recomendacao = f"{melhor} apresenta o melhor preço para o item '{item_nome}'. Recomenda-se priorizar este fornecedor."
            else:
                recomendacao = f"Os preços estão próximos entre os fornecedores para o item '{item_nome}'. Avalie outros critérios além do preço."
        else:
            recomendacao = f"Não foi possível comparar preços para o item '{item_nome}'. Verifique se os dados extraídos estão completos."
        resultado.append({
            "item": item_nome,
            "quantidade": "-",
            "fornecedores": fornecedores,
            "melhor_preco": melhor,
            "diferenca_valores": diferenca,
            "recomendacao": recomendacao
        })
        # Painel horizontal
        linha_painel["melhor_preco"] = melhor
        linha_painel["pior_preco"] = pior
        painel.append(linha_painel)
        # Mix de melhor preço
        if melhor:
            melhor_valor = fornecedores[melhor]["valor"]
            mix.append({"item": item_nome, "melhor_fornecedor": melhor, "melhor_valor": melhor_valor})
        else:
            mix.append({"item": item_nome, "melhor_fornecedor": None, "melhor_valor": None})
    # Retorna resultado detalhado, painel horizontal e mix
    return {
        "resultado": resultado,
        "painel": painel,
        "mix_melhor_preco": mix
    }
