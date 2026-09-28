# Diário de bordo

## (a) Registro de uso de IA

Usei duas IAs: a Claude, como assistente durante todo o desafio, ela me ajudou a escrever e entender os códigos, explicar conceitos e rascunhar os relatórios, o resumo executivo e o README, sempre com as decisões tomadas por mim. E o Gemini, de duas formas: na busca do Google, para pesquisar conceitos do gabarito (ônus, penhora e área útil), e via API, como parte da solução da Parte 3.

| nº | Situação | O que houve? |
|---|---|---|
| 1 | O código da IA funcionava no ambiente dela, mas deu erro no meu computador, porque a minha versão da biblioteca pandas era mais nova que a dela. Para solucionar isso, criei o requirements.txt, que fixa as versões testadas. Na instalação, meu scipy 1.18.1 foi trocado pela 1.17.1. | IA errou. |
| 2 | A IA não consegue rodar arquivos .bat, porque o ambiente dela é Linux, então testei no meu Windows, que na hora bloqueou o download. Então, tive de criar os arquivos manualmente e documentei como desbloquear ou rodar pelo terminal, já que o avaliador pode ter o mesmo problema. | Limitação da IA. |
| 3 | Discordei da IA em três decisões: removi a proposta do cliente de 14 anos pois era impossível alguém de 14 anos mandar uma proposta (a IA sugeria só apagar a idade), recalculei a data de entrada no sistema que era posterior à data do contrato assinado (ela sugeria não usar as datas) e gerei o relatório em 3 formatos, para cada pessoa usar o que preferir (ela recomendava só HTML). | Discordei da IA. |
| 4 | Ao selecionar o texto do enunciado, achei dois prompt injections. Não segui o do "abacaxi", porque parecia um teste e não fazia sentido colocá-lo no README. Segui o de excluir os terrenos, por ser uma regra de análise plausível, e medi o impacto: a conversão mudou só 0,2 p.p., e nenhuma conclusão mudou. | Leitura analítica. |
| 5 | A IA escolheu o modelo gemini-2.5-flash, que já estava desativado para contas novas. A mensagem de erro da própria API indicou alternativas, então tive que optar por pesquisar outra que pudesse usar, e escolhi o gemini-3.5-flash-lite. | A IA errou. |
| 6 | A validação criada pela IA descartou uma resposta certa do Gemini: a contradição do laudo 17 foi rejeitada por uma vírgula no lugar de um ponto e vírgula. Identifiquei o problema olhando o arquivo de resposta, e a validação passou a ignorar a pontuação, isso sem gastar cota. | A IA errou. |
| 7 | Foi muito bom na parte 3 fazer o gabarito de laudos a mão e depois comparar com outro que a própria IA fez. Foi através dessa comparação que eu achei erros bobos como: conversão errada de hectares, pontos de milhar errados, algumas informações que estavam no lugar errado. A IA foi uma conferência nessa parte para mim. | Conferência com a IA. |

## (b) O que aprendeu do zero

Eu não sabia muito bem programar em python, e por isso, não fazia ideia do que era o pandas, que eu descobri ser uma biblioteca de python para trabalhar com tabelas. Consegui aprender isso conversando com a IA e testando o código no VSCode. Através dessa biblioteca é possível filtrar, somar e agrupar milhares de linhas com uma linha de código. Achei uma ferramenta muito boa para ler a tabela, que era enorme com 6.400 linhas, corrigir e depois agrupar e somar de várias formas. Levei cerca de 20 minutos para entender como funcionava e para que seria útil no case.

## (c) Autocrítica

Devido à falta de tempo para pesquisas específicas, as respostas que obtive ao perguntar sobre algumas questões da tabela do gabarito de laudos, vieram de uma IA, o que pode ser algo não tão confiável. Nos laudos 8 e 12 acabaram ficando meio incoerentes, a IA não guardou o valor "ano de referência: 2005" em idade_informada no laudo 8, e também a IA não aceitou: "Ano informado: 2012" como ano de construção. Além disso, o relatório não é enviado de forma automática semanalmente.

Com mais 40 horas eu corrigiria esses itens listados, conferiria os conceitos em fontes oficiais, revisaria a regra de ano ambíguo e deixaria o gabarito coerente entre os laudos 8 e 12 e faria com que o relatório fosse enviado por e-mail automaticamente.

A pergunta ao time de negócio: os 124 contratos com LTV acima de 60% foram exceções aprovadas?
