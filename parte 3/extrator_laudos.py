"""
extrator_laudos.py — Parte 3: extrai campos estruturados dos laudos de avaliação usando IA (Gemini).

Rodar (na pasta parte3):
    python extrator_laudos.py              usa as respostas já salvas em respostas_ia/ quando existirem
    python extrator_laudos.py --lote 8     envia até 8 laudos por requisição (economiza a cota gratuita)
    python extrator_laudos.py --refazer    chama a IA de novo para todos os laudos (precisa da chave)
    python extrator_laudos.py --listar-modelos   mostra os modelos que a chave pode usar

Como a saída sai sempre no mesmo formato:
  1. A IA é obrigada a responder num esquema JSON fixo (response schema da API): mesmos campos,
     mesmos tipos, e o ônus só pode ser uma de três opções.
  2. O código valida de novo cada campo (tipo, formato de data, UF...).

Como o extrator evita "chutar":
  - Para cada campo, a IA precisa citar o trecho exato do laudo de onde tirou o valor (evidência).
  - O código confere se esse trecho existe de verdade no laudo e se o valor bate com ele.
    Se não bater, o valor é DESCARTADO (fica vazio) e o motivo vai para a coluna 'alertas'.
    Preferimos "não sei" a um valor plausível inventado.

As respostas brutas da IA ficam salvas em respostas_ia/, para que qualquer pessoa consiga
reproduzir a validação e a avaliação sem precisar de chave de API.
"""

import argparse
import json
import logging
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

import pandas as pd

PASTA = Path(__file__).resolve().parent
PASTA_LAUDOS = PASTA / "laudos"
PASTA_RESPOSTAS = PASTA / "respostas_ia"
PASTA_SAIDA = PASTA / "saida"
MODELO_PADRAO = "gemini-3.5-flash-lite"  # usado na entrega; 2.5-flash desativado e 3.8-flash sem cota gratuita
VERSAO_PROMPT = "v1"
ONUS_OPCOES = ["sem ônus", "com ônus", "não confirmado"]

log = logging.getLogger("extrator")

# ------------------------------------------------------------------ campos
# (nome, tipo, descrição usada no prompt)
CAMPOS = [
    ("tipo_imovel", "texto", "tipo do imóvel, como escrito no laudo"),
    ("endereco", "texto", "logradouro, número, complemento e bairro, sem cidade e UF"),
    ("cidade", "texto", "cidade do imóvel"),
    ("uf", "texto", "sigla do estado com 2 letras"),
    ("area_privativa_m2", "numero", "área privativa em m²"),
    ("area_util_m2", "numero", "área útil em m² (NÃO é a mesma coisa que área privativa)"),
    ("area_construida_m2", "numero", "área construída/edificada em m² (inclui benfeitorias construídas e área coberta de galpão)"),
    ("area_terreno_m2", "numero", "área do terreno/lote/superfície em m²; hectares convertidos (1 ha = 10.000 m²)"),
    ("area_total_m2", "numero", "área total em m²"),
    ("ano_construcao", "inteiro", "ano de construção, SOMENTE se escrito explicitamente como ano de construção"),
    ("idade_informada", "texto", "quando o laudo dá idade ou ano ambíguo em vez do ano de construção, o texto como está"),
    ("valor_avaliacao", "numero", "valor de avaliação em reais"),
    ("matricula", "texto", "número da matrícula / registro imobiliário do imóvel"),
    ("onus_situacao", "onus", "situação dos ônus/gravames"),
    ("onus_descricao", "texto", "resumo do que o laudo diz sobre ônus"),
    ("data_vistoria", "data", "data da vistoria/inspeção no formato AAAA-MM-DD"),
    ("responsavel_tecnico", "texto", "nome do responsável técnico, sem título (Eng., Arq.)"),
    ("registro_profissional", "texto", "conselho e número de registro (ex.: CREA-SP 123)"),
    ("contradicoes", "texto", "descrição de informações conflitantes dentro do laudo"),
]
NOMES = [c[0] for c in CAMPOS]

