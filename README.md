# Desafio Prático — Estágio AI & Data Lab | Bari

**Para a liderança comercial:** as conclusões estão em uma página, sem código, no arquivo [`resumo_executivo.pdf`](resumo_executivo.pdf).

---

## Visão geral

| Parte | O que foi feito | Principal resultado | Documentação |
|---|---|---|---|
| **1. Diagnóstico do funil** | Tratamento da base de propostas e análise de onde o funil perde valor | Queda de conversão **não confirmada**; problema dos correspondentes **confirmado** (qualidade, não volume); 3 recomendações com impacto estimado | [`relatorio_parte1.md`](relatorio_parte1.md) e [`registro_tratamento.md`](registro_tratamento.md) |
| **2. Automação** | Relatório semanal do funil gerado automaticamente em HTML, Excel e PDF | Dois cliques para gerar; 11/11 cenários de arquivo problemático tratados corretamente | [`relatorio_parte2.md`](relatorio_parte2.md) |
| **3. Extração com IA** | Extração estruturada dos 17 laudos de avaliação com o Gemini | **99,4% de acerto e 0 valores inventados** em 323 células | [`parte 3/relatorio_parte3.md`](parte%203/relatorio_parte3.md) |
| **4. Diário de bordo** | Uso de IA, aprendizado e autocrítica | — | [`DIARIO.md`](DIARIO.md) |

A base de propostas veio direto da extração, com problemas típicos de sistema transacional: canais escritos de formas diferentes, valores com "R$", datas em dois formatos, uma etapa de funil que não existe, um cliente de 14 anos e uma coluna do dicionário (LTV) que nem veio no arquivo. Resolver esses problemas foi o primeiro passo do desafio, e cada decisão de limpeza está registrada, com o número de linhas afetadas e a justificativa, em [`registro_tratamento.md`](registro_tratamento.md). O mesmo tratamento é reaproveitado pela automação da Parte 2, então as correções acontecem sozinhas a cada execução.

---

## Estrutura de pastas

```
case_bari/
├── README.md                    este arquivo
├── resumo_executivo.pdf         conclusões para a liderança (1 página)
├── DIARIO.md                    Parte 4: diário de bordo
│
├── dados/
│   └── propostas_credito.csv    base original de propostas
│
├── tratamento.py                Partes 1 e 2: leitura e limpeza da base
├── analise_parte1.py            Parte 1: as 4 perguntas do diagnóstico
├── registro_tratamento.md       Parte 1: problemas encontrados e decisões (gerado pelo tratamento.py)
├── relatorio_parte1.md          Parte 1: respostas e recomendações
│
├── relatorio_semanal.py         Parte 2: script principal da automação
├── metricas_semanais.py         Parte 2: cálculo das métricas
├── exportadores.py              Parte 2: geração do HTML, Excel e PDF
├── testes_parte2.py             Parte 2: testes com arquivos problemáticos
├── instalar.bat                 Parte 2: instalação em dois cliques
├── rodar_relatorio.bat          Parte 2: relatório em dois cliques
├── relatorio_parte2.md          Parte 2: documentação
├── exemplos/                    Parte 2: relatórios gerados na minha máquina (semana de 23 a 29/06/2025)
│
├── parte 3/
│   ├── extrator_laudos.py       extração com IA e validação
│   ├── avaliar_extracao.py      comparação com o gabarito
│   ├── gabarito_laudos.xlsx     gabarito preenchido à mão
│   ├── laudos/                  os 17 laudos originais
│   ├── respostas_ia/            respostas da IA usadas na entrega
│   ├── respostas_ia_gemini-3.8-flash/   primeira tentativa com outro modelo (9 laudos)
│   ├── relatorio_avaliacao.md   resultado da avaliação gerado na minha máquina (99,4% de acerto)
│   └── relatorio_parte3.md      documentação
│
├── requirements.txt             bibliotecas e versões testadas
└── .gitignore                   impede o envio da chave de API e dos arquivos gerados
```

### O que o `.gitignore` deixa de fora (e por quê)

O `.gitignore` lista o que **nunca** deve ir para o repositório:

