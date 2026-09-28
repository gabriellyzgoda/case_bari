"""
analise_parte1.py — Diagnóstico do funil (Parte 1)

Rodar:  python analise_parte1.py
Pré-requisito: tratamento.py e dados/propostas_credito.csv na pasta principal.
Também atualiza o registro_tratamento.md desta pasta.
"""

import logging
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency
# tratamento.py fica na pasta principal, porque é compartilhado com a Parte 2
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tratamento import ARQUIVO_PADRAO, REGISTRO_MD, ETAPAS, carregar_e_tratar, salvar_registro_md  # noqa: E402

pd.set_option("display.width", 200)


def pergunta1_perda_por_etapa(df):
    """Onde o funil perde mais valor: por etapa, em quantidade, em R$ e ponderado."""
    n_total = len(df)
    linhas = []
    for k, nome in ETAPAS.items():
        if k == 6:
            continue  # etapa 6 = contratação, não há perda
        chegaram = df[df["etapa_max_funil"] >= k]
        perdidas = df[(df["etapa_max_funil"] == k) & ~df["contratada"]]
        p_conv = chegaram["contratada"].mean()  # chance de contratar de quem chega nesta etapa
        rs_perdido = perdidas["valor_solicitado"].sum()
        linhas.append({
            "etapa": f"{k}. {nome}",
            "chegaram": len(chegaram),
            "perdidas": len(perdidas),
            "% do total": round(100 * len(perdidas) / n_total, 1),
            "R$ perdido (mi)": round(rs_perdido / 1e6, 1),
            "P(contratar) ao chegar": round(p_conv, 3),
            # R$ perdido x chance que essas propostas tinham de virar contrato
            "R$ ponderado (mi)": round(rs_perdido * p_conv / 1e6, 1),
        })
    return pd.DataFrame(linhas)


def pergunta1_perda_por_motivo(df):
    """R$ perdido por motivo (status_final) e etapa."""
    perdidas = df[~df["contratada"]]
    tabela = perdidas.pivot_table(index="status_final", columns="etapa_max_funil",
                                  values="valor_solicitado", aggfunc="sum", fill_value=0) / 1e6
    tabela["Total (mi)"] = tabela.sum(axis=1)
    return tabela.round(1).sort_values("Total (mi)", ascending=False)


def teste_proporcoes(a, b):
    """Teste z para diferença entre duas taxas de conversão (a e b são séries True/False).
    |z| > 1,96 => diferença estatisticamente significativa com 95% de confiança."""
    p_a, p_b = a.mean(), b.mean()
    p = pd.concat([a, b]).mean()
    erro = np.sqrt(p * (1 - p) * (1 / len(a) + 1 / len(b)))
    return p_a, p_b, (p_a - p_b) / erro


def pergunta2_conversao_no_tempo(df):
    """Conversão por trimestre de entrada, com intervalo de confiança de 95%."""
    df = df.assign(trimestre=df["data_entrada"].dt.to_period("Q").astype(str))
    t = df.groupby("trimestre").agg(propostas=("contratada", "size"),
                                    contratadas=("contratada", "sum"))
    t["conversao_%"] = 100 * t["contratadas"] / t["propostas"]
    p = t["contratadas"] / t["propostas"]
    t["margem_ic95_pp"] = 100 * 1.96 * np.sqrt(p * (1 - p) / t["propostas"])
    t["% correspondente"] = 100 * df.groupby("trimestre")["canal_origem"].apply(
        lambda s: (s == "Correspondente").mean())
    return t.round(1)


def pergunta2_correspondentes(df):
    """Correspondente x outros canais: conversão bruta, por faixa de score e de LTV,
    e taxa de passagem entre etapas."""
    df = df.assign(grupo=np.where(df["canal_origem"] == "Correspondente",
                                  "Correspondente", "Outros canais"))
    perfil = df.groupby("grupo").agg(propostas=("contratada", "size"),
                                     conversao=("contratada", "mean"),
                                     ltv_medio=("ltv", "mean"),
                                     score_medio=("score_credito", "mean"),
                                     ticket_medio=("valor_solicitado", "mean")).round(3)
    faixa_score = pd.qcut(df["score_credito"], 4)
    por_score = df.pivot_table(index=faixa_score, columns="grupo", values="contratada",
                               aggfunc="mean", observed=True).round(3)
    faixa_ltv = pd.cut(df["ltv"], [0, .4, .5, .6, 1], labels=["até 40%", "40–50%", "50–60%", "acima de 60%"])
    por_ltv = df.pivot_table(index=faixa_ltv, columns="grupo", values="contratada",
                             aggfunc="mean", observed=True).round(3)
    passagem = {}
    for g, sub in df.groupby("grupo"):
        passagem[g] = [(sub["etapa_max_funil"] >= k + 1).sum() / (sub["etapa_max_funil"] >= k).sum()
                       for k in range(1, 6)]
    passagem = pd.DataFrame(passagem, index=[f"{ETAPAS[k]} -> {ETAPAS[k+1]}" for k in range(1, 6)]).round(3)
    return perfil, por_score, por_ltv, passagem


