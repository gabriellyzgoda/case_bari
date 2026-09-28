# Parte 3 — Extração estruturada dos laudos com IA

Solução que lê os 17 laudos de avaliação em texto livre, cada um num formato diferente, e extrai de todos o mesmo conjunto de campos, usando IA (Gemini, do Google). A extração é validada automaticamente contra o próprio texto do laudo e avaliada contra um gabarito que eu preenchi à mão.

**Resultado final: 99,4% de acerto, 0 erros e 0 chutes** em 323 células (17 laudos × 19 campos).

---

## Como rodar

Na pasta `parte 3`:

```
python extrator_laudos.py        valida as respostas da IA salvas em respostas_ia/ e gera saida/extracao_laudos.xlsx
python avaliar_extracao.py       compara com o gabarito e gera saida/relatorio_avaliacao.md
```

**Para ver o resultado sem rodar nada**, abra o [`relatorio_avaliacao.md`](relatorio_avaliacao.md), gerado na minha máquina: ele traz o acerto geral, o acerto por campo e todas as divergências.

**Não é preciso ter chave de API para reproduzir o resultado.** As respostas da IA ficam salvas em `respostas_ia/` (um JSON por laudo, com o modelo e a data). O extrator valida essas respostas e o avaliador mede o acerto, sem chamar a IA.

Para chamar a IA de novo, é preciso uma chave gratuita do Google AI Studio num arquivo `.env` na pasta do projeto (`GEMINI_API_KEY=...`). O `.env` está no `.gitignore` e não vai para o repositório.

```
python extrator_laudos.py --refazer --lote 17     extrai os 17 laudos numa única requisição
python extrator_laudos.py --listar-modelos        mostra os modelos disponíveis para a chave
python extrator_laudos.py --modelo NOME           usa outro modelo
```

## Arquivos

| Arquivo | Função |
|---|---|
| `extrator_laudos.py` | Envia os laudos à IA, salva as respostas e valida cada campo contra o texto do laudo |
| `avaliar_extracao.py` | Compara a extração com o gabarito e calcula acertos, erros, omissões e chutes |
| `gabarito_laudos.xlsx` | Gabarito preenchido por mim, com as regras de preenchimento na aba "Instruções" |
| `laudos/` | Os 17 laudos originais |
| `respostas_ia/` | Respostas brutas da IA usadas na entrega (`gemini-3.5-flash-lite`) |
| `respostas_ia_gemini-3.8-flash/` | Respostas de uma primeira tentativa com outro modelo (9 laudos, não avaliadas; ver "Histórico") |
| `relatorio_avaliacao.md` | **Resultado da avaliação gerado na minha máquina**, para quem quiser ver sem rodar o código |
| `saida/` | Gerada ao rodar: tabela extraída (CSV e Excel), relatório de avaliação e detalhe por célula |

---

## Campos extraídos

| Campo | Regra |
|---|---|
| tipo_imovel | Como escrito no laudo |
| endereco, cidade, uf | Endereço sem cidade/UF; UF com 2 letras |
| area_privativa_m2 | Área privativa |
| area_util_m2 | Área útil em campo próprio: ela é **parte** da área privativa, não igual a ela |
| area_construida_m2 | Inclui "benfeitorias construídas" (laudo 5) e "área coberta" de galpão térreo (laudo 14) |
| area_terreno_m2 | Inclui lote e "superfície" de terreno; hectares convertidos (1 ha = 10.000 m²), a única conversão permitida |
| area_total_m2 | Área total; nunca calculada somando outras áreas |
| ano_construcao | Só quando o laudo diz explicitamente que é o ano de construção |
| idade_informada | Quando o laudo dá idade ("11 anos (idade aparente)", "aproximadamente 18 anos") ou um ano ambíguo: o texto é guardado, **o ano nunca é calculado** |
| valor_avaliacao | Em reais |
| matricula | Número da matrícula ou do registro imobiliário |
| onus_situacao | Só três respostas possíveis: **sem ônus**, **com ônus** ou **não confirmado** |
| onus_descricao | Resumo do que o laudo diz |
| data_vistoria | Formato AAAA-MM-DD |
| responsavel_tecnico, registro_profissional | Nome sem título; conselho e número |
| contradicoes | Preenchido só quando o laudo traz dois valores diferentes para o mesmo dado |

**Ônus: por que três opções.** "Não informado" e "sem ônus" são coisas diferentes. Se o laudo não fala de ônus, não verificou, não tem certidão ou só traz a declaração do proprietário, a resposta é **"não confirmado"**. Marcar esses casos como "sem ônus" faria o banco considerar o imóvel livre quando ninguém verificou, e para um crédito com garantia de imóvel esse é o erro mais caro. Penhora **cancelada** conta como "sem ônus". Alienação fiduciária, penhora ativa, hipoteca, servidão e reserva legal contam como "com ônus".

