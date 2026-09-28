# Parte 1 — Diagnóstico do funil

Código: `analise_parte1.py` (rodar com `python analise_parte1.py`). O tratamento de dados está em `tratamento.py`, e o registro de cada problema encontrado e da decisão tomada está em [`registro_tratamento.md`](registro_tratamento.md).

## Base analisada

- **5.864 propostas**, com entrada entre jan/2024 e dez/2025. Partindo de 6.400 linhas, removi 535 terrenos (instrução do enunciado) e 1 proposta de cliente com 14 anos (regra de negócio). As duas remoções quase não alteram os resultados; o impacto está medido no registro de tratamento.
- **1.128 contratadas (19,2%)**: R$ 2.261 mi solicitados e R$ 417 mi contratados.
- **Premissa geral:** os valores em R$ são **volume de crédito solicitado**, não receita. A receita seria o juro sobre esse volume (≈ 1,3% a.m.).

---

## 1. Onde o funil perde mais valor?

Medi a perda de duas formas:

- **R$ perdido bruto:** a soma do valor solicitado das propostas que pararam em cada etapa.
- **R$ ponderado:** o valor perdido multiplicado pela chance que essas propostas tinham de virar contrato. Isso responde ao "nem toda perda custa o mesmo": perder uma proposta perto do fim custa mais, porque a chance de fechar era maior e o Bari já tinha pago análise de crédito e laudo.

| Etapa em que parou | Propostas perdidas | R$ perdido bruto | Chance de contratar ao chegar | R$ ponderado |
|---|---|---|---|---|
| 1. Simulação | 256 | R$ 98 mi | 19% | R$ 19 mi |
| 2. Lead | 909 | R$ 347 mi | 20% | R$ 70 mi |
| 3. Análise de crédito | 1.656 | **R$ 650 mi** | 24% | R$ 156 mi |
| 4. Avaliação do imóvel | 1.151 | R$ 454 mi | 37% | R$ 168 mi |
| 5. Formalização | 764 | R$ 296 mi | 60% | **R$ 177 mi** |

**Resposta:** pelo valor bruto, a maior perda está na **análise de crédito (etapa 3)**, onde param mais propostas. Pelo valor ponderado, que considero a medida mais importante, as maiores perdas estão no **fim do funil: formalização (etapa 5) e avaliação do imóvel (etapa 4)**. Nessas etapas, cada proposta perdida estava perto de fechar e já tinha gerado custo.

**Por motivo da perda:**

| Motivo | R$ perdido |
|---|---|
| Sem retorno | R$ 575 mi |
| Desistiu | R$ 551 mi |
| Reprovada crédito | R$ 325 mi |
| Problema garantia | R$ 241 mi |
| Documentação pendente | R$ 153 mi |

**Metade do valor perdido (R$ 1,13 bi) não tem relação com crédito nem com garantia**: o cliente sumiu ou desistiu. Já a reprovação de crédito é, em boa parte, uma perda esperada, porque é a política funcionando. A "Documentação pendente" (R$ 153 mi) está toda na etapa 5: são propostas já aprovadas no crédito e no imóvel.

**Premissa do R$ ponderado:** supõe que a proposta perdida em uma etapa tinha a mesma chance de contratar que a média das propostas que chegam nela.

---

## 2. A percepção da liderança se confirma?

### "A conversão caiu" → **não confirmada. Confiança: baixa a média**

| Trimestre de entrada | Propostas | Conversão | Margem de erro (95%) | % vindas de correspondente |
|---|---|---|---|---|
| 2024 T3 | 802 | 21,3% | ± 2,8 p.p. | 24,7% |
| 2024 T4 | 1.096 | 20,9% | ± 2,4 p.p. | 28,6% |
| 2025 T1 | 1.342 | 18,3% | ± 2,1 p.p. | 28,6% |
| 2025 T2 | 1.111 | 19,9% | ± 2,3 p.p. | 27,0% |
| 2025 T3 | 687 | 17,0% | ± 2,8 p.p. | 31,3% |
| 2025 T4 | 218 | 16,1% | ± 4,9 p.p. | 29,8% |

