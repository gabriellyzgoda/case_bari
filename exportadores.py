"""
exportadores.py — Gera o relatório semanal em HTML, Excel e PDF.

Os três recebem o mesmo dicionário de métricas (metricas_semanais.calcular),
então mostram exatamente os mesmos números. Cada função é independente:
se uma falhar, as outras continuam funcionando.
"""

from html import escape
from pathlib import Path

import pandas as pd

from metricas_semanais import LTV_MAXIMO, MATURACAO_DIAS


# ---------------------------------------------------------------- formatação pt-BR
def moeda(v):
    """R$ com separadores brasileiros. Valores grandes em milhões."""
    if pd.isna(v):
        return "-"
    if abs(v) >= 1e6:
        return f"R$ {v / 1e6:,.1f} mi".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {v:,.0f}".replace(",", ".")


def pct(v, casas=1):
    return "-" if pd.isna(v) else f"{100 * v:.{casas}f}%".replace(".", ",")


def inteiro(v):
    return "-" if pd.isna(v) else f"{v:,.0f}".replace(",", ".")


def variacao(atual, anterior):
    """Texto da variação em relação à média anterior."""
    if not anterior:
        return "sem base de comparação"
    delta = atual / anterior - 1
    sinal = "+" if delta >= 0 else ""
    return f"{sinal}{100 * delta:.0f}% vs. média das 4 semanas anteriores".replace(".", ",")


def data_br(d):
    return pd.Timestamp(d).strftime("%d/%m/%Y")


def nome_arquivo(m, extensao):
    return f"relatorio_funil_{m['data_corte']:%Y-%m-%d}.{extensao}"


# ---------------------------------------------------------------- HTML
CSS = """
:root { --tinta:#1d2b3a; --texto:#34414f; --suave:#6b7885; --linha:#d9e0e7;
        --fundo:#f5f7f9; --barra:#2f5d8a; --perda:#c0633c; --ok:#2f7a57; }
* { box-sizing:border-box; }
body { margin:0; background:var(--fundo); color:var(--texto);
       font:15px/1.55 "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }
main { max-width:880px; margin:0 auto; padding:32px 20px 48px; }
header { border-bottom:3px solid var(--tinta); padding-bottom:14px; margin-bottom:28px; }
h1 { color:var(--tinta); font-size:26px; margin:0 0 4px; font-weight:600; }
h2 { color:var(--tinta); font-size:18px; margin:36px 0 10px; font-weight:600; }
.sub { color:var(--suave); margin:0; }
.kpis { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:1px;
        background:var(--linha); border:1px solid var(--linha); }
.kpi { background:#fff; padding:16px 18px; }
.kpi b { display:block; color:var(--tinta); font-size:24px; font-weight:600; }
.kpi span { color:var(--suave); font-size:13px; }
table { width:100%; border-collapse:collapse; background:#fff; font-size:14px; }
th { text-align:left; color:var(--suave); font-weight:600; border-bottom:2px solid var(--linha);
     padding:8px 10px; }
td { border-bottom:1px solid var(--linha); padding:8px 10px; }
td.n, th.n { text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }
td.b, th.b { width:22%; }
td.id { white-space:nowrap; }
.tabela { overflow-x:auto; }
.barra { height:10px; background:var(--barra); border-radius:2px; min-width:2px; }
.perda { background:var(--perda); }
.nota { color:var(--suave); font-size:13px; margin:8px 0 0; }
.maturacao { color:var(--perda); }
.alerta { border-left:4px solid var(--perda); background:#fff; padding:12px 16px; }
.tudo-ok { border-left:4px solid var(--ok); background:#fff; padding:12px 16px; }
footer { margin-top:40px; color:var(--suave); font-size:12px; }
"""


def _tabela_html(cabecalho, linhas, numericas=(), barras=(), ids=()):
    def classe(i):
        return "n" if i in numericas else "b" if i in barras else "id" if i in ids else ""
    th = "".join(f'<th class="{classe(i)}">{escape(c)}</th>' for i, c in enumerate(cabecalho))
    corpo = ""
    for linha in linhas:
        corpo += "<tr>" + "".join(f'<td class="{classe(i)}">{c}</td>' for i, c in enumerate(linha)) + "</tr>"
    return f'<div class="tabela"><table><thead><tr>{th}</tr></thead><tbody>{corpo}</tbody></table></div>'