---

## Como garanto que a saída sai sempre no mesmo formato

1. **Esquema imposto à IA.** A requisição envia um esquema JSON (response schema) que obriga a IA a devolver exatamente os 19 campos, com o tipo certo (número, inteiro, texto) e, no caso do ônus, só uma das três opções.
2. **Validação no código.** Mesmo com o esquema, cada campo é conferido de novo: números precisam ser números, datas precisam estar em AAAA-MM-DD, UF precisa ter duas letras maiúsculas. Qualquer coisa fora do formato é descartada e registrada.

## Como evito que a IA "chute"

Para cada campo, a IA precisa devolver o **valor** e a **evidência**: o trecho do laudo de onde tirou o valor. O código então aplica quatro verificações:

| Verificação | O que pega |
|---|---|
| **A evidência existe no laudo?** | Valor inventado: se o trecho citado não está no laudo, o valor é descartado |
| **O valor está na evidência?** | Valor calculado ou trocado: um ano 2014 calculado a partir de "11 anos" não aparece no trecho e é descartado |
| **Trava do ônus** | "Sem ônus" citando um trecho que indica falta de informação ("não consta", "declaração do proprietário"...) vira "não confirmado" |
| **Validação por laudo no envio em lote** | Se a IA misturar laudos, a evidência não existe no laudo em questão e o valor é descartado |

Tudo o que é descartado fica **vazio** e o motivo vai para a coluna `alertas` da tabela final. Nada é removido em silêncio. A regra geral é: **na dúvida, o sistema assume que não sabe.**

Durante o desenvolvimento, essas verificações foram testadas com respostas simuladas contendo erros plantados de propósito: uma matrícula inventada, um ano calculado a partir da idade, um "sem ônus" sem certidão, informação de um laudo colocada em outro e um laudo "esquecido" no lote. Todos foram detectados.

**Uma limitação honesta:** a validação confere a *origem* do valor, não a *interpretação*. Uma IA que cita um trecho verdadeiro mas interpreta errado passaria pelas verificações 1 e 2. Por isso existe a trava específica do ônus, e por isso o gabarito continua indispensável.

## Campo que não existe e documento que se contradiz

- **Campo que não existe:** o valor fica vazio (null). Exemplos: matrícula do laudo 8 ("matrícula não apresentada"), ano de construção dos terrenos e das idades aproximadas.
- **Documento que se contradiz:** o campo afetado fica vazio e os dois valores são descritos em `contradicoes`, com um alerta. O laudo 17 informa área total de 95 m² no cabeçalho e 92 m² na tabela interna, e pede para "manter a divergência para conferência". O sistema não escolhe um dos valores: deixa a área total vazia e sinaliza a contradição para um humano decidir.

---

## Como meço se a extração está certa

### Gabarito

Preenchi o gabarito à mão, lendo cada laudo, com as regras que decidi (aba "Instruções" do `gabarito_laudos.xlsx`). O gabarito **não foi feito pela IA**: se fosse, a IA estaria corrigindo a própria prova.

Para conferir o gabarito, usei **dupla anotação**: a IA assistente preencheu uma versão independente, gravada antes de ver a minha, e as duas foram comparadas célula a célula. A comparação encontrou erros reais no meu preenchimento, que corrigi olhando o laudo:
- conversão de hectares (4,8 ha = 48.000 m², e não 480)
- área do **lote** registrada como área total (laudo 2)
- ônus do laudo 17 marcado como "sem ônus" quando só havia declaração do proprietário
- separador de milhar nos valores e áreas (`1.450` seria lido como 1,45)

### Critério de acerto

Cada célula (laudo × campo) é classificada em uma de quatro categorias:

| Categoria | Significado |
|---|---|
| **ACERTO** | Igual ao gabarito, incluindo "vazio" quando o gabarito é vazio |
| **CHUTE** | O gabarito é vazio (a informação não existe), mas a extração preencheu. **O pior erro**: um valor plausível inventado |
| **OMISSÃO** | O gabarito tem valor, mas a extração deixou vazio. Erro "seguro": o sistema assumiu que não sabia |
| **ERRO** | Os dois têm valor, mas diferentes |

"Igual" depende do tipo de campo: números com diferença menor que 0,01; matrícula comparando só os dígitos; ônus, data e UF com igualdade exata; cidade, responsável e registro ignorando pontuação; tipo, endereço e idade aceitando quando um texto contém o outro ou compartilham 60% das palavras. `onus_descricao` e `contradicoes` são textos livres, então só conta se ambos estão preenchidos ou ambos vazios.

