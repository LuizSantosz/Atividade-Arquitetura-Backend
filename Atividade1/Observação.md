# Observações — Unidade 1

# Experimento 1 — Camadas
Condição alterada: Modifiquei a resposta de uma camada para gerar conflito
Evidência: saída mostrou conflito de respostas HTTP.
Responsabilidade: a separação em camadas evidenciou onde o erro foi tratado.

# Experimento 2 — Pipes and Filters
Condição alterada: aumentei o orçamento da vaga
Evidência: saída antes mostrava descarte/reprovação; saída depois mostrou mais aprovados e ranking diferente.
Responsabilidade: os filtros (testers, transformers, consumer) evidenciaram descarte e ranking.

# Experimento 3 — Microkernel
Condições alteradas:
Tabela de frete (SP=50, RJ=30, MG=10, RS=40, BA=65).
ICMS-RJ de 20% para 25%.
ICMS-SP padrão de 18% para 30%.
Evidência: saída depois mostrou impostos maiores e frete alterado; notificação exibiu total atualizado.
Responsabilidade: plugins de impostos e frete contribuíram conforme o contrato; ordem de categorias garantiu que a notificação refletisse o valor final correto.
