import pandas as pd
import streamlit as st
from pathlib import Path

def validate_file_type(file):
    """Valida tipo de arquivo"""
    allowed = ['.pdf', '.xlsx', '.xls']
    return Path(file.name).suffix.lower() in allowed

def handle_uploaded_files(files):
    """Processa arquivos enviados"""
    if not files:
        return {"success": False}
ECHO est† desativado.
    validations = []
    for file in files:
        if validate_file_type(file):
            validations.append(f"‚úÖ {file.name} validado")
        else:
            validations.append(f"‚ùå {file.name} inv√°lido")
ECHO est† desativado.
    return {
        "success": True,
        "validations": validations
    }
