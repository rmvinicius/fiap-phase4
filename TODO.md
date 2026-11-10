# Etapa 1

## Provisionar os recursos no cluster:

* Prometheus | OK
* Loki       | OK
* Grafana    | OK
* Alloy      | OK
* Tempo      | OK

# Etapa 2

* Configurar os microserviços com opentelemetry e expor no alloy        | OK
* Configurar o datadog ou new relic em contas gratuitas for education

# Etapa 3

* No grafana ou APM, gerar alertas com taxas de erro 5xx maiores que 5%
* Criar uma conta no PagerDuty para abrir incidente automaticamente
* Notificar no slack ou discord
* Criar uma automação no github action ou aws lambda via webhook reiniciando o serviço após incidente

# Execuções

* Ajustado no terraform a labrole para o EKS
* Adicionado as senhas do banco nas secrets do github actions
* Adicionado as credenciais de autenticação na aws no github actions
* Criado a branch develop

* Provisionado o terraform
* Acessado a maquina EC2 e instalado o runner self-hosted
* Instalado o psql 17 client https://dev.to/johndotowl/postgresql-17-installation-on-ubuntu-2404-5bfi

* Criado o usuário para cadaa base auth_db / flags_db / targeting_db / grafana_db
    CREATE USER auth_service WITH PASSWORD '<senha>';
    GRANT ALL PRIVILEGES ON DATABASE auth_db TO auth_service;
    ALTER DATABASE auth_db OWNER TO auth_service;
    ALTER SCHEMA public OWNER TO auth_service;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO auth_service;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO auth_service;

* Executar script da base
    psql "host=$RDSHOST01 port=5432 dbname=auth_db user=auth_service" -f init.sql
    psql "host=$RDSHOST02 port=5432 dbname=flags_db user=flag_service" -f init.sql
    psql "host=$RDSHOST03 port=5432 dbname=targeting_db user=targeting_service" -f init.sql

* Instalar kubectl https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/

* Instalar awscli
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
    unzip awscliv2.zip
    sudo ./aws/install

* Copiar as credenciais aws -> ~/.aws/credentials

* Conectar no cluster: aws eks update-kubeconfig --region <region-code> --name <cluster-name>

* Criar storageclass local pois via lab aws nao é possível usar o gp3 ou gp2
    * Instalar o storageclass do rancher
        kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.30/deploy/local-path-storage.yaml
        kubect get pods -n local-path-storage

    * Configurar nos recursos que tem pvc o seguinte storageClass:
        storageClassName: local-path

* Executar as pipelines:
    * Micro service / ALL
    * Helm CI/CD
    * Install Keda
    * Install Ingress Nginx
    * Install Argo CD
    * Install Monitoring Stack

* Configurar ARGO CD
    * Acessar o argo cd pela url do load balancer/
        * A senha esta disponível: kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
    * Configurar o repositório:
        argocd repo add https://github.com/rmvinicius/fiap-phase3.git \
        --username <your-github-username> \
        --password <your-github-token> \
        --upsert

        Method 2: Via ArgoCD UI
        Settings → Repositories → Connect Repo
        Type: Git
        Repository URL: https://github.com/rmvinicius/fiap-phase3.git
        Username: Your GitHub username
        Password: Personal Access Token (PAT) with repo scope
        Click Connect

    * Executar a pipeline Deploy Gitops

* Configurar os serviços:
    * Atualizar no values.yaml de cada serviço
        * Url do ECR
        * Credenciais AWS
        * Url do SQS
        * Conexão com banco

* Sempres que iniciar o LAB:
    * Atualizar AWS Credentials nos microserviços
    * Atualizar as credenciais no github

* Validar as chamadas

-----

# Para o tech-challenge 4

* Criado Storage Class local-path

* Adicionado workflow para instalar stack de monitoramento

* Adicionado o addon kube-state-metrics e metrics-server no cluster

* Configurado o grafana com datasource tempo, loki e prometheus

* Criar dashboard com monitoramento do cluster = OK
* Criar dashboard com logs dos microserviços   = OK
* Criar dashboard com monitoramento das metricas dos microserviços = OK
* Plus: Adicionar o traceid no log para fazer o trace to log + log output em logback = OK

* Criar alerta no Grafana para taxa de erros 5xx do auth-service maior que 5%

    Acessar grafana > Alerting > Alert rules > New alert rule

    Selecionar: prometheus

    Consulta:

    (sum(rate(http_requests_total{status=~"5.."}[5m]))) /
    clamp_min(
    sum(rate(http_requests_total[5m])) + 1)

    Condição: Reduce → Last → is above → 0.05.
    Intervalo: 1m; For: 2m.
    Annotations: add summary, description, runbook_url.

    Notificações: 

    Contact points → Add contact point → PagerDuty
    Contact points → Add contact point → Slack
    Contact points → Add contact point → Webhook URL: http://grafana-github-relay.monitoring.svc.cluster.local/webhook

-----

# O que falta

* Utilizar secret da aws ao invés de secret do cluster
* Melhorar o dashboard do http status
* Criar o alert para cada serviço

* Criar conta no pagerduty e abrir um incidente automaticamente
* Configurar notificação para envio pro Slack, Discord ou teams
* Ao gerar um alerta, criar um automation runbook ou aws lambda para reiniciar o auth-service

* Instalar new relic gratuito
* Distributed tracing: Ao fazer uma requisição no evaluation-service, o APM deve mostrar o trace da requisição
* Service Map: o APM deve mostrar as dependencias dos 5 microserviços

# Evidências

* Código IaC/Gitops com a inclusão da stack de monitoramento
* Código fonte das aplicações com inclusão opentelemetry
* Script e automação para o automation runbook

* Print do Dashboard do Grafana.
* Print de um Trace distribuído no APM.
* Print da notificação de incidente no ChatOps.
* Print do log/execução da automação de Self-Healing.