INSTRUCOES = """Você extrai dados de laudos de avaliação de imóveis escritos em português do Brasil.
Responda SOMENTE no formato JSON pedido. Para cada campo, devolva:
  - "valor": o dado extraído, ou null se o laudo não traz a informação;
  - "evidencia": o trecho EXATO do laudo, copiado letra por letra, de onde o valor saiu (null se o valor for null).

Regras obrigatórias:
1. NUNCA invente nem estime. Se a informação não está escrita no laudo, o valor é null. Um valor plausível inventado é o pior erro possível.
2. Números: use ponto como separador decimal e nenhum separador de milhar (ex.: "R$ 1.275.000,00" -> 1275000; "78,40 m²" -> 78.4).
3. Hectares viram m² (1 ha = 10.000 m²). Essa é a única conversão permitida.
4. ano_construcao: só quando o laudo diz explicitamente o ano de construção/conclusão/edificação. Se o laudo dá uma idade ("11 anos", "aproximadamente 18 anos") ou um "ano de referência", ano_construcao = null e o texto vai em idade_informada. Nunca calcule ano a partir de idade.
5. Área útil vai em area_util_m2, nunca em area_privativa_m2. Área de lote/terreno/superfície vai em area_terreno_m2, nunca em area_total_m2. Não some áreas.
6. onus_situacao:
   - "sem ônus": só quando o laudo CONFIRMA a ausência com base em certidão/matrícula (ex.: certidão sem ônus, sem gravames). Penhora CANCELADA conta como "sem ônus".
   - "com ônus": quando o laudo aponta ônus/gravame/restrição registrada (hipoteca, penhora ativa, alienação fiduciária, servidão, reserva legal...).
   - "não confirmado": quando o laudo não informa, não verificou, não tem certidão, ou só tem declaração do proprietário.
7. Contradições: se o laudo traz dois valores diferentes para o mesmo dado, deixe esse campo como null e descreva os dois valores em "contradicoes". Não escolha um dos dois.
8. data_vistoria no formato AAAA-MM-DD."""


def esquema_resposta():
    """Esquema JSON imposto à IA (formato OpenAPI aceito pela API do Gemini)."""
    tipos = {"texto": "STRING", "numero": "NUMBER", "inteiro": "INTEGER", "data": "STRING"}
    props = {}
    for nome, tipo, desc in CAMPOS:
        if tipo == "onus":
            valor = {"type": "STRING", "enum": ONUS_OPCOES, "description": desc}
        else:
            valor = {"type": tipos[tipo], "nullable": True, "description": desc}
        props[nome] = {"type": "OBJECT",
                       "properties": {"valor": valor, "evidencia": {"type": "STRING", "nullable": True}},
                       "required": ["valor", "evidencia"]}
    return {"type": "OBJECT", "properties": props, "required": NOMES, "propertyOrdering": NOMES}


def esquema_lote():
    """Esquema para vários laudos numa requisição: uma lista, um item por laudo."""
    base = esquema_resposta()
    item = {"type": "OBJECT",
            "properties": {"arquivo": {"type": "STRING"}, **base["properties"]},
            "required": ["arquivo"] + NOMES, "propertyOrdering": ["arquivo"] + NOMES}
    return {"type": "OBJECT", "properties": {"laudos": {"type": "ARRAY", "items": item}}, "required": ["laudos"]}


# ------------------------------------------------------------------ chave
def carregar_chave():
    """Lê GEMINI_API_KEY do ambiente ou de um arquivo .env (nesta pasta ou na pasta acima)."""
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"].strip()
    for pasta in (PASTA, PASTA.parent):
        env = pasta / ".env"
        if env.exists():
            for linha in env.read_text(encoding="utf-8-sig").splitlines():
                if linha.strip().startswith("GEMINI_API_KEY="):
                    return linha.split("=", 1)[1].strip().strip('"').strip("'")
    return None


# ------------------------------------------------------------------ chamada à IA
class ErroIA(Exception):
    pass


def listar_modelos(chave):
    """Mostra os modelos que a chave consegue usar para gerar texto."""
    url = "https://generativelanguage.googleapis.com/v1beta/models?pageSize=200"
    req = urllib.request.Request(url, headers={"x-goog-api-key": chave})
    with urllib.request.urlopen(req, timeout=60) as resp:
        modelos = json.loads(resp.read().decode("utf-8")).get("models", [])
    for m in modelos:
        if "generateContent" in m.get("supportedGenerationMethods", []):
            print(m["name"].replace("models/", ""))


class CotaEsgotada(ErroIA):
    pass