- A conversão passou de uma média de **19,9%** (2024 T3 a 2025 T2) para **17,0%** em 2025 T3. O teste estatístico (teste z = 1,78) **não confirma** a queda com 95% de confiança: ela pode ser oscilação natural.
- **2025 T4 não é confiável.** A análise mais longa da base levou 78 dias e o último desfecho registrado é de 04/02/2026. Propostas que entraram no fim de 2025 podem ainda estar em andamento e não aparecer na extração, o que também explicaria a queda forte de volume.
- **Parte da queda vem da mudança de mix:** a participação dos correspondentes, que convertem menos, subiu de ~25% para ~31%.

**Conclusão:** há um sinal de queda de ~3 p.p., mas ele não pode ser afirmado com segurança. A resposta honesta à liderança é "talvez tenha caído; é preciso acompanhar os próximos meses para confirmar".

### "O canal de correspondentes não está performando" → **confirmada. Confiança: alta**

- Os correspondentes convertem **13,7%**, contra **21,4%** dos outros canais, em 1.627 propostas (teste z = −6,66, muito além do limite de 1,96).
- **O problema é do canal, não do perfil do cliente.** LTV e ticket médio são praticamente iguais aos dos outros canais, e em **todas as faixas de score e de LTV** o correspondente converte menos:

| Faixa de score | Correspondente | Outros canais |
|---|---|---|
| até 618 | 9,1% | 12,4% |
| 618 a 669 | 14,2% | 17,7% |
| 669 a 722 | 13,7% | 21,7% |
| acima de 722 | 20,7% | 31,9% |

- **A diferença aparece no meio e no fim do funil.** Da avaliação do imóvel para a formalização passam 54% das propostas de correspondente, contra 65% nos outros canais. Isso sugere mais problemas de imóvel e de documentação nas propostas enviadas por eles.

**Nuance importante:** é um problema de **qualidade, não de volume**. O correspondente é o maior canal em número de propostas e trouxe R$ 78 mi em contratos. A recomendação não é cortar o canal, e sim melhorar a qualidade do que ele envia. Se ele convertesse como os demais canais, seriam **~125 contratos a mais (≈ R$ 49 mi)**.

---

## 3. Quais características mais se associam à contratação?

Para cada característica, comparei a conversão entre faixas e testei se a diferença é real ou pode ser acaso (teste qui-quadrado; p-valor abaixo de 0,05 indica associação real).

| Característica | Melhor faixa | Pior faixa | Associação real? |
|---|---|---|---|
| **Score de crédito** | acima de 750: 31,9% | até 600: 9,6% | Sim, muito forte |
| **LTV** | 40–50%: 23,0% | acima de 60%: 12,1% | Sim, forte |
| **Canal** | Parceria: 22,8% | Correspondente: 13,7% | Sim, forte |
| Cliente recorrente | Sim: 23,1% | Não: 18,3% | Sim |
| Região | Centro-Oeste: 22,3% | Sul: 17,1% | Sim, fraca |
| Ticket | 2º quartil: 20,9% | maiores: 17,5% | Sim, fraca |
| Tipo de imóvel, prazo, renda, idade | diferenças de até 2,6 p.p. | | Não |
| Consultor | CONS-018: 23,2% | CONS-003: 14,2% | Não |

**Resposta:** os fatores que mais se associam à contratação são **score, LTV e canal**. Clientes que já operaram com o Bari também convertem melhor.

**Cuidado com os consultores:** a diferença de 9 p.p. entre o melhor e o pior parece grande, mas cada consultor tem só ~190 propostas, e essa variação é compatível com o acaso (p = 0,78). Não há base para concluir que algum consultor tem desempenho pior.

**Alertas encontrados durante a análise:**
- **124 propostas contratadas com LTV acima de 60%**, o limite da política interna. Ou existem exceções à política, ou há contratos fora da regra.
- **249 contratos em que a parcela, mesmo sem juros, é maior que a renda declarada do cliente** (ver recomendação 3).

---

## 4. Três recomendações priorizadas

Priorizei pelo tamanho da perda e pelo risco para o banco: primeiro atacar a maior perda e a sua causa, depois resgatar o dinheiro que já está parado no fim do funil e, por último, investigar um risco de crédito encontrado na base.

