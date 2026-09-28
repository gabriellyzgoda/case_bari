"""
relatorio_semanal.py — Gera o relatório semanal do funil (Parte 2).

Fluxo: lê o arquivo bruto -> aplica o tratamento -> calcula as métricas -> exporta HTML, Excel e PDF.

Uso:
    python relatorio_semanal.py
    python relatorio_semanal.py --entrada dados/outro_arquivo.csv
    python relatorio_semanal.py --data-corte 2025-06-29      (semana que termina nesse dia)
    python relatorio_semanal.py --formatos html,xlsx          (só alguns formatos)

Códigos de saída (úteis para o agendador do Windows saber se deu certo):
    0 = tudo gerado | 1 = algum formato falhou | 2 = problema no arquivo de entrada | 3 = erro inesperado
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from exportadores import EXPORTADORES
from metricas_semanais import calcular
from tratamento import ErroEstrutura, carregar_e_tratar

PASTA = Path(__file__).resolve().parent
log = logging.getLogger("relatorio")


def configurar_log(pasta_logs):
    """Log no terminal e num arquivo por execução (logs/relatorio_AAAA-MM-DD_HHMMSS.log)."""
    pasta_logs.mkdir(parents=True, exist_ok=True)
    arquivo = pasta_logs / f"relatorio_{datetime.now():%Y-%m-%d_%H%M%S}.log"
    formato = logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s", "%Y-%m-%d %H:%M:%S")
    raiz = logging.getLogger()
    raiz.handlers.clear()
    raiz.setLevel(logging.INFO)
    for handler in (logging.FileHandler(arquivo, encoding="utf-8"), logging.StreamHandler(sys.stdout)):
        handler.setFormatter(formato)
        raiz.addHandler(handler)
    return arquivo


def main(argv=None):
    parser = argparse.ArgumentParser(description="Gera o relatório semanal do funil de crédito.")
    parser.add_argument("--entrada", default=str(PASTA / "dados" / "propostas_credito.csv"))
    parser.add_argument("--saida", default=str(PASTA / "saida"))
    parser.add_argument("--logs", default=str(PASTA / "logs"))
    parser.add_argument("--data-corte", default=None, help="último dia da semana (AAAA-MM-DD)")
    parser.add_argument("--formatos", default="html,xlsx,pdf")
    args = parser.parse_args(argv)

    arquivo_log = configurar_log(Path(args.logs))
    log.info("=== Início da execução ===")
    log.info("Entrada: %s", args.entrada)

    # 1. Leitura e tratamento: se falhar aqui, não há relatório possível.
    try:
        df, registro = carregar_e_tratar(args.entrada)
    except FileNotFoundError as e:
        log.error("%s. Confira se o arquivo foi salvo na pasta 'dados' com o nome certo.", e)
        return 2
    except ErroEstrutura as e:
        log.error("Arquivo de entrada com problema: %s. O relatório NÃO foi gerado.", e)
        return 2
    except Exception:
        log.exception("Erro inesperado ao ler/tratar o arquivo. O relatório NÃO foi gerado.")
        return 3

    # 2. Métricas
    try:
        metricas = calcular(df, registro, args.data_corte)
    except Exception:
        log.exception("Erro inesperado ao calcular as métricas. O relatório NÃO foi gerado.")
        return 3
    s = metricas["semana"]
    log.info("Semana do relatório: %s a %s | %d propostas novas | %d contratos assinados",
             f"{s['inicio']:%d/%m/%Y}", f"{s['fim']:%d/%m/%Y}", s["propostas_novas"], s["contratos_assinados"])
    if s["propostas_novas"] == 0:
        log.warning("Nenhuma proposta nova na semana: confira se o arquivo é o mais recente.")
    if not metricas["alertas"].empty:
        log.warning("%d contrato(s) da semana marcado(s) para revisão.", len(metricas["alertas"]))

    # 3. Exportação: cada formato é independente; a falha de um não impede os outros.
    pasta_saida = Path(args.saida)
    pasta_saida.mkdir(parents=True, exist_ok=True)
    gerados, falhas = [], []
    for formato in [f.strip().lower() for f in args.formatos.split(",") if f.strip()]:
        exportar = EXPORTADORES.get(formato)
        if exportar is None:
            log.error("Formato desconhecido: '%s' (use html, xlsx ou pdf)", formato)
            falhas.append(formato)
            continue
        try:
            caminho = exportar(metricas, pasta_saida)
            log.info("Gerado: %s", caminho)
            gerados.append(caminho)
        except ModuleNotFoundError as e:
            log.error("Formato %s não gerado: biblioteca '%s' não instalada. Rode instalar.bat.", formato, e.name)
            falhas.append(formato)
        except Exception:
            log.exception("Formato %s não gerado por erro inesperado.", formato)
            falhas.append(formato)

    log.info("=== Fim: %d arquivo(s) gerado(s), %d falha(s). Log: %s ===", len(gerados), len(falhas), arquivo_log)
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