REGIOES = {"SP": "Sudeste", "RJ": "Sudeste", "MG": "Sudeste", "PR": "Sul", "SC": "Sul",
           "RS": "Sul", "GO": "Centro-Oeste", "DF": "Centro-Oeste", "PE": "Nordeste", "BA": "Nordeste"}


def pergunta3_caracteristicas(df):
    """Conversão por faixa de cada característica + p-valor do teste qui-quadrado.
    p-valor = chance de a diferença entre as faixas ser só acaso. Abaixo de 0,05 => associação real."""
    df = df.assign(
        regiao=df["uf"].map(REGIOES),
        faixa_score=pd.cut(df["score_credito"], [0, 600, 650, 700, 750, 1000]),
        faixa_ltv=pd.cut(df["ltv"], [0, .4, .5, .6, 1], labels=["até 40%", "40–50%", "50–60%", "acima de 60%"]),
        faixa_ticket=pd.qcut(df["valor_solicitado"], 4, labels=["1º quartil", "2º", "3º", "4º (maiores)"]),
        faixa_idade=pd.cut(df["idade_cliente"], [17, 30, 40, 50, 60, 80]),
        faixa_renda=pd.qcut(df["renda_mensal_declarada"], 4, labels=["1º quartil", "2º", "3º", "4º (maiores)"]),
    )
    variaveis = {"Score de crédito": "faixa_score", "LTV": "faixa_ltv", "Canal": "canal_origem",
                 "Cliente recorrente": "flag_cliente_recorrente", "Região": "regiao",
                 "Ticket": "faixa_ticket", "Tipo de imóvel": "tipo_imovel", "Renda": "faixa_renda",
                 "Prazo": "prazo_meses", "Idade": "faixa_idade", "Consultor": "consultor_id"}
    resumo, detalhes = [], {}
    for nome, col in variaveis.items():
        conv = df.groupby(col, observed=True)["contratada"].agg(propostas="size", conversao="mean")
        _, p, _, _ = chi2_contingency(pd.crosstab(df[col], df["contratada"]))
        detalhes[nome] = conv.round(3)
        resumo.append({"caracteristica": nome,
                       "melhor faixa": f"{conv['conversao'].idxmax()} ({100*conv['conversao'].max():.1f}%)",
                       "pior faixa": f"{conv['conversao'].idxmin()} ({100*conv['conversao'].min():.1f}%)",
                       "diferenca_pp": round(100 * (conv["conversao"].max() - conv["conversao"].min()), 1),
                       "p_valor": float(f"{p:.2g}"),
                       "associacao_real": "sim" if p < 0.05 else "não"})
    resumo = pd.DataFrame(resumo).sort_values("p_valor")
    return resumo, detalhes