| # | Recomendação | Impacto estimado (cenário base) | Intervalo |
|---|---|---|---|
| 1 | Investigar as causas de "Sem retorno" e "Desistiu" e reduzi-las | **R$ 51 mi** em contratos (≈ R$ 25 mi/ano, recorrente) | R$ 25 mi a R$ 102 mi |
| 2 | Recuperar as propostas com "Documentação pendente" | **R$ 46 mi** em contratos | R$ 31 mi a R$ 76 mi |
| 3 | Investigar a renda declarada nos contratos aprovados | **R$ 134 mi** expostos a risco | — |

### 1. Investigar as causas de "Sem retorno" e "Desistiu" e reduzi-las

É a maior perda do funil: **2.887 propostas e R$ 1,13 bi** solicitados, metade de tudo que o Bari perdeu, sem nenhuma relação com crédito ou garantia. Mais importante do que recuperar essas propostas é entender por que isso acontece, para parar de acontecer. Por isso o ganho é **recorrente**.

**O que fazer:**
- Pesquisa curta com quem desistiu, perguntando por que não seguiu.
- Medir o tempo de resposta do Bari ao cliente em cada etapa.
- Começar pela **etapa 3 (análise de crédito)**, que concentra 1.101 dessas perdas, e pelo **canal de correspondentes**, que responde por 30% delas.

**Premissas:**
- Uma ação sobre as causas recupera **10%** dessas propostas (5% no cenário pessimista e 20% no otimista). É uma suposição, porque a base não registra o motivo da desistência.
- A proposta recuperada volta ao funil com a mesma chance de contratar das propostas que passaram da etapa em que ela parou.
- O valor se refere aos dois anos da base; por ano, ≈ R$ 25 mi.

### 2. Recuperar as propostas com "Documentação pendente"

São **398 propostas e R$ 153 mi parados na formalização**. Elas já foram aprovadas no crédito e na avaliação do imóvel, e o Bari já pagou análise e laudo. Falta só o documento: é o dinheiro mais perto de virar contrato em toda a base.

**O que fazer:**
- Acompanhamento ativo das propostas paradas, com prazo definido para o envio dos documentos.
- Lista clara dos documentos exigidos, enviada ao cliente logo no início do processo.
- Alerta automático para propostas paradas há mais de X dias na formalização.

**Premissas:**
- **30%** dos clientes enviam a documentação depois do acompanhamento (20% no pessimista e 50% no otimista).
- Quem envia a documentação contrata, já que crédito e garantia estão aprovados.

### 3. Investigar a renda declarada nos contratos aprovados

Há **249 contratos aprovados, que somam R$ 134 mi, em que a parcela é maior que a renda mensal declarada**. Ou a renda está registrada errada, ou a análise de crédito não está considerando a renda. Nos dois casos, é um risco relevante para o banco.

**O que fazer:**
- Auditar uma amostra desses contratos para saber se o problema é de cadastro ou de aprovação.
- Verificar se a análise usa a renda **comprovada** ou só a **declarada**.
- Criar uma trava no sistema que sinalize propostas em que a parcela ultrapassa um percentual da renda.

**Impacto:** não gera receita nova, **evita perda**. São R$ 134 mi expostos a risco de inadimplência. O risco é atenuado pela garantia (LTV médio de 50%: o imóvel vale cerca do dobro da dívida), mas retomar um imóvel é caro e demorado.

**Premissas:**
- A parcela foi calculada como valor solicitado ÷ prazo, **sem juros**. A parcela real é maior, então 249 é um número mínimo.
- A renda declarada foi considerada correta. Se estiver errada (há 142 casos com renda de exatamente R$ 1.800, um valor suspeito), o problema é de cadastro, mas precisa ser corrigido do mesmo jeito.

---

## Limitações

- As porcentagens de recuperação das recomendações 1 e 2 são suposições; não há dado na base que permita estimá-las.
- A base não informa a data da extração. Usei o último desfecho registrado (04/02/2026) como referência.
- As análises da pergunta 3 comparam uma característica por vez. Elas mostram associação, não causa.
