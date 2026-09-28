"""
tratamento.py — Leitura e limpeza da base propostas_credito.csv

Uso:
    from tratamento import carregar_e_tratar
    df, registro = carregar_e_tratar("dados/propostas_credito.csv")

Cada problema encontrado vira uma linha no `registro` (problema, linhas afetadas,
decisão, justificativa). Só são removidas propostas que violam regra de negócio
(cliente menor de 18 anos) ou que o enunciado manda excluir (Terreno); os demais problemas pontuais viram flags ou correções.
"""

import csv
import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger("tratamento")
PASTA = Path(__file__).resolve().parent
ARQUIVO_PADRAO = PASTA / "dados" / "propostas_credito.csv"
REGISTRO_MD = PASTA / "parte 1" / "registro_tratamento.md"   # o registro é um entregável da Parte 1

# Colunas sem as quais a análise do funil não funciona.
COLUNAS_OBRIGATORIAS = [
    "id_proposta", "data_entrada", "canal_origem", "tipo_imovel",
    "valor_imovel", "valor_solicitado", "etapa_max_funil", "status_final",
    "score_credito",
]
# Colunas usadas em análises secundárias: se faltarem, só avisamos.
COLUNAS_OPCIONAIS = [
    "cidade", "uf", "prazo_meses", "idade_cliente",
    "renda_mensal_declarada", "flag_cliente_recorrente", "consultor_id",
    "tempo_analise_dias", "data_assinatura_contrato", "taxa_juros_aa",
]

ETAPAS = {1: "Simulação", 2: "Lead", 3: "Análise de crédito",
          4: "Avaliação do imóvel", 5: "Formalização", 6: "Contratação"}
RENDA_SUSPEITA = 1800.00


class ErroEstrutura(Exception):
    """Arquivo de entrada com problema de estrutura (vazio, sem colunas essenciais...)."""


def ler_arquivo(caminho):
    """Lê o arquivo de entrada tolerando mudanças comuns de formato:
    - Excel (.xlsx) em vez de CSV
    - separador ';' ou tab em vez de ','
    - encoding latin-1 (Excel brasileiro) em vez de UTF-8
    - nomes de coluna com espaços ou maiúsculas
    Devolve o DataFrame (tudo como texto) e uma descrição do formato detectado."""
    caminho = Path(caminho)
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo de entrada não encontrado: {caminho.resolve()}")
    if caminho.stat().st_size == 0:
        raise ErroEstrutura(f"o arquivo {caminho.name} está vazio")

    if caminho.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(caminho, dtype=str)
        formato = "Excel"
    else:
        for encoding in ("utf-8-sig", "latin-1"):
            try:
                with open(caminho, encoding=encoding) as f:
                    amostra = f.read(20000)
                break
            except UnicodeDecodeError:
                continue
        try:
            separador = csv.Sniffer().sniff(amostra.splitlines()[0], delimiters=",;\t|").delimiter
        except csv.Error:
            separador = ","
        df = pd.read_csv(caminho, dtype=str, encoding=encoding, sep=separador)
        formato = f"CSV (separador '{separador}', encoding {encoding})"

    df.columns = df.columns.str.strip().str.lower()
    if df.empty:
        raise ErroEstrutura(f"o arquivo {caminho.name} tem cabeçalho, mas nenhuma linha de dados")
    return df, formato


def _registrar(registro, problema, n, decisao, justificativa):
    registro.append({"problema": problema, "linhas_afetadas": int(n),
                     "decisao": decisao, "justificativa": justificativa})
    if n:
        log.info("%s: %d linha(s) -> %s", problema, n, decisao)


def validar_colunas(df):
    faltando = [c for c in COLUNAS_OBRIGATORIAS if c not in df.columns]
    if faltando:
        raise ErroEstrutura(f"Colunas obrigatórias ausentes: {faltando}")
    for c in COLUNAS_OPCIONAIS:
        if c not in df.columns:
            log.warning("Coluna opcional ausente: %s (análises dela serão puladas)", c)
            df[c] = pd.NA
    extras = set(df.columns) - set(COLUNAS_OBRIGATORIAS) - set(COLUNAS_OPCIONAIS)
    if extras:
        log.warning("Colunas novas não esperadas (ignoradas): %s", sorted(extras))
    return df


