# Nota de evidências — Oficina de eventos (Módulo 5)

Todos os comandos abaixo foram executados de verdade, não simulados. Uma adaptação de ambiente: o container `rabbitmq:4-management` do Docker Hub não estava acessível na minha rede, então instalei um RabbitMQ 3.12.1 nativo via `apt` (pacote oficial do Ubuntu) em vez do Compose. Funcionalmente é o mesmo broker (AMQP 0-9-1 + plugin de management); a única diferença prática são as portas nativas — AMQP em `5672` e management em `15672` — em vez do remapeamento `15672`/`15673` que o `compose.eventos.yml` usa para desfazer a tradução de porta do Docker. `RABBITMQ_URL` e `RABBITMQ_MANAGEMENT_PORT` foram ajustados de acordo; nenhum código da oficina foi alterado.

IDs usados são todos sintéticos, iguais aos do próprio enunciado (`3fa85f64-5717-4562-b3fc-2c963f66afa6` e `65e95d82-4f8c-4e93-9bb3-3e0e92deaf1d`).

## Configuração validada

```
$ python3 -c "import yaml; yaml.safe_load(open('infra/compose.eventos.yml')); print('YAML valido')"
YAML valido

$ .venv/bin/python --version
Python 3.12.3

$ .venv/bin/python -c "import aio_pika, pydantic; print(aio_pika.__version__, pydantic.VERSION)"
10.0.1 2.13.5

$ rabbitmqctl status  →  RabbitMQ version: 3.12.1, nó rabbit@vm, management plugin habilitado (HTTP 200 em /api/overview)
```

## Saídas processed=True attempts=1 e processed=False attempts=2

```
=== 1a publicacao ===
Publicado: ResultadoLaboratorialDisponibilizado.v1 event_id=3fa85f64-5717-4562-b3fc-2c963f66afa6
=== 1o consumo ===
ResultadoLaboratorialDisponibilizado.v1 event_id=3fa85f64-5717-4562-b3fc-2c963f66afa6 processed=True attempts=1
=== 2a publicacao, mesmo event_id ===
Publicado: ResultadoLaboratorialDisponibilizado.v1 event_id=3fa85f64-5717-4562-b3fc-2c963f66afa6
=== 2o consumo ===
ResultadoLaboratorialDisponibilizado.v1 event_id=3fa85f64-5717-4562-b3fc-2c963f66afa6 processed=False attempts=2
```

Testes automatizados (offline, sem broker): `2 passed, 1 skipped in 0.15s` — o único pulado é o que exige `COMPOSE_LIVE=1`.

## Consulta de um efeito

```
$ python -c "...select event_id, attempts from processed_events...; ...select count(*) from billing_effects..."
[('3fa85f64-5717-4562-b3fc-2c963f66afa6', 2)]
(1,)
```

Uma única identidade, duas tentativas registradas, **um** efeito de negócio gravado — exatamente a assinatura que a oficina pede.

## Mensagem na DLQ

```
$ curl -u guest:guest http://localhost:15672/api/queues/%2F/billing.resultados.v1.dlq
{
  "name": "billing.resultados.v1.dlq",
  "messages": 1,
  "messages_ready": 1
}
```

O consumidor imprimiu `Mensagem rejeitada para DLQ: schema inválido (1 erro)` ao processar o evento publicado com `--invalid` (sem `result_reference`), e a fila `billing.resultados.v1.dlq` confirma 1 mensagem retida. O teste ao vivo, que percorre publicação → validação → rejeição → DLX → DLQ de ponta a ponta, fechou com `3 passed in 0.18s`.

*Nota de bastidor: a primeira consulta HTTP que fiz caiu bem no meio do ciclo de agregação de estatísticas do management (que atualiza a cada poucos segundos) e mostrou `messages: 0` por um instante — daí a importância do retry com espera que o próprio teste automatizado já implementa, em vez de confiar numa única leitura pontual.*

## Por que há entrega pelo menos uma vez com idempotência, e não exactly-once

O broker garante que uma mensagem publicada com sucesso **não se perde** — no mínimo, ela chega uma vez. Ele não garante que chega **exatamente** uma vez, porque não tem visibilidade do que acontece do lado do consumidor: se o consumidor processar e cair antes de confirmar, o RabbitMQ não sabe que o trabalho já foi feito e reentrega por precaução. É por isso que a garantia nativa do broker é "pelo menos uma vez" — a entrega repetida é o preço de nunca perder uma mensagem diante de falhas ambíguas.

**Exactly-once** exigiria coordenar atomicamente a confirmação ao broker com o efeito gravado no consumidor — algo que uma transação distribuída resolveria, mas que nenhum dos dois lados garante sozinho. A idempotência não elimina a entrega repetida (ela continua acontecendo, como a evidência acima mostra: `attempts=2`); ela neutraliza o *efeito* da repetição, garantindo que o segundo processamento do mesmo `event_id` não gere um segundo lançamento em `billing_effects`. Entrega repetida com efeito único **parece** exactly-once do ponto de vista de negócio, mas é, por baixo, "pelo menos uma vez" mais uma tabela de deduplicação — não uma garantia do protocolo de mensageria.

## Onde Kafka valeria como extensão, sem substituir o desenho atual

O desenho atual (RabbitMQ com fila de trabalho por consumidor) atende bem este caso porque há um único consumidor de faturamento e a necessidade é entrega confiável, não reprocessamento histórico. Kafka valeria como extensão especificamente se aparecesse uma exigência que este desenho não tem: **múltiplos grupos de consumidores independentes precisando reler os mesmos resultados por um período retido** — por exemplo, se Auditoria e uma futura área de Qualidade precisarem, cada uma no seu próprio ritmo, reprocessar os últimos 90 dias de resultados sempre que uma regra de negócio mudar. Uma fila tradicional remove a mensagem na leitura; um log com retenção permite isso sem tirar nada dos consumidores existentes. Continua sendo necessário `event_id`, idempotência e versão de contrato de qualquer forma — Kafka resolve retenção e replay, não substitui a decisão de deduplicação que já está no `ProcessedEventStore`.
