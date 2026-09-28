"""
avaliar_extracao.py — Parte 3: mede se a extração está certa, comparando com o gabarito feito à mão.

Rodar (na pasta parte3, depois do extrator):
    python avaliar_extracao.py

Critério de acerto (definido por mim):
Cada célula (laudo x campo) é classificada em uma de quatro categorias:
  - ACERTO:   extração igual ao gabarito, incluindo "vazio" quando o gabarito é vazio
  - CHUTE:    o gabarito é vazio (a informação não existe no laudo), mas a extração preencheu um valor.
              É o pior erro: um valor plausível inventado.
  - OMISSÃO:  o gabarito tem valor, mas a extração deixou vazio. Erro "seguro": o sistema assumiu que não sabia.
  - ERRO:     os dois têm valor, mas diferentes.

Como "igual" é decidido, por tipo de campo:
  - números (áreas, ano, valor): diferença menor que 0,01
  - matrícula: só os dígitos (184.772 = 184772)
  - ônus, data, UF: igualdade exata (sem acento/maiúscula)
  - cidade, responsável, registro: mesmas letras e números, ignorando pontuação
  - tipo, endereço, idade: um texto contém o outro ou compartilham 60%+ das palavras
  - onus_descricao e contradicoes: são textos livres, então só conta se ambos estão preenchidos ou ambos vazios
"""

import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

PASTA = Path(__file__).resolve().parent
GABARITO = PASTA / "gabarito_laudos.xlsx"
EXTRACAO = PASTA / "saida" / "extracao_laudos.csv"
SAIDA = PASTA / "saida"

NUMERICOS = ["area_privativa_m2", "area_util_m2", "area_construida_m2", "area_terreno_m2",
             "area_total_m2", "ano_construcao", "valor_avaliacao"]
EXATOS = ["onus_situacao", "data_vistoria", "uf"]
ALFANUMERICOS = ["cidade", "responsavel_tecnico", "registro_profissional"]
TEXTO_FLEXIVEL = ["tipo_imovel", "endereco", "idade_informada"]
SO_PRESENCA = ["onus_descricao", "contradicoes"]
CAMPOS = (["tipo_imovel", "endereco", "cidade", "uf"] + NUMERICOS[:5] + ["ano_construcao", "idade_informada",
          "valor_avaliacao", "matricula", "onus_situacao", "onus_descricao", "data_vistoria",
          "responsavel_tecnico", "registro_profissional", "contradicoes"])


def vazio(v):
    return v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() in ("", "nan", "None")


