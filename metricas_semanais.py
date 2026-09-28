"""
metricas_semanais.py — Calcula as métricas do relatório semanal do funil.

Recebe a base já tratada (tratamento.py) e devolve um dicionário com todas as tabelas
que os exportadores (HTML, Excel, PDF) vão mostrar. Nenhum formato de saída é decidido aqui:
os três relatórios mostram exatamente os mesmos números.
"""

import pandas as pd

from tratamento import ETAPAS

# Parâmetros do relatório (mudar aqui, e não espalhado pelo código)
LTV_MAXIMO = 0.60          # política de crédito
MATURACAO_DIAS = 80        # a análise mais longa da base levou 78 dias
MESES_TENDENCIA = 6        # meses mostrados na tabela de tendência
SEMANAS_COMPARACAO = 4     # a semana é comparada com a média das 4 anteriores


def _janela(df, coluna, inicio, fim):
    """Linhas cuja data em `coluna` está entre inicio e fim (inclusive)."""
    return df[(df[coluna] >= inicio) & (df[coluna] <= fim)]


def resumo_semana(df, data_corte):
    """Números da semana que termina em data_corte, comparados com as semanas anteriores."""
    inicio = data_corte - pd.Timedelta(days=6)
    entradas = _janela(df, "data_entrada", inicio, data_corte)
    assinados = _janela(df, "data_assinatura_contrato", inicio, data_corte)

    ini_ant = inicio - pd.Timedelta(weeks=SEMANAS_COMPARACAO)
    fim_ant = inicio - pd.Timedelta(days=1)
    entradas_ant = len(_janela(df, "data_entrada", ini_ant, fim_ant)) / SEMANAS_COMPARACAO
    assinados_ant = _janela(df, "data_assinatura_contrato", ini_ant, fim_ant)

    return {
        "inicio": inicio, "fim": data_corte,
        "propostas_novas": len(entradas),
        "propostas_novas_media_ant": entradas_ant,
        "contratos_assinados": len(assinados),
        "contratos_assinados_media_ant": len(assinados_ant) / SEMANAS_COMPARACAO,
        "rs_contratado": assinados["valor_solicitado"].sum(),
        "rs_contratado_media_ant": assinados_ant["valor_solicitado"].sum() / SEMANAS_COMPARACAO,
    }


def tendencia_mensal(df, data_corte):
    """Conversão por mês de entrada nos últimos meses. Meses recentes são marcados como
    'em maturação': parte das propostas ainda pode não ter desfecho (achado da Parte 1)."""
    inicio = (data_corte - pd.DateOffset(months=MESES_TENDENCIA - 1)).to_period("M").to_timestamp()
    base = df[(df["data_entrada"] >= inicio) & (df["data_entrada"] <= data_corte)].copy()
    base["mes"] = base["data_entrada"].dt.to_period("M")
    t = base.groupby("mes").agg(propostas=("contratada", "size"),
                                contratadas=("contratada", "sum"),
                                correspondente=("canal_origem", lambda s: (s == "Correspondente").sum()))
    limite_maduro = data_corte - pd.Timedelta(days=MATURACAO_DIAS)
    t["situacao"] = ["em maturação" if m.end_time > limite_maduro else "completo" for m in t.index]
    t.index = t.index.astype(str)
    return t.reset_index()


def funil_e_perdas(df, data_corte):
    """Funil dos últimos 6 meses: quantas chegam a cada etapa, quantas param nela e quanto
    R$ se perde (bruto e ponderado pela chance de contratar — mesma lógica da Parte 1)."""
    inicio = data_corte - pd.DateOffset(months=MESES_TENDENCIA)
    base = df[(df["data_entrada"] > inicio) & (df["data_entrada"] <= data_corte)]
    linhas = []
    for k, nome in ETAPAS.items():
        chegaram = base[base["etapa_max_funil"] >= k]
        perdidas = base[(base["etapa_max_funil"] == k) & ~base["contratada"]]
        linhas.append({
            "etapa": f"{k}. {nome}",
            "chegaram": len(chegaram),
            "perdidas": len(perdidas) if k < 6 else 0,
            "rs_perdido": perdidas["valor_solicitado"].sum() if k < 6 else 0.0,
            "chance_contratar": chegaram["contratada"].mean() if len(chegaram) else 0.0,
        })
    return pd.DataFrame(linhas)


def canais(df, data_corte):
    """Desempenho por canal nos últimos 6 meses."""
    inicio = data_corte - pd.DateOffset(months=MESES_TENDENCIA)
    base = df[(df["data_entrada"] > inicio) & (df["data_entrada"] <= data_corte)]
    t = base.groupby("canal_origem").agg(
        propostas=("contratada", "size"),
        contratadas=("contratada", "sum"),
        rs_contratado=("valor_solicitado", lambda s: s[base.loc[s.index, "contratada"]].sum()),
    )
    return t.sort_values("propostas", ascending=False).reset_index()


def alertas(df, data_corte):
    """Contratos assinados na semana que merecem revisão (achados da Parte 1)."""
    inicio = data_corte - pd.Timedelta(days=6)
    semana = _janela(df, "data_assinatura_contrato", inicio, data_corte).copy()
    semana["parcela_sem_juros"] = semana["valor_solicitado"] / semana["prazo_meses"]
    colunas = ["id_proposta", "canal_origem", "valor_solicitado", "ltv",
               "renda_mensal_declarada", "parcela_sem_juros"]
    ltv = semana[semana["ltv"] > LTV_MAXIMO][colunas].assign(motivo="LTV acima de 60%")
    renda = semana[semana["parcela_sem_juros"] > semana["renda_mensal_declarada"]][colunas].assign(
        motivo="Parcela maior que a renda declarada")
    return pd.concat([ltv, renda], ignore_index=True)


def calcular(df, registro, data_corte=None):
    """Calcula tudo. data_corte = último dia da semana do relatório.
    Se não for informada, usa a data de entrada mais recente da base."""
    if data_corte is None:
        data_corte = df["data_entrada"].max()
    data_corte = pd.Timestamp(data_corte).normalize()
    qualidade = registro[registro["linhas_afetadas"] > 0][["problema", "linhas_afetadas", "decisao"]]
    return {
        "data_corte": data_corte,
        "total_propostas_base": len(df),
        "semana": resumo_semana(df, data_corte),
        "tendencia": tendencia_mensal(df, data_corte),
        "funil": funil_e_perdas(df, data_corte),
        "canais": canais(df, data_corte),
        "alertas": alertas(df, data_corte),
        "qualidade": qualidade.reset_index(drop=True),
    }