def exportar_html(m, pasta):
    s = m["semana"]
    kpis = f"""
    <div class="kpis">
      <div class="kpi"><b>{inteiro(s['propostas_novas'])}</b>propostas novas
        <br><span>{variacao(s['propostas_novas'], s['propostas_novas_media_ant'])}</span></div>
      <div class="kpi"><b>{inteiro(s['contratos_assinados'])}</b>contratos assinados
        <br><span>{variacao(s['contratos_assinados'], s['contratos_assinados_media_ant'])}</span></div>
      <div class="kpi"><b>{moeda(s['rs_contratado'])}</b>em crédito contratado
        <br><span>{variacao(s['rs_contratado'], s['rs_contratado_media_ant'])}</span></div>
    </div>"""

    t = m["tendencia"]
    linhas_t = [[r.mes, inteiro(r.propostas), pct(r.contratadas / r.propostas),
                 pct(r.correspondente / r.propostas),
                 f'<span class="maturacao">{r.situacao}</span>' if r.situacao != "completo" else r.situacao]
                for r in t.itertuples()]
    tabela_t = _tabela_html(["Mês de entrada", "Propostas", "Conversão", "% correspondente", "Situação"],
                            linhas_t, numericas=(1, 2, 3))

    f = m["funil"]
    maior = f["chegaram"].max() or 1
    maior_perda = f["rs_perdido"].max() or 1
    linhas_f = [[r.etapa, inteiro(r.chegaram),
                 f'<div class="barra" style="width:{100 * r.chegaram / maior:.0f}%"></div>',
                 inteiro(r.perdidas) if r.perdidas else "-",
                 moeda(r.rs_perdido) if r.rs_perdido else "-",
                 f'<div class="barra perda" style="width:{100 * r.rs_perdido / maior_perda:.0f}%"></div>'
                 if r.rs_perdido else ""]
                for r in f.itertuples()]
    tabela_f = _tabela_html(["Etapa", "Chegaram", "", "Pararam aqui", "R$ perdido", ""],
                            linhas_f, numericas=(1, 3, 4), barras=(2, 5))

    c = m["canais"]
    linhas_c = [[r.canal_origem, inteiro(r.propostas), pct(r.contratadas / r.propostas),
                 moeda(r.rs_contratado)] for r in c.itertuples()]
    tabela_c = _tabela_html(["Canal", "Propostas", "Conversão", "R$ contratado"], linhas_c,
                            numericas=(1, 2, 3))

    a = m["alertas"]
    if a.empty:
        bloco_a = '<p class="tudo-ok">Nenhum contrato assinado na semana acima do LTV máximo ou com parcela maior que a renda declarada.</p>'
    else:
        linhas_a = [[escape(r.id_proposta), escape(r.motivo), escape(r.canal_origem), moeda(r.valor_solicitado),
                     pct(r.ltv), moeda(r.renda_mensal_declarada), moeda(r.parcela_sem_juros)]
                    for r in a.itertuples()]
        bloco_a = '<div class="alerta">' + _tabela_html(
            ["Proposta", "Motivo", "Canal", "Valor", "LTV", "Renda", "Parcela s/ juros"],
            linhas_a, numericas=(3, 4, 5, 6), ids=(0,)) + "</div>"

    q = m["qualidade"]
    linhas_q = [[escape(r.problema), inteiro(r.linhas_afetadas), escape(r.decisao)] for r in q.itertuples()]
    tabela_q = _tabela_html(["Problema encontrado no arquivo", "Linhas", "O que foi feito"], linhas_q,
                            numericas=(1,))

    html = f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Funil de crédito — semana até {data_br(m['data_corte'])}</title>
<style>{CSS}</style></head>
<body><main>
<header>
  <h1>Funil de crédito — relatório semanal</h1>
  <p class="sub">Semana de {data_br(s['inicio'])} a {data_br(s['fim'])} ·
     base com {inteiro(m['total_propostas_base'])} propostas analisadas</p>
</header>

<h2>A semana</h2>
{kpis}

<h2>Conversão por mês de entrada</h2>
{tabela_t}
<p class="nota">Meses "em maturação" ainda têm propostas sem desfecho (a análise pode levar até
{MATURACAO_DIAS} dias), por isso a conversão deles tende a subir. Compare apenas meses completos.</p>