---

## Resultado

Modelo: `gemini-3.5-flash-lite`, 17 laudos numa única requisição.

| Resultado | Células | % |
|---|---|---|
| ACERTO | 321 | 99,4% |
| ERRO | 0 | 0,0% |
| OMISSÃO | 2 | 0,6% |
| CHUTE | 0 | 0,0% |

**Taxa de chute: 0 de 93 células** em que a informação não existe no laudo.

### Divergências analisadas

| Laudo | Campo | Gabarito | Extração | Análise |
|---|---|---|---|---|
| 5 | endereco | ~~Sítio Boa Vista~~ → vazio | vazio | **O erro era do gabarito.** O laudo só traz o nome da propriedade e o município, não um endereço. A IA estava certa, e corrigi o gabarito |
| 8 | idade_informada | ano de referência: 2005 | vazio | Omissão da IA. Ela não inventou um ano de construção, mas também não guardou o texto ambíguo, como a regra pedia. Nenhuma informação falsa entrou, mas uma informação útil ficou de fora |
| 12 | ano_construcao | 2012 | vazio | O laudo diz "Ano informado: 2012", sem dizer que é o de construção. A IA aplicou a regra ao pé da letra. Mantive o gabarito, mas reconheço que ele é incoerente com o laudo 8, em que tratei um ano ambíguo como incerto |

A avaliação funcionou nos dois sentidos: mostrou limitações da IA e também um erro e uma incoerência do meu gabarito.

---

## Histórico da execução

A extração passou por vários problemas reais, e em nenhum deles o trabalho feito se perdeu, porque cada resposta é salva assim que chega:

1. **Modelo desativado.** O primeiro modelo escolhido (`gemini-2.5-flash`) não estava mais disponível para contas novas. O próprio erro da API indicou o modelo substituto.
2. **Servidor sobrecarregado (503) e queda de internet.** O programa tenta de novo sozinho com espera crescente. Quando desiste, os laudos já extraídos ficam salvos e a execução seguinte continua de onde parou.
3. **Cota diária esgotada (429).** No modo "um laudo por requisição", cada nova tentativa também consumia cota, e a cota gratuita do `gemini-3.8-flash` acabou depois de 9 laudos (respostas guardadas em `respostas_ia_gemini-3.8-flash/`). O programa passou a detectar a cota diária esgotada e parar na hora, sem gastar tentativas.
4. **Envio em lote.** Por sugestão de um colega que trabalha na área, implementei o envio de vários laudos numa única requisição (`--lote`). O risco do lote é a IA misturar informações entre laudos, mas a validação por evidência, feita laudo a laudo, protege contra isso. Os 17 laudos foram extraídos com o `gemini-3.5-flash-lite` numa só requisição, em cerca de 30 segundos, todos pelo mesmo modelo.
5. **Validação rígida demais.** Na primeira validação, a contradição do laudo 17 foi descartada: a IA detectou corretamente, mas citou o trecho com uma vírgula no lugar de um ponto e vírgula. Ajustei a verificação para ignorar a pontuação, mantendo palavras e números idênticos. Um teste confirmou que um número trocado (97 m² em vez de 95 m²) continua sendo descartado. Como as respostas estavam salvas, a correção não gastou nenhuma requisição.

## Segurança e dados

- A chave de API fica no arquivo `.env`, que está no `.gitignore` e nunca vai para o repositório.
- No plano gratuito, o Google pode usar os dados enviados para melhorar os seus produtos. Isso só é aceitável porque os laudos do desafio são fictícios, o que mostra na prática o motivo da regra "nada de dado real".

## Limitações

- **Amostra pequena:** 17 laudos não bastam para garantir o mesmo desempenho em milhares de documentos reais.
- **Uma execução:** a resposta da IA pode variar entre execuções. O ideal seria rodar várias vezes e medir a estabilidade.
- **Um modelo avaliado:** as respostas do `gemini-3.8-flash` cobrem só 9 laudos e não foram comparadas.
- **Comparação flexível de textos:** endereço e tipo aceitam variações de escrita, o que pode esconder pequenas diferenças.
- **Trava do ônus baseada em palavras-chave:** cobre as formas de escrita dos 17 laudos, mas laudos novos podem usar outras expressões.

## Fontes externas

- Conceitos de penhora cancelada e de área útil × área privativa: pesquisa no Google, com as respostas geradas pela IA do próprio buscador (Gemini). Não foi consultada uma fonte primária (legislação de registros públicos ou norma técnica de áreas).
- Chave e limites da API do Gemini: Google AI Studio (aistudio.google.com)