def chamar_gemini(texto_usuario, chave, modelo, esquema=None, tentativas=4):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
    corpo = {
        "systemInstruction": {"parts": [{"text": INSTRUCOES}]},
        "contents": [{"role": "user", "parts": [{"text": texto_usuario}]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 32768,
                             "responseMimeType": "application/json",
                             "responseSchema": esquema or esquema_resposta()},
    }
    dados = json.dumps(corpo).encode("utf-8")
    for tentativa in range(1, tentativas + 1):
        req = urllib.request.Request(url, data=dados, method="POST",
                                     headers={"Content-Type": "application/json", "x-goog-api-key": chave})
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                resposta = json.loads(resp.read().decode("utf-8"))
            partes = resposta["candidates"][0]["content"]["parts"]
            texto = "".join(p.get("text", "") for p in partes if not p.get("thought"))
            return json.loads(texto)
        except urllib.error.HTTPError as e:
            detalhe = e.read().decode("utf-8", errors="ignore")
            if e.code == 429 and re.search(r"PerDay|per day|daily", detalhe, re.IGNORECASE):
                raise CotaEsgotada(f"Cota DIÁRIA do modelo '{modelo}' esgotada no plano gratuito. "
                                   "Tente amanhã, ou use outro modelo (--listar-modelos / --modelo), "
                                   "ou envie vários laudos por requisição (--lote).")
            if e.code == 429 or e.code >= 500:
                espera = 15 * tentativa
                log.warning("API respondeu %s (limite de uso ou instabilidade). Nova tentativa em %ss.", e.code, espera)
                time.sleep(espera)
                continue
            if e.code in (400, 401, 403):
                raise ErroIA(f"A API recusou a requisição ({e.code}). Confira a chave no .env. Detalhe: {detalhe[:300]}")
            if e.code == 404:
                raise ErroIA(f"Modelo '{modelo}' não encontrado. Use --listar-modelos para ver as opções. "
                             f"Detalhe: {detalhe[:300]}")
            raise ErroIA(f"Erro HTTP {e.code}: {detalhe[:300]}")
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            log.warning("Resposta fora do formato esperado (%s). Nova tentativa.", e)
            time.sleep(3)
        except urllib.error.URLError as e:
            raise ErroIA(f"Sem conexão com a API do Gemini (confira a internet): {e.reason}")
    raise ErroIA(f"Sem resposta válida depois de {tentativas} tentativas.")


def extrair_em_lote(arquivos, chave, modelo):
    """Envia vários laudos numa única requisição e devolve {nome_do_arquivo: resposta}."""
    blocos = [f"=== ARQUIVO: {a.name} ===\n{a.read_text(encoding='utf-8-sig')}" for a in arquivos]
    texto = ("A seguir há vários laudos DIFERENTES, cada um começando com '=== ARQUIVO: nome ==='. "
             "Extraia cada laudo separadamente e devolva um item por arquivo, com o nome exato em 'arquivo'. "
             "NUNCA use informação de um laudo em outro: cada evidência deve vir do próprio laudo.\n\n"
             + "\n\n".join(blocos))
    resposta = chamar_gemini(texto, chave, modelo, esquema=esquema_lote())
    return {item.get("arquivo"): {k: v for k, v in item.items() if k != "arquivo"}
            for item in resposta.get("laudos", [])}


# ------------------------------------------------------------------ validação
MESES = {"janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5, "junho": 6, "julho": 7,
         "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12}


def simplificar(t):
    """Minúsculas, sem acento e com espaços normalizados, para comparar textos."""
    t = unicodedata.normalize("NFKD", str(t)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", t).strip()


def sem_pontuacao(t):
    """Texto simplificado sem pontuação: usado para conferir se a evidência existe no laudo.
    Palavras e números precisam ser idênticos; vírgula x ponto e vírgula não descarta um acerto."""
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", simplificar(t))).strip()


def so_alfanumerico(t):
    return re.sub(r"[^a-z0-9]", "", simplificar(t))


def numeros_do_texto(t):
    """Todos os números escritos no trecho, entendendo o formato brasileiro (1.275.000,00 e 78,40)."""
    achados = []
    for bruto in re.findall(r"\d[\d.,]*\d|\d", t):
        s = bruto
        if "," in s:
            s = s.replace(".", "").replace(",", ".")
        elif re.fullmatch(r"\d{1,3}(\.\d{3})+", s):
            s = s.replace(".", "")
        try:
            achados.append(float(s))
        except ValueError:
            pass
    if re.search(r"\bha\b|hectare", simplificar(t)):
        achados += [n * 10000 for n in achados]
    return achados


def datas_do_texto(t):
    s = simplificar(t)
    datas = {f"{a}-{int(m):02d}-{int(d):02d}" for d, m, a in re.findall(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", s)}
    for d, mes, a in re.findall(r"(\d{1,2}) de ([a-z]+) de (\d{4})", s):
        if mes in MESES:
            datas.add(f"{a}-{MESES[mes]:02d}-{int(d):02d}")
    return datas


def validar(resposta, texto_laudo):
    """Confere formato e evidência de cada campo. Valores sem sustentação no laudo são descartados.
    Devolve (valores, alertas)."""
    laudo = sem_pontuacao(texto_laudo)
    valores, alertas = {}, []
    for nome, tipo, _ in CAMPOS:
        item = resposta.get(nome)
        if not isinstance(item, dict):
            alertas.append(f"{nome}: campo ausente na resposta da IA")
            valores[nome] = "não confirmado" if tipo == "onus" else None
            continue
        valor, evidencia = item.get("valor"), item.get("evidencia")
        if valor in ("", "null", "None"):
            valor = None

        # 1) formato
        if valor is not None:
            if tipo in ("numero", "inteiro") and not isinstance(valor, (int, float)):
                alertas.append(f"{nome}: valor '{valor}' não é número; descartado")
                valor = None
            elif tipo == "data" and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(valor)):
                alertas.append(f"{nome}: data '{valor}' fora do formato AAAA-MM-DD; descartada")
                valor = None
            elif tipo == "onus" and valor not in ONUS_OPCOES:
                alertas.append(f"{nome}: opção inválida '{valor}'; trocado por 'não confirmado'")
                valor = "não confirmado"
            elif nome == "uf" and not re.fullmatch(r"[A-Z]{2}", str(valor)):
                alertas.append(f"uf: '{valor}' não é sigla de estado; descartado")
                valor = None

        # 2) evidência: o trecho citado precisa existir no laudo
        precisa_evidencia = valor is not None and not (tipo == "onus" and valor == "não confirmado")
        if precisa_evidencia:
            if not evidencia or sem_pontuacao(evidencia) not in laudo:
                alertas.append(f"{nome}: trecho citado pela IA não existe no laudo; valor '{valor}' descartado")
                valor = "não confirmado" if tipo == "onus" else None
            # 3) o valor precisa bater com o trecho citado
            elif tipo in ("numero", "inteiro") and not any(abs(n - float(valor)) < 0.01 for n in numeros_do_texto(evidencia)):
                alertas.append(f"{nome}: valor {valor} não aparece no trecho citado; descartado")
                valor = None
            elif tipo == "data" and valor not in datas_do_texto(evidencia):
                alertas.append(f"{nome}: data {valor} não confere com o trecho citado; descartada")
                valor = None
            elif nome in ("cidade", "uf", "matricula", "responsavel_tecnico", "registro_profissional") \
                    and so_alfanumerico(valor) not in so_alfanumerico(evidencia):
                alertas.append(f"{nome}: valor '{valor}' não aparece no trecho citado; descartado")
                valor = None

        # 4) trava para o erro mais caro: declarar o imóvel livre sem confirmação.
        #    "sem ônus" com um trecho que indica falta de informação vira "não confirmado".
        if nome == "onus_situacao" and valor == "sem ônus" and evidencia and re.search(
                r"nao consta|nao informad|sem informacao|nao ha mencao|nao foi possivel|"
                r"declaracao do proprietario|nao anexad|nada informado", simplificar(evidencia)):
            alertas.append("onus_situacao: 'sem ônus' sem confirmação por certidão; trocado por 'não confirmado'")
            valor = "não confirmado"

        if nome == "contradicoes" and valor:
            alertas.append(f"CONTRADIÇÃO NO LAUDO: {valor}")
        valores[nome] = valor
    return valores, alertas


# ------------------------------------------------------------------ execução
def main(argv=None):
    parser = argparse.ArgumentParser(description="Extrai campos estruturados dos laudos com IA.")
    parser.add_argument("--refazer", action="store_true", help="chamar a IA de novo mesmo com respostas salvas")
    parser.add_argument("--modelo", default=os.environ.get("GEMINI_MODEL", MODELO_PADRAO))
    parser.add_argument("--laudos", default=str(PASTA_LAUDOS))
    parser.add_argument("--listar-modelos", action="store_true", help="mostra os modelos disponíveis para a chave")
    parser.add_argument("--lote", type=int, default=1,
                        help="quantos laudos enviar por requisição (ex.: --lote 8). Economiza a cota do plano gratuito")
    args = parser.parse_args(argv)

    if args.listar_modelos:
        chave = carregar_chave()
        if not chave:
            print("Chave não encontrada no .env")
            return 2
        listar_modelos(chave)
        return 0

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s",
                        datefmt="%H:%M:%S", handlers=[logging.StreamHandler(sys.stdout)])
    arquivos = sorted(Path(args.laudos).glob("*.txt"))
    if not arquivos:
        log.error("Nenhum laudo .txt encontrado em %s", args.laudos)
        return 2
    PASTA_RESPOSTAS.mkdir(exist_ok=True)
    PASTA_SAIDA.mkdir(exist_ok=True)

    def salvar(arq, resposta, modo):
        registro = {"arquivo": arq.name, "modelo": args.modelo, "versao_prompt": VERSAO_PROMPT, "modo": modo,
                    "data": f"{datetime.now():%Y-%m-%d %H:%M}", "resposta": resposta}
        (PASTA_RESPOSTAS / f"{arq.stem}.json").write_text(json.dumps(registro, ensure_ascii=False, indent=2),
                                                         encoding="utf-8")
        log.info("%s: extraído pela IA (%s) e salvo em respostas_ia/", arq.name, modo)

    # 1. Quais laudos ainda precisam da IA
    pendentes = [a for a in arquivos if args.refazer or not (PASTA_RESPOSTAS / f"{a.stem}.json").exists()]
    log.info("%d laudo(s) com resposta salva | %d para enviar à IA | modo: %s",
             len(arquivos) - len(pendentes), len(pendentes),
             f"lotes de {args.lote}" if args.lote > 1 else "um laudo por requisição")

    # 2. Chamadas à IA (uma por laudo ou em lotes)
    codigo_saida = 0
    chave = carregar_chave() if pendentes else None
    if pendentes and not chave:
        log.error("Chave não encontrada: %d laudo(s) não serão extraídos. Crie o arquivo .env com "
                  "GEMINI_API_KEY=sua_chave. Os laudos com resposta salva serão validados normalmente.", len(pendentes))
        codigo_saida = 2
    if pendentes and chave:
        grupos = [pendentes[i:i + args.lote] for i in range(0, len(pendentes), max(args.lote, 1))]
        for n, grupo in enumerate(grupos):
            if n > 0:
                time.sleep(7)  # respeita o limite de requisições por minuto do plano gratuito
            try:
                if len(grupo) == 1:
                    texto = grupo[0].read_text(encoding="utf-8-sig")
                    salvar(grupo[0], chamar_gemini(f"LAUDO:\n{texto}", chave, args.modelo), "individual")
                else:
                    respostas = extrair_em_lote(grupo, chave, args.modelo)
                    for arq in grupo:
                        if arq.name in respostas:
                            salvar(arq, respostas[arq.name], f"lote de {len(grupo)}")
                        else:
                            log.error("%s: a IA não devolveu este laudo no lote; rode de novo para tentar outra vez.",
                                      arq.name)
                            codigo_saida = 3
            except ErroIA as e:
                log.error("%s", e)
                log.error("Os laudos já extraídos ficaram salvos em respostas_ia/. "
                          "Rode de novo mais tarde: o programa continua de onde parou.")
                codigo_saida = 3
                break

    # 3. Validação de todos os laudos com resposta salva
    linhas = []
    for arq in arquivos:
        salvo = PASTA_RESPOSTAS / f"{arq.stem}.json"
        if not salvo.exists():
            linhas.append({"arquivo": arq.name, **{c: None for c in NOMES},
                           "alertas": "laudo ainda não extraído pela IA"})
            continue
        registro = json.loads(salvo.read_text(encoding="utf-8"))
        valores, alertas = validar(registro["resposta"], arq.read_text(encoding="utf-8-sig"))
        for a in alertas:
            log.warning("%s | %s", arq.name, a)
        linhas.append({"arquivo": arq.name, **valores, "alertas": " | ".join(alertas)})

    tabela = pd.DataFrame(linhas)
    tabela.to_csv(PASTA_SAIDA / "extracao_laudos.csv", index=False, encoding="utf-8-sig")
    tabela.to_excel(PASTA_SAIDA / "extracao_laudos.xlsx", index=False)
    faltando = tabela["alertas"].str.contains("ainda não extraído").sum()
    log.info("Extração concluída: %d laudos | %d com alertas | %d ainda sem extração | saída em saida/extracao_laudos.xlsx",
             len(tabela), (tabela["alertas"] != "").sum(), faltando)
    return codigo_saida


if __name__ == "__main__":
    sys.exit(main())