# Parte 2 — Automação do relatório semanal do funil

Rotina que, a cada execução, **lê o arquivo bruto, aplica o tratamento da Parte 1, calcula as métricas-chave e exporta o relatório em HTML, Excel e PDF**, com log de tudo o que aconteceu.

### Pasta `exemplos/`

Criei a pasta [`exemplos/`](exemplos/) pensando em quem não sabe ou não quer instalar o código: assim, qualquer pessoa consegue ver **exemplos reais** do que a automação produz, só abrindo os arquivos. São os três relatórios (HTML, Excel e PDF) gerados na minha máquina para a semana de 23 a 29/06/2025.

Quem rodar o código não precisa deles: o programa cria a pasta `saida/` e gera os relatórios na hora. Por isso as pastas `saida/` e `logs/` não vão na entrega: estão no `.gitignore` e são recriadas a cada execução. Assim, quem testar vê os arquivos novos aparecendo.

---

## Como rodar (para quem não programa)

**Na primeira vez**, dê dois cliques em `instalar.bat`. Ele instala as bibliotecas necessárias. Se o Python não estiver instalado, a janela avisa e explica como instalar.

**Toda segunda-feira:**
1. Salve o arquivo novo na pasta `dados`, que fica na pasta principal do projeto, com o nome `propostas_credito.csv`.
2. Dê dois cliques em `rodar_relatorio.bat`, dentro da pasta `parte 2`.
3. Ao terminar, a pasta `saida` abre sozinha com os três arquivos. O nome de cada um traz a data da semana, por exemplo `relatorio_funil_2025-06-29.pdf`.
4. Envie para a liderança o formato que preferir.

Se aparecer **"ERRO: o relatório NÃO foi gerado"**, a mensagem logo acima diz o motivo, como arquivo não encontrado ou coluna faltando. O detalhe completo fica no log mais recente da pasta `logs`.

> **Se o Windows bloquear os arquivos `.bat`**, o que é comum quando eles são baixados da internet: clique com o botão direito no arquivo → Propriedades → marque "Desbloquear". Outra saída é rodar pelo terminal, como na seção abaixo.

### Pelo terminal

```
cd "parte 2"
python -m pip install -r ../requirements.txt    (só na primeira vez)
python relatorio_semanal.py
```

Opções:

| Opção | Para que serve | Exemplo |
|---|---|---|
| `--entrada` | Usar outro arquivo de entrada | `--entrada ../dados/base_nova.xlsx` |
| `--data-corte` | Gerar o relatório de uma semana específica (último dia da semana) | `--data-corte 2025-06-29` |
| `--formatos` | Gerar só alguns formatos | `--formatos html,pdf` |

### Agendar para rodar sozinho toda segunda

1. Abra o **Agendador de Tarefas** do Windows e clique em **Criar Tarefa Básica**.
2. Nome: "Relatório semanal do funil". Disparador: **Semanalmente**, às **segundas**, às **8h**.
3. Ação: **Iniciar um programa**.
   - Programa/script: o caminho completo do `rodar_relatorio.bat`
   - Adicione argumentos: `agendado` (assim a janela não fica esperando alguém apertar uma tecla)
   - Iniciar em: o caminho da pasta `parte 2`
4. Conclua. O computador precisa estar ligado no horário.

---

## O que o relatório mostra

Os três formatos mostram **exatamente os mesmos números**, porque são gerados a partir do mesmo cálculo.

| Seção | Conteúdo | Por que está no relatório |
|---|---|---|
| A semana | Propostas novas, contratos assinados e R$ contratado, comparados com a média das 4 semanas anteriores | Visão rápida do volume |
| Conversão por mês de entrada | Últimos 6 meses, com a % de propostas vindas de correspondentes | Acompanhar a possível queda de conversão (Parte 1, pergunta 2) |
| Onde o funil perde | Propostas e R$ perdidos por etapa nos últimos 6 meses | Acompanhar onde está a perda de valor (Parte 1, pergunta 1) |
| Canais | Propostas, conversão e R$ contratado por canal | Acompanhar o canal de correspondentes (Parte 1, pergunta 2) |
| Contratos da semana para revisão | Contratos com LTV acima de 60% ou com parcela maior que a renda declarada | Alertas da Parte 1 (política de LTV e recomendação 3) |
| Qualidade dos dados | Problemas encontrados no arquivo e o que foi feito | Transparência sobre o tratamento |

**Meses "em maturação":** a análise mais longa da base levou 78 dias. Por isso, meses com propostas de menos de 80 dias aparecem marcados. A conversão deles ainda vai subir e não deve ser comparada com a de meses completos. Essa regra evita que a liderança leia "ainda não fechou" como "a conversão caiu", um dos achados da Parte 1.

### Por que três formatos

O enunciado pede um formato (Excel, PDF **ou** HTML). Decidi gerar os três porque o relatório vai ser lido por pessoas diferentes, e minha ideia é que **qualquer uma delas, seja da área de negócio ou do time de tecnologia, consiga acessar do jeito que mais entende**:

- **HTML:** o mais visual e legível. Abre em qualquer navegador e pode ser enviado por e-mail. Pensado para a liderança comercial.
- **Excel:** para quem quer filtrar e mexer nos números. A conversão e o R$ ponderado são fórmulas, e não valores fixos, então a planilha se recalcula se algum dado for alterado.
- **PDF:** um documento fechado, que não muda. Bom para arquivar e encaminhar.

Gerar três formatos também traz um risco: são três pontos possíveis de falha. Por isso cada formato é gerado de forma independente (ver "Tratamento de erros").

---

## Tratamento de erros

