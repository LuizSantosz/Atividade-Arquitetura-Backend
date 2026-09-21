
## Aplicar — Recomendar a forma de propagar o resultado de exame

**1. Recomendação em uma frase**

Recomendo a alternativa **D — tópico com registro de saída**: ela rompe o acoplamento entre gravar o resultado e notificar (a causa do incidente da semana passada) e já entrega a capacidade de reprocessamento que a Auditoria e os próximos consumidores vão precisar.

**2. O que cada alternativa resolve e o que ela cobra**

- **A. Chamada síncrona.** Resolve nada do problema atual — é exatamente o desenho de hoje que causou o incidente (Notificações lenta travando a gravação do resultado). Cobra a disponibilidade do resultado inteiro atrelada ao consumidor mais lento entre os três, e cada consumidor novo (que aparece a cada dois meses, em média) piora essa fragilidade.
- **B. Uma fila por destino.** Resolve o isolamento de falha entre consumidores — Notificações lenta deixa de afetar Faturamento, já que cada um tem fila e dono próprios. Cobra que Exames precisa mudar código toda vez que um consumidor novo aparece, e nenhuma fila tradicional guarda histórico suficiente para o reprocessamento de 90 dias que a Auditoria precisa.
- **C. Tópico compartilhado.** Resolve o acoplamento de Exames a cada consumidor individual — publicar uma vez, e consumidores novos apenas assinam o tópico, sem mudança em Exames. Cobra que a publicação ainda não tem garantia atômica com a gravação do resultado, e sem retenção, ainda não resolve o reprocessamento que a Auditoria precisa.
- **D. Tópico com registro de saída.** Resolve os dois problemas de C ao mesmo tempo: a tabela de saída gravada na mesma transação do resultado garante que gravar e publicar nunca fiquem inconsistentes entre si, e a retenção permite à Auditoria (e a qualquer consumidor novo) reprocessar sob demanda. Cobra manter essa tabela e um processo que a lê e publica de fato no tópico — mais uma peça de operação do que C.

**3. Como a recomendação atende aos fatos 1 e 2 ao mesmo tempo**

O fato 1 pede retenção e capacidade de reprocessar — isso vem da tabela de saída em si, que guarda histórico suficiente para qualquer consumidor reler sob demanda, não só consumir o que passa ao vivo. O fato 2 pede garantias diferentes por consumidor — isso não vem da retenção, vem de cada consumidor controlar sua própria posição de leitura no tópico: Faturamento só avança sua posição depois de confirmar o processamento (garantindo que nada se perde), enquanto Notificações pode tolerar avançar mesmo perdendo uma entrega ocasional. A mesma infraestrutura atende os dois porque a garantia de entrega é uma decisão de cada consumidor, não uma propriedade única do tópico.

**4. O que acontece se a equipe ligar a recomendação antes de resolver o fato 6**

Qualquer reentrega — que acontece mesmo em condições normais de mensageria com garantia "pelo menos uma vez", e fica mais provável ainda com um mecanismo de reprocessamento como o de D — processa o mesmo resultado mais de uma vez em cada consumidor. Em Faturamento isso vira cobrança duplicada; em Notificações, o paciente recebe o mesmo aviso duas vezes; em Auditoria, o histórico ganha entradas duplicadas para o mesmo evento. A pré-condição que falta é cada consumidor conseguir reconhecer e descartar reentregas do mesmo identificador de evento antes de aplicar qualquer efeito — sem isso, D não é seguro para ligar.

**5. Alternativa a descartar de imediato, fato que a derruba, e sinal de revisão**

Descartaria a **A** de imediato. O fato que a derruba é o fato 4 — "hoje, se um dos avisos falha, a gravação do resultado é desfeita junto" — que é exatamente o comportamento de A e a causa direta do incidente da semana passada. Sinal que faria rever a escolha de D: se a defasagem entre a gravação do resultado e a disponibilidade do evento para os consumidores passar a ultrapassar um limite aceitável de forma recorrente (o processo que lê a tabela de saída atrasando sistematicamente), isso indicaria que a saída assíncrona introduziu um atraso que a operação clínica não tolera para algum consumidor específico.

---

## Analisar — Investigar uma fila que cresce

**1. Duas hipóteses e o sinal que as separa**

- **Hipótese A:** o consumidor de Faturamento está falhando ao processar parte das mensagens — provavelmente as que chegam sem `unidade_medida`, agora que o campo é opcional — e essas mensagens são reentregues até esgotar tentativas e caírem na fila de rejeitadas. Isso explica o crescimento das duas filas ao mesmo tempo.
- **Hipótese B:** o consumidor simplesmente parou de confirmar mensagens (travou ou entrou em laço sem dar *ack*), sem relação direta com o campo opcional. Nesse caso a fila principal cresce porque nada é consumido, mas a fila de rejeitadas não deveria crescer, já que rejeição exige um consumidor ativo decidindo rejeitar.

