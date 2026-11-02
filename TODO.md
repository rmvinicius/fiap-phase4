# Etapa 1

## Provisionar os recursos no cluster:

* Prometheus
* Loki
* Grafana
* Alloy

# Etapa 2

* Cconfigurar os microserviços com opentelemetry e expor no alloy
* Configurar o datadog ou new relic em contas gratuitas for education

# Etapa 3

* No grafana ou APM, gerar alertas com taxas de erro 5xx maiores que 5%
* Criar uma conta no PagerDuty para abrir incidente automaticamente
* Notificar no slack ou discord
* Criar uma automação no githubaction ou aws lambda via webhook reiniciando o serviço após incidente
