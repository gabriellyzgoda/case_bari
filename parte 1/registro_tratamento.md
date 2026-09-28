# Registro de tratamento de dados

| # | Problema | Linhas afetadas | Decisão | Justificativa |
|---|---|---|---|---|
| 1 | Formato do arquivo de entrada | 0 | Lido como CSV (separador ',', encoding utf-8-sig) | Separador e encoding detectados automaticamente; BOM removido com utf-8-sig |
| 2 | canal_origem com grafias diferentes | 4 | Padronizado para a grafia mais frequente | São o mesmo canal; separados, criariam canais fantasmas com 1–2 propostas |
| 3 | valor_imovel com prefixo 'R$' | 3 | Prefixo removido e convertido para número | Valor em si é válido |
| 4 | data_entrada no formato dd/mm/aaaa | 3 | Convertida como dia/mês/ano | Confirmado na PR-000153: entrada + tempo_analise_dias = data de assinatura |
| 5 | taxa_juros_aa: nome diz ao ano, dicionário diz ao mês | 0 | Renomeada para taxa_juros_am | Valores entre 0,94 e 1,73: como taxa anual seriam impossíveis; ao mês (~17% a.a.) são típicos de home equity |
| 6 | Coluna ltv ausente no arquivo | 6400 | Calculada como valor_solicitado / valor_imovel | Definição do próprio dicionário de dados |
| 7 | etapa_max_funil = 7 (inexistente) | 1 | Corrigida para 6 | Status 'Contratada' só existe na etapa 6 |
| 8 | idade_cliente menor que 18 | 1 | Proposta removida da base (PR-000079) | Só maiores de 18 podem solicitar crédito; a proposta não deveria existir no sistema |
| 9 | Assinatura anterior à data de entrada | 1 | data_entrada recalculada = data_assinatura - tempo_analise_dias | Premissa: a data do contrato é a mais confiável (documento assinado); tempo_analise_dias bate com as datas em 99,7% das contratadas |
| 10 | Renda exatamente R$ 1.800,00 | 142 | Mantida e marcada | Concentração anormal num valor redondo; renda usada com cautela |
| 11 | score_credito extremo (<400 ou >900) | 9 | Mantido | Dentro da escala do bureau; só registrado |
| 12 | tipo_imovel = Terreno | 535 | Propostas removidas da base | Instrução explícita do enunciado: a análise não considera terreno como garantia |

## Impacto das remoções nos resultados

| Métrica | Com terreno | Sem terreno (base final) |
|---|---|---|
| Propostas | 6.399 | 5.864 |
| Conversão geral | 19,4% | 19,2% |
| Conversão correspondentes | 14,3% | 13,7% |
| R$ solicitado (mi) | 2.459 | 2.261 |

A remoção dos terrenos altera a conversão geral em 0,2 p.p. e a dos correspondentes em 0,6 p.p. A remoção da proposta com cliente menor de idade (1 linha) tem efeito desprezível.