Sinal que separa as duas: os registros de log do consumidor logo antes de cada mensagem cair na fila de rejeitadas — um erro de validação ou exceção citando `unidade_medida` aponta para A; ausência de qualquer atividade de processamento no log aponta para B. O fato de a fila de rejeitadas já ter 300 mensagens (não zero) já favorece a hipótese A, mas isso ainda precisa ser confirmado pelo log, não assumido só pela contagem.

**2. Por que afrouxar um campo pode quebrar um consumidor**

Um consumidor escrito antes da mudança provavelmente assume, no código, que `unidade_medida` sempre existe — não porque alguém decidiu tratar a ausência dele, mas porque nunca precisou tratar. Tornar o campo opcional não facilita a vida do consumidor: troca uma garantia que ele dependia silenciosamente por uma possibilidade nova que o código nunca previu. Se o consumidor acessa o campo diretamente, sem checar se existe, a ausência agora gera uma exceção — a mudança afrouxou o contrato do lado de quem publica, mas do lado de quem consome isso quebrou uma suposição que antes era sempre verdadeira.

**3. Diferença entre a fila principal crescer e a fila de rejeitadas crescer**

A fila principal crescer sozinha costuma indicar que o consumidor parou de processar, ou está mais lento que a chegada de mensagens novas — o defeito está na capacidade geral do consumidor. A fila de rejeitadas crescer indica que o consumidor está ativo e tentando, mas falhando ao processar mensagens específicas o suficiente para elas serem descartadas para decisão controlada — o defeito está no conteúdo ou formato de mensagens específicas. As duas crescendo juntas, como neste caso, sugere as duas coisas acontecendo: mensagens específicas falhando e indo para a fila de rejeitadas, o que consome tempo do consumidor e atrasa o restante, fazendo a fila principal também crescer.

**4. O sinal que teria avisado antes do usuário reclamar**

Um alarme sobre o tamanho da fila principal (contagem de mensagens) ou sobre a idade da mensagem mais antiga nela, com um limite configurado, teria avisado a equipe muito antes de "Faturamento parou de fechar contas" virar um problema visível para usuários. A contagem de mensagens é um sinal barato e disponível de observar continuamente; a ausência de qualquer alarme sobre ele é, em si, uma lacuna de observabilidade, independente de qual tenha sido a causa técnica.

**5. Conclusão não sustentada, rotulada como hipótese, e o dado que a confirmaria**

Conclusão não sustentada: "a mudança do contrato foi a causa da fila crescer." **Hipótese** — os dois eventos são próximos no tempo (mudança na véspera, fila crescendo na manhã seguinte), mas os cinco fatos estabelecem só coincidência temporal, não uma relação causal direta. Dado que confirmaria: uma amostra das mensagens na fila de rejeitadas mostrando, de fato, ausência do campo `unidade_medida`, ou uma mensagem de erro do consumidor citando esse campo especificamente.

---

## Avaliar — Escolher o mecanismo de entrega para um consumidor novo

**1. Critérios de julgamento e qual pesa mais**

Critérios: (a) capacidade de reprocessamento sob demanda — atende a Qualidade; (b) garantia de não perda para consumidores críticos — atende Faturamento; (c) operabilidade dada a equipe existente; (d) impacto de migração sobre consumidores que já funcionam. O critério que mais pesa é **(c) operabilidade** — porque o risco de errar nele não é "a Qualidade espera mais um pouco pelo indicador", é a equipe de duas pessoas, sem plantão noturno, operando algo que nunca operou e não conseguindo diagnosticar um incidente fora do horário. Um erro em (a) é inconveniente; um erro em (c) pode derrubar Faturamento, que é o consumidor que não pode perder nada.

**2. Os três mecanismos julgados contra os critérios**

- **Mecanismo 1 (fila dedicada, leitura remove).** Resolve dar à Qualidade seu próprio canal sem interferir nos consumidores existentes, mantendo a operação em algo que a equipe já sabe operar. Cobra que a fila, por natureza, não guarda histórico suficiente para o reprocessamento de três meses que a Qualidade precisa toda vez que um indicador muda — a fila resolve receber o que é novo, não reler o que já passou.
- **Mecanismo 2 (log com retenção de 90 dias, todos migram).** Resolve o reprocessamento de forma uniforme para os três consumidores de uma vez. Cobra a mudança mais arriscada das três: migrar Faturamento e Notificações — que já funcionam — para uma tecnologia que a equipe nunca operou, tudo de uma vez, sem necessidade comprovada de que os outros dois precisem dessa capacidade.
- **Mecanismo 3 (fila dedicada + cópia própria da Qualidade).** Resolve o reprocessamento sem migrar quem já funciona — a Qualidade ganha sua própria base para reprocessar, e a equipe de plataforma continua operando só o que já conhece. Cobra que a própria Qualidade mantenha essa cópia consistente e atualizada — o custo do reprocessamento sai da plataforma central e vai para quem precisa dele.