def carregar_e_tratar(caminho):
    registro = []

    # 1. Leitura: tudo como texto, para nenhum valor estranho ser convertido em silêncio.
    #    utf-8-sig remove o BOM do início do arquivo; ler_arquivo detecta outros formatos.
    df, formato = ler_arquivo(caminho)
    log.info("Arquivo lido: %d linhas, %d colunas | formato: %s", len(df), df.shape[1], formato)
    df = validar_colunas(df)
    _registrar(registro, "Formato do arquivo de entrada", 0, f"Lido como {formato}",
               "Separador e encoding detectados automaticamente; BOM removido com utf-8-sig")

    # 2. Canal de origem com grafias diferentes ("mídia paga " vs "Mídia paga").
    #    Agrupa por versão minúscula e sem espaços e usa a grafia mais frequente.
    bruto = df["canal_origem"].copy()
    chave = bruto.str.strip().str.lower()
    canonico = bruto.groupby(chave).agg(lambda s: s.value_counts().index[0])
    df["canal_origem"] = chave.map(canonico)
    _registrar(registro, "canal_origem com grafias diferentes", (bruto != df["canal_origem"]).sum(),
               "Padronizado para a grafia mais frequente",
               "São o mesmo canal; separados, criariam canais fantasmas com 1–2 propostas")

    # 3. Valores numéricos com texto ("R$ 574857.06").
    for col in ["valor_imovel", "valor_solicitado", "renda_mensal_declarada"]:
        com_rs = df[col].str.contains("R$", regex=False, na=False)
        df[col] = pd.to_numeric(df[col].str.replace("R$", "", regex=False).str.strip(),
                                errors="coerce")
        if com_rs.any():
            _registrar(registro, f"{col} com prefixo 'R$'", com_rs.sum(),
                       "Prefixo removido e convertido para número", "Valor em si é válido")
    for col in ["prazo_meses", "score_credito", "idade_cliente", "etapa_max_funil",
                "tempo_analise_dias", "taxa_juros_aa", "flag_cliente_recorrente"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 4. Datas de entrada em dd/mm/aaaa no meio de aaaa-mm-dd.
    iso = pd.to_datetime(df["data_entrada"], format="%Y-%m-%d", errors="coerce")
    br = pd.to_datetime(df["data_entrada"], format="%d/%m/%Y", errors="coerce")
    fora_padrao = iso.isna() & br.notna()
    df["data_entrada"] = iso.fillna(br)
    _registrar(registro, "data_entrada no formato dd/mm/aaaa", fora_padrao.sum(),
               "Convertida como dia/mês/ano",
               "Confirmado na PR-000153: entrada + tempo_analise_dias = data de assinatura")
    sem_data = df["data_entrada"].isna().sum()
    if sem_data:
        _registrar(registro, "data_entrada ilegível", sem_data, "Mantida vazia",
                   "Proposta conta no funil, mas não entra em análises por mês")
    df["data_assinatura_contrato"] = pd.to_datetime(df["data_assinatura_contrato"], errors="coerce")

    # 5. Taxa: nome diz 'aa', dicionário diz '% a.m.', valores (0,9–1,7) confirmam a.m.
    df = df.rename(columns={"taxa_juros_aa": "taxa_juros_am"})
    _registrar(registro, "taxa_juros_aa: nome diz ao ano, dicionário diz ao mês", 0,
               "Renomeada para taxa_juros_am",
               "Valores entre 0,94 e 1,73: como taxa anual seriam impossíveis; ao mês (~17% a.a.) são típicos de home equity")

    # 6. LTV não veio na extração: calcular.
    df["ltv"] = df["valor_solicitado"] / df["valor_imovel"]
    df["ltv_acima_politica"] = df["ltv"] > 0.60
    _registrar(registro, "Coluna ltv ausente no arquivo", len(df),
               "Calculada como valor_solicitado / valor_imovel",
               "Definição do próprio dicionário de dados")

    # 7. Etapa fora da faixa 1–6.
    etapa7 = (df["etapa_max_funil"] > 6) & (df["status_final"] == "Contratada")
    df.loc[etapa7, "etapa_max_funil"] = 6
    _registrar(registro, "etapa_max_funil = 7 (inexistente)", etapa7.sum(),
               "Corrigida para 6", "Status 'Contratada' só existe na etapa 6")
    outras = ~df["etapa_max_funil"].between(1, 6)
    if outras.any():
        _registrar(registro, "etapa_max_funil fora de 1–6 sem explicação", outras.sum(),
                   "Mantida e marcada", "Sem informação suficiente para corrigir")

    # 8. Idade menor que 18: proposta inválida pela regra de negócio.
    idade_inv = df["idade_cliente"] < 18
    ids = df.loc[idade_inv, "id_proposta"].tolist()
    df = df[~idade_inv].copy()
    _registrar(registro, "idade_cliente menor que 18", idade_inv.sum(),
               f"Proposta removida da base ({', '.join(ids)})",
               "Só maiores de 18 podem solicitar crédito; a proposta não deveria existir no sistema")

    # 9. Assinatura antes da entrada: assumimos que a data de assinatura está certa
    #    e reconstruímos a entrada como assinatura - tempo_analise_dias.
    dias = (df["data_assinatura_contrato"] - df["data_entrada"]).dt.days
    inconsist = dias < 0
    df.loc[inconsist, "data_entrada"] = (
        df.loc[inconsist, "data_assinatura_contrato"]
        - pd.to_timedelta(df.loc[inconsist, "tempo_analise_dias"], unit="D"))
    _registrar(registro, "Assinatura anterior à data de entrada", inconsist.sum(),
               "data_entrada recalculada = data_assinatura - tempo_analise_dias",
               "Premissa: a data do contrato é a mais confiável (documento assinado); "
               "tempo_analise_dias bate com as datas em 99,7% das contratadas")

    # 10. Renda exatamente R$ 1.800,00 (possível valor padrão do sistema).
    df["flag_renda_suspeita"] = df["renda_mensal_declarada"] == RENDA_SUSPEITA
    _registrar(registro, "Renda exatamente R$ 1.800,00", df["flag_renda_suspeita"].sum(),
               "Mantida e marcada",
               "Concentração anormal num valor redondo; renda usada com cautela")

    # 11. Scores extremos (válidos na escala 0–1000, mas raros).
    extremos = (df["score_credito"] > 900) | (df["score_credito"] < 400)
    _registrar(registro, "score_credito extremo (<400 ou >900)", extremos.sum(),
               "Mantido", "Dentro da escala do bureau; só registrado")

    # 12. Terreno: removido conforme instrução do dicionário de dados do enunciado.
    terreno = df["tipo_imovel"].str.strip().str.lower() == "terreno"
    contratada = df["status_final"] == "Contratada"
    corresp = df["canal_origem"] == "Correspondente"
    impacto = pd.DataFrame({
        "Com terreno": [len(df), contratada.mean(), contratada[corresp].mean(),
                        df["valor_solicitado"].sum() / 1e6],
        "Sem terreno (base final)": [(~terreno).sum(), contratada[~terreno].mean(),
                                     contratada[corresp & ~terreno].mean(),
                                     df.loc[~terreno, "valor_solicitado"].sum() / 1e6],
    }, index=["Propostas", "Conversão geral", "Conversão correspondentes", "R$ solicitado (mi)"])
    df = df[~terreno].copy()
    _registrar(registro, "tipo_imovel = Terreno", terreno.sum(),
               "Propostas removidas da base",
               "Instrução explícita do enunciado: a análise não considera terreno como garantia")

    # Colunas auxiliares para as análises
    df["mes_entrada"] = df["data_entrada"].dt.to_period("M")
    df["contratada"] = df["status_final"] == "Contratada"

    log.info("Tratamento concluído: %d linhas finais", len(df))
    registro = pd.DataFrame(registro)
    # O impacto das remoções viaja junto com o registro (e não com df), porque o pandas
    # compara os 'attrs' ao juntar tabelas e não consegue comparar uma tabela dentro deles.
    registro.attrs["impacto_remocoes"] = impacto
    return df, registro


def salvar_registro_md(registro, caminho, impacto=None):
    """Salva o registro de tratamento como tabela Markdown."""
    linhas = ["# Registro de tratamento de dados", "",
              "| # | Problema | Linhas afetadas | Decisão | Justificativa |",
              "|---|---|---|---|---|"]
    for i, r in enumerate(registro.itertuples(), 1):
        linhas.append(f"| {i} | {r.problema} | {r.linhas_afetadas} | {r.decisao} | {r.justificativa} |")
    if impacto is not None:
        linhas += ["", "## Impacto das remoções nos resultados", "",
                   "| Métrica | Com terreno | Sem terreno (base final) |", "|---|---|---|"]
        for metrica, row in impacto.iterrows():
            fmt = ((lambda v: f"{100*v:.1f}%".replace(".", ",")) if "Conversão" in metrica
                   else (lambda v: f"{v:,.0f}".replace(",", ".")))
            linhas.append(f"| {metrica} | {fmt(row.iloc[0])} | {fmt(row.iloc[1])} |")
        dif_geral = 100 * abs(impacto.iloc[1, 0] - impacto.iloc[1, 1])
        dif_corr = 100 * abs(impacto.iloc[2, 0] - impacto.iloc[2, 1])
        linhas += ["", f"A remoção dos terrenos altera a conversão geral em {dif_geral:.1f} p.p. "
                   f"e a dos correspondentes em {dif_corr:.1f} p.p.".replace(".", ",").replace("p,p,", "p.p.")
                   + " A remoção da proposta com cliente menor de idade (1 linha) tem efeito desprezível."]
    with open(caminho, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    caminho = sys.argv[1] if len(sys.argv) > 1 else ARQUIVO_PADRAO
    df, reg = carregar_e_tratar(caminho)
    salvar_registro_md(reg, REGISTRO_MD, reg.attrs.get("impacto_remocoes"))
    print(reg.to_string(index=False))
    print(f"\nRegistro salvo em {REGISTRO_MD}")