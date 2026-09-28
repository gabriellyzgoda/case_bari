"""
testes_parte2.py — Simula arquivos de entrada problemáticos e confere o comportamento da automação.

Rodar:  python testes_parte2.py
Cada cenário cria um arquivo alterado a partir da base original numa pasta temporária,
roda o relatório e confere o código de saída (0 = ok, 1 = formato falhou, 2 = problema no arquivo).
"""

import logging
import shutil
import tempfile
from pathlib import Path

import pandas as pd

from relatorio_semanal import main

ORIGINAL = Path(__file__).resolve().parent.parent / "dados" / "propostas_credito.csv"


def preparar(pasta, nome, alterar=None, **kwargs_csv):
    """Cria uma cópia modificada da base. `alterar` recebe o DataFrame e devolve a versão alterada."""
    df = pd.read_csv(ORIGINAL, dtype=str, encoding="utf-8-sig")
    if alterar:
        df = alterar(df)
    caminho = pasta / nome
    if caminho.suffix == ".xlsx":
        df.to_excel(caminho, index=False)
    else:
        df.to_csv(caminho, index=False, **kwargs_csv)
    return caminho


def cenarios(pasta):
    """(descrição, caminho do arquivo, código de saída esperado)"""
    vazio = pasta / "vazio.csv"
    vazio.write_text("")
    so_cabecalho = pasta / "so_cabecalho.csv"
    so_cabecalho.write_text(ORIGINAL.read_text(encoding="utf-8-sig").splitlines()[0])
    return [
        ("Arquivo original", ORIGINAL, 0),
        ("Sem coluna obrigatória (status_final)",
         preparar(pasta, "sem_status.csv", lambda d: d.drop(columns="status_final")), 2),
        ("Sem coluna opcional (renda_mensal_declarada)",
         preparar(pasta, "sem_renda.csv", lambda d: d.drop(columns="renda_mensal_declarada")), 0),
        ("Coluna nova inesperada",
         preparar(pasta, "coluna_nova.csv", lambda d: d.assign(observacao="x")), 0),
        ("Nomes de coluna com maiúsculas e espaços",
         preparar(pasta, "colunas_maiusculas.csv", lambda d: d.rename(columns=lambda c: f" {c.upper()} ")), 0),
        ("Separador ';' (padrão do Excel brasileiro)",
         preparar(pasta, "ponto_virgula.csv", sep=";"), 0),
        ("Encoding latin-1", preparar(pasta, "latin1.csv", encoding="latin-1"), 0),
        ("Arquivo Excel (.xlsx) em vez de CSV", preparar(pasta, "base.xlsx"), 0),
        ("Arquivo vazio", vazio, 2),
        ("Só cabeçalho, sem linhas", so_cabecalho, 2),
        ("Arquivo inexistente", pasta / "nao_existe.csv", 2),
    ]


if __name__ == "__main__":
    pasta = Path(tempfile.mkdtemp(prefix="testes_bari_"))
    resultados = []
    try:
        for descricao, caminho, esperado in cenarios(pasta):
            codigo = main(["--entrada", str(caminho), "--saida", str(pasta / "saida"),
                           "--logs", str(pasta / "logs"), "--formatos", "html"])
            resultados.append((descricao, esperado, codigo))
    finally:
        logging.getLogger().handlers.clear()
        shutil.rmtree(pasta, ignore_errors=True)

    print("\n" + "=" * 78)
    print(f"{'Cenário':<48}{'Esperado':>10}{'Obtido':>9}   Resultado")
    print("-" * 78)
    for descricao, esperado, codigo in resultados:
        print(f"{descricao:<48}{esperado:>10}{codigo:>9}   {'OK' if esperado == codigo else 'FALHOU'}")
    falhas = sum(e != c for _, e, c in resultados)
    print("-" * 78)
    print(f"{len(resultados) - falhas}/{len(resultados)} cenários com o comportamento esperado")