O script nunca termina com um erro técnico em inglês. Cada problema previsível gera uma mensagem em português dizendo o que aconteceu e o que fazer. Ao final, ele devolve um **código de saída**, que o Agendador de Tarefas usa para saber se deu certo:

| Código | Significado | Exemplo |
|---|---|---|
| 0 | Tudo gerado | Execução normal |
| 1 | Algum formato falhou, mas os outros foram gerados | Biblioteca do PDF não instalada |
| 2 | Problema no arquivo de entrada: relatório não gerado | Arquivo não encontrado, vazio ou sem coluna obrigatória |
| 3 | Erro inesperado: relatório não gerado | Qualquer outro caso (detalhe técnico completo no log) |

**Os formatos são independentes.** Se o PDF falhar, o HTML e o Excel são gerados mesmo assim, e o log registra qual falhou e por quê. Gerar três formatos significa ter três pontos possíveis de falha, e um problema em um deles não pode deixar a liderança sem relatório.

## Log da execução

Cada execução cria um arquivo novo em `logs/`, por exemplo `relatorio_2026-09-27_124630.log`, com:
- o arquivo lido e o formato detectado
- cada problema encontrado nos dados, com o número de linhas e o que foi feito
- a semana do relatório, as propostas novas e os contratos assinados
- os avisos (semana sem propostas novas, contratos para revisão, colunas faltando ou novas)
- os arquivos gerados e as falhas

## Arquivo de entrada com uma coluna a menos ou em formato novo

As colunas foram divididas em dois grupos:
- **Obrigatórias:** sem elas não existe funil. São identificação, data de entrada, canal, tipo de imóvel, valores, etapa, status e **score de crédito** (obrigatório porque é a principal variável da decisão de crédito). Se faltar uma, o script **para e diz qual é**.
- **Opcionais:** usadas em análises secundárias (renda, prazo, idade, cidade...). Se faltar uma, o script **avisa no log e gera o relatório mesmo assim**.

Além disso, a leitura se adapta sozinha a mudanças comuns de formato: arquivo **Excel** em vez de CSV, separador **`;`** (padrão do Excel brasileiro), encoding **latin-1** e nomes de coluna com **maiúsculas ou espaços**. Colunas novas e inesperadas são ignoradas e registradas no log.

### Testes

O `testes_parte2.py` cria versões alteradas da base, roda a automação com cada uma e confere o resultado. Resultado na minha máquina: **11/11 cenários com o comportamento esperado.**

| Cenário | Esperado | Resultado |
|---|---|---|
| Arquivo original | Gera o relatório (0) | OK |
| Sem coluna obrigatória (`status_final`) | Para com mensagem clara (2) | OK |
| Sem coluna opcional (`renda_mensal_declarada`) | Avisa e gera (0) | OK |
| Coluna nova inesperada | Ignora, avisa e gera (0) | OK |
| Nomes de coluna com maiúsculas e espaços | Gera (0) | OK |
| Separador `;` | Gera (0) | OK |
| Encoding latin-1 | Gera (0) | OK |
| Arquivo Excel (.xlsx) em vez de CSV | Gera (0) | OK |
| Arquivo vazio | Para com mensagem clara (2) | OK |
| Só cabeçalho, sem linhas | Para com mensagem clara (2) | OK |
| Arquivo inexistente | Para com mensagem clara (2) | OK |

Para rodar: `python testes_parte2.py`

---

## Arquivos da Parte 2

| Arquivo | Função |
|---|---|
| `relatorio_semanal.py` | Script principal: orquestra as etapas, grava o log, trata os erros e define o código de saída |
| `metricas_semanais.py` | Calcula as métricas do relatório. Os parâmetros (LTV máximo, dias de maturação, meses exibidos) ficam no topo do arquivo |
| `exportadores.py` | Gera o HTML, o Excel e o PDF a partir das mesmas métricas |
| `../tratamento.py` | Mesmo tratamento da Parte 1, com a leitura adaptada a formatos novos. Fica na pasta principal, compartilhado pelas duas partes |
| `testes_parte2.py` | Testes dos cenários de falha |
| `../requirements.txt` | Bibliotecas com as versões fixas que foram testadas (na pasta principal, vale para o projeto todo) |
| `instalar.bat` | Instalação em dois cliques (primeira vez) |
| `rodar_relatorio.bat` | Geração do relatório em dois cliques (toda segunda) |

## Problemas encontrados durante o desenvolvimento

- **Versão de biblioteca:** um trecho do código funcionava numa versão do pandas e quebrava na versão instalada na minha máquina. Por isso o `requirements.txt` fixa as versões testadas, e o `instalar.bat` garante que todos usem as mesmas.
- **Bloqueio do Windows:** o navegador bloqueou o download dos arquivos `.bat`. A documentação acima explica como desbloquear, e o relatório também pode ser gerado direto pelo terminal.

## Limitações

- **Semana padrão:** o relatório usa a semana que termina na data de entrada mais recente do arquivo. Na base do desafio, essa semana (23 a 29/12/2025) tem só 2 propostas, por isso o exemplo usa a semana de junho. Em produção, o arquivo novo de cada segunda traria a semana anterior completa.
- **Relatórios de semanas passadas:** quando uso `--data-corte` numa data antiga, os status das propostas já refletem desfechos que aconteceram depois dessa data. Em produção isso não acontece, porque o arquivo é sempre o mais recente.
- **Envio:** a rotina gera os arquivos, mas não envia o e-mail. O próximo passo seria enviar automaticamente para uma lista de destinatários.
- **Windows:** os `.bat` funcionam só no Windows. Em Linux ou Mac, o relatório roda pelo comando `python relatorio_semanal.py`.