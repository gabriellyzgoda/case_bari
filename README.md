# Desafio Prático — Estágio AI & Data Lab | Bari

**Para a liderança comercial:** as conclusões estão em uma página, sem código, no arquivo [`resumo_executivo.pdf`](resumo_executivo.pdf).

---

## Visão geral

| Parte | O que foi feito | Principal resultado | Documentação |
|---|---|---|---|
| **1. Diagnóstico do funil** | Tratamento da base de propostas e análise de onde o funil perde valor | Queda de conversão **não confirmada**; problema dos correspondentes **confirmado** (qualidade, não volume); 3 recomendações com impacto estimado | [`parte 1/relatorio_parte1.md`](parte%201/relatorio_parte1.md) e [`parte 1/registro_tratamento.md`](parte%201/registro_tratamento.md) |
| **2. Automação** | Relatório semanal do funil gerado automaticamente em HTML, Excel e PDF | Dois cliques para gerar; 11/11 cenários de arquivo problemático tratados corretamente | [`parte 2/relatorio_parte2.md`](parte%202/relatorio_parte2.md) |
| **3. Extração com IA** | Extração estruturada dos 17 laudos de avaliação com o Gemini | **99,4% de acerto e 0 valores inventados** em 323 células | [`parte 3/relatorio_parte3.md`](parte%203/relatorio_parte3.md) |
| **4. Diário de bordo** | Uso de IA, aprendizado e autocrítica | — | [`DIARIO.md`](DIARIO.md) |

A base de propostas veio direto da extração, com problemas típicos de sistema transacional: canais escritos de formas diferentes, valores com "R$", datas em dois formatos, uma etapa de funil que não existe, um cliente de 14 anos e uma coluna do dicionário (LTV) que nem veio no arquivo. Resolver esses problemas foi o primeiro passo do desafio, e cada decisão de limpeza está registrada, com o número de linhas afetadas e a justificativa, em [`parte 1/registro_tratamento.md`](parte%201/registro_tratamento.md). O mesmo tratamento é reaproveitado pela automação da Parte 2, então as correções acontecem sozinhas a cada execução.

---

## Estrutura de pastas

```
case_bari/
├── README.md                    este arquivo
├── resumo_executivo.pdf         conclusões para a liderança (1 página)
├── DIARIO.md                    Parte 4: diário de bordo
├── tratamento.py                leitura e limpeza da base, compartilhado pelas Partes 1 e 2
├── requirements.txt             bibliotecas e versões testadas (projeto todo)
├── .gitignore                   impede o envio da chave de API e dos arquivos gerados
│
├── dados/
│   └── propostas_credito.csv    base original de propostas (usada pelas Partes 1 e 2)
│
├── parte 1/
│   ├── analise_parte1.py        as 4 perguntas do diagnóstico
│   ├── registro_tratamento.md   problemas encontrados e decisões (gerado pelo código)
│   └── relatorio_parte1.md      respostas e recomendações
│
├── parte 2/
│   ├── relatorio_semanal.py     script principal da automação
│   ├── metricas_semanais.py     cálculo das métricas
│   ├── exportadores.py          geração do HTML, Excel e PDF
│   ├── testes_parte2.py         testes com arquivos problemáticos
│   ├── instalar.bat             instalação em dois cliques
│   ├── rodar_relatorio.bat      relatório em dois cliques
│   ├── exemplos/                relatórios gerados na minha máquina (semana de 23 a 29/06/2025)
│   └── relatorio_parte2.md      documentação
│
└── parte 3/
    ├── extrator_laudos.py       extração com IA e validação
    ├── avaliar_extracao.py      comparação com o gabarito
    ├── gabarito_laudos.xlsx     gabarito preenchido à mão
    ├── laudos/                  os 17 laudos originais
    ├── respostas_ia/            respostas da IA usadas na entrega
    ├── respostas_ia_gemini-3.8-flash/   primeira tentativa com outro modelo (9 laudos)
    ├── relatorio_avaliacao.md   resultado da avaliação gerado na minha máquina (99,4% de acerto)
    └── relatorio_parte3.md      documentação
```

**Por que o `tratamento.py` e o `dados/` ficam na pasta principal:** as Partes 1 e 2 usam exatamente o mesmo tratamento e a mesma base. Deixando os dois num lugar só, uma correção no tratamento vale para as duas partes, sem código duplicado.

### O que o `.gitignore` deixa de fora (e por quê)

O `.gitignore` lista o que **nunca** deve ir para o repositório:

