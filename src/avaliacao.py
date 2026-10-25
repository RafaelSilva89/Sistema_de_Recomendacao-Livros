"""Ficha do modelo (JSON) com o que é preciso saber para usar o recomendador corretamente."""
import json
from datetime import datetime


def salvar_ficha_modelo(caminho, **campos):
    """Grava a ficha do modelo (JSON): tudo o que é preciso saber para usá-lo corretamente."""
    ficha = {'data_treino': datetime.now().strftime('%Y-%m-%d %H:%M'), **campos}
    with open(caminho, 'w', encoding='utf-8') as arquivo:
        json.dump(ficha, arquivo, ensure_ascii=False, indent=2, default=float)
    return ficha