<h2>Onde o funil perde (últimos 6 meses)</h2>
{tabela_f}
<p class="nota">Perdas no fim do funil custam mais: a proposta estava mais perto de fechar e o banco já
pagou análise de crédito e laudo.</p>

<h2>Canais (últimos 6 meses)</h2>
{tabela_c}

<h2>Contratos da semana para revisão</h2>
{bloco_a}
<p class="nota">Critérios: LTV acima de {pct(LTV_MAXIMO, 0)} (política de crédito) ou parcela, mesmo sem juros,
maior que a renda mensal declarada.</p>

<h2>Qualidade dos dados</h2>
{tabela_q}

<footer>Gerado automaticamente por relatorio_semanal.py. Dados sintéticos do desafio.</footer>
</main></body></html>"""
    caminho = Path(pasta) / nome_arquivo(m, "html")
    caminho.write_text(html, encoding="utf-8")
    return caminho


# ---------------------------------------------------------------- Excel
def exportar_excel(m, pasta):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    fonte = "Arial"
    negrito = Font(name=fonte, bold=True, color="FFFFFF")
    normal = Font(name=fonte)
    cabecalho_fill = PatternFill("solid", fgColor="1D2B3A")
    fmt_moeda = 'R$ #,##0;-R$ #,##0;"-"'
    fmt_pct = '0.0%;-0.0%;"-"'

    wb = Workbook()

    def aba(nome, cabecalho, linhas, formatos, larguras, nota=None):
        ws = wb.create_sheet(nome)
        ws.append(cabecalho)
        for c in ws[1]:
            c.font, c.fill = negrito, cabecalho_fill
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        for linha in linhas:
            ws.append(linha)
        for linha in ws.iter_rows(min_row=2):
            for c in linha:
                c.font = normal
                fmt = formatos.get(c.column)
                if fmt:
                    c.number_format = fmt
        for i, w in enumerate(larguras, 1):
            ws.column_dimensions[get_column_letter(i)].width = w
        ws.freeze_panes = "A2"
        if nota:
            ws.cell(row=ws.max_row + 2, column=1, value=nota).font = Font(name=fonte, italic=True)
        return ws

    # Resumo
    s = m["semana"]
    ws = wb.active
    ws.title = "Resumo"
    ws["A1"] = "Funil de crédito — relatório semanal"
    ws["A1"].font = Font(name=fonte, bold=True, size=14)
    ws["A2"] = f"Semana de {data_br(s['inicio'])} a {data_br(s['fim'])}"
    ws["A2"].font = normal
    ws.append([])
    ws.append(["Indicador", "Semana", "Média 4 semanas anteriores", "Variação"])
    for c in ws[4]:
        c.font, c.fill = negrito, cabecalho_fill
    dados = [("Propostas novas", s["propostas_novas"], s["propostas_novas_media_ant"], "0"),
             ("Contratos assinados", s["contratos_assinados"], s["contratos_assinados_media_ant"], "0"),
             ("R$ contratado", s["rs_contratado"], s["rs_contratado_media_ant"], fmt_moeda)]
    for i, (nome, atual, ant, fmt) in enumerate(dados, start=5):
        ws.append([nome, atual, ant, f"=IFERROR(B{i}/C{i}-1,\"-\")"])
        ws[f"B{i}"].number_format = fmt_moeda if fmt == fmt_moeda else "#,##0"
        ws[f"C{i}"].number_format = fmt_moeda if fmt == fmt_moeda else "#,##0.0"
        ws[f"D{i}"].number_format = '+0%;-0%;0%'
        for col in "ABCD":
            ws[f"{col}{i}"].font = normal
    for col, w in zip("ABCD", (26, 16, 28, 14)):
        ws.column_dimensions[col].width = w
    ws["A10"] = "As demais abas trazem o detalhamento. Colunas de conversão usam fórmulas."
    ws["A10"].font = Font(name=fonte, italic=True)

    # Tendência mensal: conversão e % correspondente como fórmula
    t = m["tendencia"]
    linhas = [[r.mes, r.propostas, r.contratadas, f"=C{i}/B{i}", r.correspondente, f"=E{i}/B{i}", r.situacao]
              for i, r in enumerate(t.itertuples(), start=2)]
    aba("Tendência mensal",
        ["Mês de entrada", "Propostas", "Contratadas", "Conversão", "Correspondente", "% correspondente", "Situação"],
        linhas, {4: fmt_pct, 6: fmt_pct}, (16, 12, 13, 12, 16, 18, 15),
        nota=f"'Em maturação': propostas com menos de {MATURACAO_DIAS} dias podem ainda não ter desfecho.")

    # Funil
    f = m["funil"]
    linhas = [[r.etapa, r.chegaram, r.perdidas, r.rs_perdido, r.chance_contratar, f"=D{i}*E{i}"]
              for i, r in enumerate(f.itertuples(), start=2)]
    aba("Funil (6 meses)",
        ["Etapa", "Chegaram", "Pararam aqui", "R$ perdido", "Chance de contratar ao chegar", "R$ ponderado"],
        linhas, {4: fmt_moeda, 5: fmt_pct, 6: fmt_moeda}, (24, 11, 13, 18, 20, 18),
        nota="R$ ponderado = R$ perdido x chance que a proposta tinha de virar contrato naquela etapa.")

    # Canais
    c = m["canais"]
    linhas = [[r.canal_origem, r.propostas, r.contratadas, f"=C{i}/B{i}", r.rs_contratado]
              for i, r in enumerate(c.itertuples(), start=2)]
    aba("Canais (6 meses)", ["Canal", "Propostas", "Contratadas", "Conversão", "R$ contratado"],
        linhas, {4: fmt_pct, 5: fmt_moeda}, (18, 12, 13, 12, 18))

    # Alertas
    a = m["alertas"]
    linhas = [[r.id_proposta, r.motivo, r.canal_origem, r.valor_solicitado, r.ltv,
               r.renda_mensal_declarada, r.parcela_sem_juros] for r in a.itertuples()]
    aba("Alertas da semana",
        ["Proposta", "Motivo", "Canal", "Valor", "LTV", "Renda declarada", "Parcela sem juros"],
        linhas, {4: fmt_moeda, 5: fmt_pct, 6: fmt_moeda, 7: fmt_moeda}, (14, 34, 16, 16, 9, 16, 18),
        nota=None if linhas else "Nenhum contrato da semana se enquadrou nos critérios de alerta.")

    # Qualidade dos dados
    q = m["qualidade"]
    aba("Qualidade dos dados", ["Problema encontrado", "Linhas", "O que foi feito"],
        [[r.problema, r.linhas_afetadas, r.decisao] for r in q.itertuples()], {2: "#,##0"}, (42, 10, 60))

    caminho = Path(pasta) / nome_arquivo(m, "xlsx")
    wb.save(caminho)
    return caminho


# ---------------------------------------------------------------- PDF
def exportar_pdf(m, pasta):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    tinta = colors.HexColor("#1D2B3A")
    linha = colors.HexColor("#D9E0E7")
    estilos = getSampleStyleSheet()
    titulo = ParagraphStyle("t", parent=estilos["Title"], textColor=tinta, alignment=0, fontSize=18)
    h2 = ParagraphStyle("h2", parent=estilos["Heading2"], textColor=tinta, fontSize=12.5, spaceBefore=12,
                        keepWithNext=1)
    corpo = ParagraphStyle("c", parent=estilos["Normal"], fontSize=9.5, leading=13)
    nota = ParagraphStyle("n", parent=corpo, fontSize=8, textColor=colors.HexColor("#6B7885"))
    celula = ParagraphStyle("cel", parent=corpo, fontSize=8.5, leading=11)

    def tabela(cabecalho, linhas, larguras, numericas=()):
        dados = [cabecalho] + [[Paragraph(str(v), celula) if i not in numericas else str(v)
                                for i, v in enumerate(l)] for l in linhas]
        tab = Table(dados, colWidths=[w * cm for w in larguras], repeatRows=1)
        estilo = [("BACKGROUND", (0, 0), (-1, 0), tinta), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                  ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                  ("LINEBELOW", (0, 1), (-1, -1), 0.4, linha), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                  ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
        for i in numericas:
            estilo.append(("ALIGN", (i, 0), (i, -1), "RIGHT"))
        tab.setStyle(TableStyle(estilo))
        return tab

    s = m["semana"]
    story = [Paragraph("Funil de crédito — relatório semanal", titulo),
             Paragraph(f"Semana de {data_br(s['inicio'])} a {data_br(s['fim'])}. "
                       f"Base com {inteiro(m['total_propostas_base'])} propostas analisadas.", corpo),
             Paragraph("A semana", h2),
             tabela(["Indicador", "Semana", "Comparação"],
                    [["Propostas novas", inteiro(s["propostas_novas"]),
                      variacao(s["propostas_novas"], s["propostas_novas_media_ant"])],
                     ["Contratos assinados", inteiro(s["contratos_assinados"]),
                      variacao(s["contratos_assinados"], s["contratos_assinados_media_ant"])],
                     ["R$ contratado", moeda(s["rs_contratado"]),
                      variacao(s["rs_contratado"], s["rs_contratado_media_ant"])]],
                    (5, 3.5, 8.5), numericas=(1,))]

    t = m["tendencia"]
    story += [Paragraph("Conversão por mês de entrada", h2),
              tabela(["Mês", "Propostas", "Conversão", "% corresp.", "Situação"],
                     [[r.mes, inteiro(r.propostas), pct(r.contratadas / r.propostas),
                       pct(r.correspondente / r.propostas), r.situacao] for r in t.itertuples()],
                     (3, 3, 3, 3, 5), numericas=(1, 2, 3)),
              Paragraph(f"Meses em maturação ainda têm propostas sem desfecho (até {MATURACAO_DIAS} dias). "
                        "Compare apenas meses completos.", nota)]

    f = m["funil"]
    story += [Paragraph("Onde o funil perde (últimos 6 meses)", h2),
              tabela(["Etapa", "Chegaram", "Pararam aqui", "R$ perdido", "Chance de contratar"],
                     [[r.etapa, inteiro(r.chegaram), inteiro(r.perdidas) if r.perdidas else "-",
                       moeda(r.rs_perdido) if r.rs_perdido else "-", pct(r.chance_contratar)]
                      for r in f.itertuples()],
                     (5, 2.5, 3, 3.5, 3), numericas=(1, 2, 3, 4))]

    c = m["canais"]
    story += [Paragraph("Canais (últimos 6 meses)", h2),
              tabela(["Canal", "Propostas", "Conversão", "R$ contratado"],
                     [[r.canal_origem, inteiro(r.propostas), pct(r.contratadas / r.propostas),
                       moeda(r.rs_contratado)] for r in c.itertuples()],
                     (6, 3.5, 3.5, 4), numericas=(1, 2, 3))]

    a = m["alertas"]
    story.append(Paragraph("Contratos da semana para revisão", h2))
    if a.empty:
        story.append(Paragraph("Nenhum contrato assinado na semana acima do LTV máximo ou com parcela "
                               "maior que a renda declarada.", corpo))
    else:
        story.append(tabela(["Proposta", "Motivo", "Valor", "LTV", "Renda", "Parcela"],
                            [[r.id_proposta, r.motivo, moeda(r.valor_solicitado), pct(r.ltv),
                              moeda(r.renda_mensal_declarada), moeda(r.parcela_sem_juros)]
                             for r in a.itertuples()],
                            (2.5, 5, 2.5, 1.8, 2.5, 2.5), numericas=(2, 3, 4, 5)))

    q = m["qualidade"]
    story += [Paragraph("Qualidade dos dados", h2),
              tabela(["Problema encontrado", "Linhas", "O que foi feito"],
                     [[r.problema, inteiro(r.linhas_afetadas), r.decisao] for r in q.itertuples()],
                     (6.5, 1.8, 8.7), numericas=(1,)),
              Spacer(1, 10),
              Paragraph("Gerado automaticamente por relatorio_semanal.py. Dados sintéticos do desafio.", nota)]

    caminho = Path(pasta) / nome_arquivo(m, "pdf")
    SimpleDocTemplate(str(caminho), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                      topMargin=1.8 * cm, bottomMargin=1.8 * cm,
                      title="Funil de crédito — relatório semanal").build(story)
    return caminho


EXPORTADORES = {"html": exportar_html, "xlsx": exportar_excel, "pdf": exportar_pdf}