| Item | Por que fica de fora |
|---|---|
| `.env` | Guarda a minha chave da API do Gemini. Se fosse publicada, qualquer pessoa poderia usá-la. O código não contém a chave: ele só a lê do `.env` na hora de rodar, então cada pessoa usa a sua |
| `saida/` e `logs/` | São resultados gerados pelo próprio código, recriados a cada execução. Para ver resultados sem rodar nada, existem a pasta `parte 2/exemplos/` e o arquivo `parte 3/relatorio_avaliacao.md` |
| `__pycache__/` | Arquivos temporários que o Python cria sozinho |

---

## Passo a passo: rodando tudo do zero

Siga na ordem. Todos os comandos são digitados num terminal (no VS Code: menu **Terminal → New Terminal**), começando **na pasta principal** do projeto, `case_bari`.

> No Windows, se o comando `python` não for reconhecido, use `py` no lugar (por exemplo, `py analise_parte1.py`).
>
> As aspas em `cd "parte 1"` são necessárias por causa do espaço no nome da pasta. O comando `cd ..` volta para a pasta principal.

### Passo 0: instalar (só na primeira vez)

Requisito: **Python 3** instalado (testado com Python 3.14, no Windows). Depois, na pasta principal:

```
python -m pip install -r requirements.txt
```

Isso instala as bibliotecas nas versões testadas. Quem não usa terminal pode dar dois cliques em `parte 2/instalar.bat`, que faz o mesmo.

### Passo 1: Parte 1, diagnóstico do funil

```
cd "parte 1"
python analise_parte1.py
cd ..
```

**O que deve aparecer:** "Base analisada: 5864 propostas | contratadas: 1128 (19.2%)" e, em seguida, as tabelas das quatro perguntas (P1 a P4). O `parte 1/registro_tratamento.md` é atualizado com os problemas encontrados na base.

**O que ler:** as respostas e recomendações estão explicadas em [`parte 1/relatorio_parte1.md`](parte%201/relatorio_parte1.md).

### Passo 2: Parte 2, relatório semanal

```
cd "parte 2"
python relatorio_semanal.py --data-corte 2025-06-29
python testes_parte2.py
cd ..
```

**O que deve aparecer:**
- No primeiro comando, o log da execução e, no final, "Fim: 3 arquivo(s) gerado(s), 0 falha(s)". Os relatórios (HTML, Excel e PDF) ficam em `parte 2/saida/`, e o log em `parte 2/logs/`. Sem o `--data-corte`, o relatório usa a semana mais recente da base, que tem poucas propostas.
- No segundo comando, a tabela dos cenários de teste e, no final, "11/11 cenários com o comportamento esperado".

**Quem não usa terminal:** dois cliques em `parte 2/rodar_relatorio.bat`. Se o Windows bloquear o arquivo: botão direito → Propriedades → marcar "Desbloquear".

**O que ler:** [`parte 2/relatorio_parte2.md`](parte%202/relatorio_parte2.md), incluindo como agendar a execução toda segunda-feira.

### Passo 3: Parte 3, extração dos laudos com IA

```
cd "parte 3"
python extrator_laudos.py
python avaliar_extracao.py
cd ..
```

**O que deve aparecer:**
- No primeiro comando, "17 laudo(s) com resposta salva | 0 para enviar à IA", o alerta da contradição do laudo 17 e "Extração concluída: 17 laudos". A tabela extraída fica em `parte 3/saida/extracao_laudos.xlsx`.
- No segundo, "Acerto geral: 99.4% | erros: 0 | omissões: 2 | chutes: 0". O relatório fica em `parte 3/saida/relatorio_avaliacao.md`.

**Não é preciso chave de API:** as respostas da IA estão salvas em `parte 3/respostas_ia/`, e o extrator só as valida. Para chamar a IA de novo, é preciso uma chave gratuita do Google AI Studio num arquivo `.env` na pasta principal, com a linha `GEMINI_API_KEY=sua_chave`, e rodar `python extrator_laudos.py --refazer --lote 17`.

**O que ler:** [`parte 3/relatorio_parte3.md`](parte%203/relatorio_parte3.md).

### Sem rodar nada

Para ver os resultados só abrindo arquivos:
- **Conclusões para a liderança:** [`resumo_executivo.pdf`](resumo_executivo.pdf)
- **Relatórios semanais de exemplo:** pasta [`parte 2/exemplos/`](parte%202/exemplos/)
- **Resultado da extração dos laudos:** [`parte 3/relatorio_avaliacao.md`](parte%203/relatorio_avaliacao.md)

---

## Quanto tempo levei

| Etapa | Tempo |
|---|---|
| Leitura do enunciado e entendimento do problema | cerca de 2h |
| Parte 1: tratamento e diagnóstico | cerca de 3h |
| Parte 2: automação | cerca de 3h |
| Parte 3: gabarito, extração e avaliação | cerca de 3h |
| Diário, resumo executivo e README | cerca de 2h |
| Revisão final, organização das pastas e publicação no GitHub | cerca de 9h |
| **Total** | **cerca de 22h** |

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