**3. O fato que elimina um mecanismo diretamente**

O fato 1 (Qualidade precisa reler três meses inteiros quando um indicador muda) elimina o **Mecanismo 1** diretamente: numa fila tradicional, a leitura remove a mensagem — não existe "reler" o que já foi consumido. Assim que a Qualidade lê uma mensagem, ela desaparece da fila; não há como recuperar os últimos três meses a partir dela.

**4. Parecer e impacto sobre os consumidores atuais**

Parecer: recomendo o **Mecanismo 3**. Faturamento e Notificações não precisam mudar nada — continuam recebendo pela mesma fila, do mesmo jeito de hoje, sem nenhum risco novo introduzido na operação deles.

**5. Objeção mais forte (considerando o fato 3) e resposta**

Objeção: se a Qualidade também depende da mesma equipe de plataforma de duas pessoas para manter sua cópia em banco, "empurrar a responsabilidade para a Qualidade" não elimina o problema de operar algo novo — só troca "operar um log com retenção" por "operar uma cópia com lógica de reprocessamento própria", que também é inédito. Resposta: mesmo sendo trabalho novo, o raio de impacto é muito menor e mais contido — um problema na cópia da Qualidade afeta só a Qualidade, que já está disposta a esperar por indicadores mensais, enquanto um problema na migração do Mecanismo 2 poderia afetar Faturamento, que não pode perder nenhum resultado. A objeção é válida, mas o custo de errar no "algo novo" é bem menor no Mecanismo 3.

---

## Criar — Propor a evolução do contrato de resultado

**1. Caminho escolhido e defesa citando duas restrições**

Escolho o **caminho 1** — acrescentar o campo novo na própria versão 1, como campo opcional. Isso atende a restrição 1 (o consumidor antigo só entende v1 e só tem janela de mudança em oito meses — um campo opcional na mesma v1 não exige que ele mude nada, nem agora nem depois) e a restrição 4 (só Compliance vai usar o campo novo — não há razão de negócio para os outros consumidores precisarem de um formato diferente, então criar uma v2 inteira serviria a necessidade de um único consumidor).

**2. Os dois caminhos não escolhidos — ganho e custo de cada um**

- **Caminho 2 (v2 em paralelo).** Ganharia uma trilha de evolução formalmente mais "limpa" — quem quiser o campo novo assina v2, quem não quiser fica em v1 sem perceber nada. Custaria manter dois formatos publicados simultaneamente por, no mínimo, oito meses, com o dobro de superfície de contrato para testar e documentar, para servir a necessidade de um único consumidor.
- **Caminho 3 (só v2 + tradutor para o legado).** Ganharia simplificar o lado da origem, que passaria a publicar um único formato — todo o peso de compatibilidade migraria para o tradutor. Custaria introduzir um componente novo no caminho crítico do consumidor legado, mantido por um fornecedor externo — qualquer defeito no tradutor quebra justamente o consumidor mais frágil e mais caro de corrigir depressa.

**3. Ordem das etapas, responsável por etapa, e quando desligar o consumidor antigo da v1**

- **Etapa 1** — equipe de Resultados (dona do evento) acrescenta o campo novo como opcional no schema da v1 e passa a publicá-lo preenchido em todo evento novo.
- **Etapa 2** — equipe de Compliance atualiza seu consumidor para ler o campo novo, já disponível desde a etapa 1, sem qualquer coordenação com os outros consumidores.
- **Etapa 3** — nenhuma ação é necessária da equipe do consumidor antigo nem da equipe de Faturamento, já que o formato deles nunca muda.

Como este caminho nunca cria uma segunda versão, não existe "consumidor antigo na v1" para desligar — a v1 nunca deixa de ser a única versão, então essa pergunta não se aplica aqui.

**4. Descarte de mensagem repetida durante a coexistência**

Como o caminho 1 nunca cria um segundo formato, não existe coexistência de duas versões do evento — o identificador do evento continua sendo emitido exatamente como já é hoje, sem qualquer mudança de mecanismo. Um evento, com ou sem o campo novo preenchido, ainda tem um único ID, e o descarte de repetição continua funcionando exatamente como antes, porque a estrutura do identificador não foi tocada.

**5. Sinal de que a transição terminou**

Como não há uma versão antiga para desligar neste caminho, o sinal equivalente de conclusão é: Compliance confirmar que o campo novo está presente e correto em 100% dos eventos consumidos por um período representativo (por exemplo, um mês fechado), sem nenhum evento pendente de processamento sem esse campo nas filas de Compliance.