def pergunta4_impactos(df, recuperacao_perdas=(0.05, 0.10, 0.20), recuperacao_doc=(0.20, 0.30, 0.50)):
    """Impacto estimado das 3 recomendações em cenários (pessimista, base, otimista).

    Premissas:
    - Rec. 1: uma proposta 'Sem retorno'/'Desistiu' recuperada volta ao funil e tem a mesma chance
      de contratar de quem passou da etapa em que ela parou.
    - Rec. 2: 'Documentação pendente' já passou por crédito e garantia; se o documento chegar, contrata.
    - Rec. 3: não é receita nova, é exposição a risco (contratos com parcela > renda declarada).
    """
    p_chegou = {k: df.loc[df["etapa_max_funil"] >= k, "contratada"].mean() for k in range(1, 7)}

    perdas = df[df["status_final"].isin(["Sem retorno", "Desistiu"])]
    chance = perdas["etapa_max_funil"].map(lambda k: p_chegou[min(k + 1, 6)])
    potencial_rec1 = (perdas["valor_solicitado"] * chance).sum()

    doc = df[df["status_final"] == "Documentação pendente"]["valor_solicitado"].sum()

    comprometimento = (df["valor_solicitado"] / df["prazo_meses"]) / df["renda_mensal_declarada"]
    risco = df[(comprometimento > 1) & df["contratada"]]

    cenarios = ["pessimista", "base", "otimista"]
    tabela = pd.DataFrame({
        "1. Investigar causas e reduzir Sem retorno/Desistiu (R$ mi)": [potencial_rec1 * r / 1e6 for r in recuperacao_perdas],
        "2. Recuperar Documentação pendente (R$ mi)": [doc * r / 1e6 for r in recuperacao_doc],
    }, index=cenarios).round(1)
    tabela["premissa rec.1 (% recuperado)"] = [f"{100*r:.0f}%" for r in recuperacao_perdas]
    tabela["premissa rec.2 (% recuperado)"] = [f"{100*r:.0f}%" for r in recuperacao_doc]
    info_risco = {"contratos": len(risco), "exposicao_mi": round(risco["valor_solicitado"].sum() / 1e6, 1),
                  "ltv_medio": round(risco["ltv"].mean(), 2)}
    return tabela, info_risco


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    df, registro = carregar_e_tratar(ARQUIVO_PADRAO)
    salvar_registro_md(registro, REGISTRO_MD, registro.attrs.get("impacto_remocoes"))

    print(f"Base analisada: {len(df)} propostas | contratadas: {df['contratada'].sum()} "
          f"({100 * df['contratada'].mean():.1f}%)")
    print(f"Volume solicitado total: R$ {df['valor_solicitado'].sum() / 1e6:,.1f} mi | "
          f"contratado: R$ {df.loc[df['contratada'], 'valor_solicitado'].sum() / 1e6:,.1f} mi\n")

    print("=== P1. Perda por etapa ===")
    print(pergunta1_perda_por_etapa(df).to_string(index=False))
    print("\n=== P1. R$ perdido (milhões) por motivo x etapa ===")
    print(pergunta1_perda_por_motivo(df).to_string())

    print("\n=== P2a. Conversão por trimestre de entrada ===")
    print(pergunta2_conversao_no_tempo(df).to_string())
    tri = df["data_entrada"].dt.to_period("Q").astype(str)
    antes = df.loc[tri.isin(["2024Q3", "2024Q4", "2025Q1", "2025Q2"]), "contratada"]
    depois = df.loc[tri == "2025Q3", "contratada"]
    pa, pb, z = teste_proporcoes(antes, depois)
    print(f"2024T3–2025T2: {100*pa:.1f}% | 2025T3: {100*pb:.1f}% | z = {z:.2f}")

    print("\n=== P2b. Correspondente x outros canais ===")
    perfil, por_score, por_ltv, passagem = pergunta2_correspondentes(df)
    print(perfil.to_string()); print(); print(por_score.to_string()); print()
    print(por_ltv.to_string()); print(); print(passagem.to_string())
    corr = df["canal_origem"] == "Correspondente"
    pa, pb, z = teste_proporcoes(df.loc[corr, "contratada"], df.loc[~corr, "contratada"])
    print(f"Correspondente {100*pa:.1f}% x outros {100*pb:.1f}% | z = {z:.2f}")

    print("\n=== P3. Características associadas à contratação ===")
    resumo, detalhes = pergunta3_caracteristicas(df)
    print(resumo.to_string(index=False))
    comprometimento = (df["valor_solicitado"] / df["prazo_meses"]) / df["renda_mensal_declarada"]
    estranho = (comprometimento > 1) & df["contratada"]
    print(f"\nAlerta: {estranho.sum()} contratos com parcela (sem juros) maior que a renda declarada")

    print("\n=== P4. Impacto estimado das recomendações (R$ em novos contratos) ===")
    tabela, risco = pergunta4_impactos(df)
    print(tabela.to_string())
    print(f"3. Renda declarada: {risco['contratos']} contratos, R$ {risco['exposicao_mi']} mi expostos "
          f"(LTV médio {risco['ltv_medio']:.0%})")