| Item | Por que fica de fora |
|---|---|
| `.env` | Guarda a minha chave da API do Gemini. Se fosse publicada, qualquer pessoa poderia usá-la. O código não contém a chave: ele só a lê do `.env` na hora de rodar, então cada pessoa usa a sua |
| `saida/` e `logs/` | São resultados gerados pelo próprio código, recriados a cada execução. Para ver resultados sem rodar nada, existem a pasta `exemplos/` e o arquivo `parte 3/relatorio_avaliacao.md` |
| `__pycache__/` | Arquivos temporários que o Python cria sozinho |

---

## Como rodar

### Requisitos

- **Python 3** (testado com Python 3.14, no Windows)
- As bibliotecas do `requirements.txt`, com as versões fixadas para evitar diferenças entre computadores

Instalação, só na primeira vez: dois cliques em `instalar.bat`, ou pelo terminal:

```
python -m pip install -r requirements.txt
```

> **Se o Windows bloquear os arquivos `.bat`**, o que é comum quando são baixados da internet: botão direito no arquivo → Propriedades → marcar "Desbloquear". Ou use os comandos de terminal indicados em cada parte.

### Parte 1: diagnóstico

Na pasta principal:

```
python tratamento.py          gera o registro_tratamento.md
python analise_parte1.py      mostra as respostas das 4 perguntas no terminal
```

### Parte 2: relatório semanal

Dois cliques em `rodar_relatorio.bat`, ou:

```
python relatorio_semanal.py
python relatorio_semanal.py --data-corte 2025-06-29     relatório de uma semana específica
python testes_parte2.py                                 testes com arquivos problemáticos
```

Os relatórios aparecem na pasta `saida/`, e o registro da execução em `logs/`. O passo a passo para agendar a execução toda segunda-feira está em [`relatorio_parte2.md`](relatorio_parte2.md).

### Parte 3: extração dos laudos

Na pasta `parte 3` (as aspas são necessárias por causa do espaço no nome):

```
cd "parte 3"
python extrator_laudos.py
python avaliar_extracao.py
```

Para ver o resultado sem rodar nada: [`parte 3/relatorio_avaliacao.md`](parte%203/relatorio_avaliacao.md).

**Não é preciso chave de API para reproduzir o resultado:** as respostas da IA estão salvas em `respostas_ia/`, e o extrator só as valida. Para chamar a IA de novo, é preciso uma chave gratuita do Google AI Studio num arquivo `.env` na pasta principal, com a linha `GEMINI_API_KEY=sua_chave`, e rodar `python extrator_laudos.py --refazer --lote 17`.

---

## Quanto tempo levei

| Etapa | Tempo |
|---|---|
| Leitura do enunciado e entendimento do problema | cerca de 2h |
| Parte 1: tratamento e diagnóstico | cerca de 3h |
| Parte 2: automação | cerca de 3h |
| Parte 3: gabarito, extração e avaliação | cerca de 3h |
| Diário, resumo executivo e README | cerca de 2h |
| **Total** | **cerca de 13h** |

---

## Uso de IA

Usei IA durante todo o desafio, como o enunciado permite. Foram três usos diferentes:

| Ferramenta | Para quê |
|---|---|
| **Claude (Anthropic)**, como assistente | Entender o enunciado, explorar a base, escrever e corrigir o código das três partes, explicar conceitos que eu não conhecia (pandas, testes estatísticos, códigos de saída, entre outros) e redigir a primeira versão dos relatórios, do resumo executivo e deste README a partir das minhas decisões. Revisei e ajustei os textos, e todas as decisões de negócio e de tratamento foram minhas |
| **Gemini (Google), via API** | Parte da solução da Parte 3: extração dos campos dos laudos (modelo `gemini-3.5-flash-lite`) |
| **IA do buscador do Google (Gemini)** | Pesquisa de conceitos para o gabarito da Parte 3 (penhora cancelada; área útil e área privativa) |

O registro de onde a IA ajudou, onde errou e onde discordei dela está no [`DIARIO.md`](DIARIO.md).

## Fontes externas

- **Dados:** somente os materiais fornecidos no desafio (dados sintéticos).
- **Bibliotecas:** pandas, SciPy, openpyxl e ReportLab.
- **API de IA:** Google Gemini, via Google AI Studio (aistudio.google.com), plano gratuito.
- **Conceitos pesquisados** (penhora cancelada; área útil e área privativa): pesquisa no Google, com as respostas geradas pela IA do próprio buscador (Gemini). Não consultei uma fonte primária, como legislação ou norma técnica (ver limitação no [`DIARIO.md`](DIARIO.md)).