def simples(t):
    t = unicodedata.normalize("NFKD", str(t)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", t).strip().rstrip(".")


def alnum(t):
    return re.sub(r"[^a-z0-9]", "", simples(t))


def numero(v, campo, arquivo):
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        raise ValueError(f"Gabarito/extração com número inválido em {arquivo}, campo {campo}: '{v}'")


def iguais(campo, g, e, arquivo):
    if campo in NUMERICOS:
        return abs(numero(g, campo, arquivo) - numero(e, campo, arquivo)) < 0.01
    if campo == "matricula":
        return re.sub(r"\D", "", str(g)) == re.sub(r"\D", "", str(e))
    if campo in EXATOS:
        return simples(g) == simples(e)
    if campo in ALFANUMERICOS:
        return alnum(g) == alnum(e)
    if campo in TEXTO_FLEXIVEL:
        a, b = alnum(g), alnum(e)
        if a in b or b in a:
            return True
        pa = {p for p in re.findall(r"[a-z0-9]+", simples(g)) if len(p) > 1}
        pb = {p for p in re.findall(r"[a-z0-9]+", simples(e)) if len(p) > 1}
        return len(pa & pb) / max(len(pa | pb), 1) >= 0.6
    return True  # SO_PRESENCA: ambos preenchidos já basta


def classificar(campo, g, e, arquivo):
    if vazio(g) and vazio(e):
        return "ACERTO"
    if vazio(g):
        return "CHUTE"
    if vazio(e):
        return "OMISSÃO"
    return "ACERTO" if iguais(campo, g, e, arquivo) else "ERRO"


def main():
    for caminho in (GABARITO, EXTRACAO):
        if not caminho.exists():
            print(f"Arquivo não encontrado: {caminho}. Rode antes o extrator_laudos.py e confira o gabarito.")
            return 2
    gab = pd.read_excel(GABARITO, sheet_name="Gabarito", dtype=str).set_index("arquivo")
    ext = pd.read_csv(EXTRACAO, dtype=str, encoding="utf-8-sig").set_index("arquivo")
    faltando = set(gab.index) - set(ext.index)
    if faltando:
        print(f"Laudos no gabarito sem extração: {sorted(faltando)}")

    linhas = []
    for arquivo in gab.index.intersection(ext.index):
        for campo in CAMPOS:
            g, e = gab.at[arquivo, campo], ext.at[arquivo, campo]
            linhas.append({"arquivo": arquivo, "campo": campo,
                           "gabarito": None if vazio(g) else g, "extracao": None if vazio(e) else e,
                           "resultado": classificar(campo, g, e, arquivo)})
    det = pd.DataFrame(linhas)
    SAIDA.mkdir(exist_ok=True)
    det.to_csv(SAIDA / "avaliacao_detalhada.csv", index=False, encoding="utf-8-sig")

    total = len(det)
    cont = det["resultado"].value_counts().reindex(["ACERTO", "ERRO", "OMISSÃO", "CHUTE"], fill_value=0)
    vazios_gab = det["gabarito"].isna().sum()
    por_campo = det.pivot_table(index="campo", columns="resultado", values="arquivo",
                                aggfunc="count", fill_value=0).reindex(CAMPOS)
    for col in ["ACERTO", "ERRO", "OMISSÃO", "CHUTE"]:
        if col not in por_campo:
            por_campo[col] = 0
    por_campo["acerto_%"] = (100 * por_campo["ACERTO"] / por_campo[["ACERTO", "ERRO", "OMISSÃO", "CHUTE"]].sum(axis=1)).round(1)

    md = ["# Avaliação da extração dos laudos", "",
          f"Laudos avaliados: {det['arquivo'].nunique()} | células (laudo x campo): {total}", "",
          "| Resultado | Células | % |", "|---|---|---|"]
    for k, v in cont.items():
        md.append(f"| {k} | {v} | {100 * v / total:.1f}% |")
    md += ["", f"**Taxa de chute:** {cont['CHUTE']} de {vazios_gab} células em que a informação não existe no laudo "
           f"({100 * cont['CHUTE'] / max(vazios_gab, 1):.1f}%).", "",
           "## Por campo", "", "| Campo | Acerto % | Erros | Omissões | Chutes |", "|---|---|---|---|---|"]
    for campo, r in por_campo.iterrows():
        md.append(f"| {campo} | {r['acerto_%']:.1f}% | {int(r['ERRO'])} | {int(r['OMISSÃO'])} | {int(r['CHUTE'])} |")
    problemas = det[det["resultado"] != "ACERTO"]
    md += ["", "## Todas as divergências", ""]
    if problemas.empty:
        md.append("Nenhuma divergência.")
    else:
        md += ["| Laudo | Campo | Resultado | Gabarito | Extração |", "|---|---|---|---|---|"]
        for r in problemas.itertuples():
            gab_txt = "(vazio)" if vazio(r.gabarito) else r.gabarito
            ext_txt = "(vazio)" if vazio(r.extracao) else r.extracao
            md.append(f"| {r.arquivo} | {r.campo} | {r.resultado} | {gab_txt} | {ext_txt} |")
    (SAIDA / "relatorio_avaliacao.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(f"Acerto geral: {100 * cont['ACERTO'] / total:.1f}% | erros: {cont['ERRO']} | "
          f"omissões: {cont['OMISSÃO']} | chutes: {cont['CHUTE']}")
    print("Relatório: saida/relatorio_avaliacao.md | detalhe: saida/avaliacao_detalhada.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())