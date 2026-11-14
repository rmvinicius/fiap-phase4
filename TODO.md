# Etapa 1

## Provisionar os recursos no cluster:

* [OK] Prometheus
* [OK] Loki
* [OK] Grafana
* [OK] Alloy
* [OK] Tempo

# Etapa 2

* [OK] Configurar os microserviços com opentelemetry e expor no alloy
* Configurar o datadog ou new relic em contas gratuitas for education -> Não precisa

# Etapa 3

* [OK] No grafana ou APM, gerar alertas com taxas de erro 5xx maiores que 5%
* [OK] Criar uma conta no PagerDuty para abrir incidente automaticamente
* [OK] Notificar no slack ou discord
* [OK] Criar uma automação no github action ou aws lambda via webhook reiniciando o serviço após incidente

# Execuções

* Preparar o repositório para o terraform
    Criado a branch develop
    Ajustado no terraform a labrole para o EKS
    Criar bucket s3 para estado do terraform
    Criar a chave key para EC2
    Adicionado as senhas do banco nas secrets do github actions
    Adicionado as credenciais de autenticação na aws no github actions
    Provisionado o terraform

* Acessado a maquina EC2 e instalado o runner self-hosted
* Instalado o psql 17 client https://dev.to/johndotowl/postgresql-17-installation-on-ubuntu-2404-5bfi

* Criado o usuário para cada base auth_db / flags_db / targeting_db / grafana_db
    CREATE USER auth_db WITH PASSWORD '<senha>';
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

* Instalar k9s https://dev.to/dm8ry/how-to-install-k9s-on-ubuntu-a-step-by-step-guide-2f98

* Criar storageclass local pois via lab aws nao é possível usar o gp3 ou gp2
    * Instalar o storageclass do rancher
        kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.30/deploy/local-path-storage.yaml
        kubectl get pods -n local-path-storage

    * Configurar nos recursos que tem pvc o seguinte storageClass:
        storageClassName: local-path

* Configurar os serviços:
    * Atualizar no values.yaml de cada serviço
        * Url do ECR
        * Credenciais AWS
        * Url do SQS
        * Conexão com banco

* Executar as pipelines:
    * Helm CI/CD
    * Micro service / ALL
    * Install Keda
    * Install Argo CD
    * Install Monitoring Stack
    * Install Ingress Nginx

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

* Sempres que iniciar o LAB:
    * Atualizar AWS Credentials nos microserviços
    * Atualizar as credenciais no github
    * Atualizar a secret do github-webhook direto no cluster
    * remover os PVCs e redeployar o grafana e prometheus

* Validar as chamadas

-----

# Para o tech-challenge 4

* Criado Storage Class local-path

* Adicionado workflow para instalar stack de monitoramento

* Adicionado o addon kube-state-metrics e metrics-server no cluster

* Configurado o grafana com datasource tempo, loki e prometheus

* Criado dashboard com monitoramento do cluster
* Criado dashboard com logs dos microserviços
* Criado dashboard com monitoramento das metricas dos microserviços
* Plus: Adicionado o traceid no log para fazer o trace to log + log output em logback

* Criado conta/configurar o PagerDuty
    * Criar o service e gerar token
        https://cresol-teste.pagerduty.com/
    
* Criado conta/configurar slack

* Criado webhook.site para teste

* Retirado sync do argocd na secret do github-webhook para não expor o TOKEN do github actions

* Criado o microserviço "github-webhook" para servir como middleware de integração entre o trigger do alert rules com github actions
    * Retirado sync do argocd na secret do github-webhook para não expor o TOKEN do github actions

* Criado workflow para reinicio dos serviços via dispatch

* Criado alerta no Grafana para taxa de erros 5xx do auth-service maior que 5%

    Acessar grafana > Alerting > Alert rules > New alert rule

    Nome: Go Applications (5xx Error) | Python Applications (5xx Error)
    Query: prometheus

    # Go applications
    sum by(app) (rate(http_requests_total{app!="",status=~"5.."}[5m])) / (sum by(app) (rate(http_requests_total[5m]) + 1))

    # Python applications
    sum by(app) (rate(flask_http_requests_total{app!="",status=~"5.."}[5m])) / (sum by(app) (rate(flask_http_requests_total[5m]) + 1))

    Condição: When Query is above → 0.05.

    Add folder and labels: HTTP Alerts / Labels empty
    Evaluation behavior: microservices
    Intervalo: 1m; For: 2m.

    Notificações: 
        Contact points → Integrations

    ** Necessário criar um contact point adicionando todas as integrações
        Alerting > Notification configuration > + New contacting point
            Name: integrations
                Webhook | Url: http://github-webhook-svc.monitoring.svc.cluster.local:8080/webhook
                Webhook | Url: https://webhook.site/e3c7c031-68f7-4a51-801a-d73cb50cd825
                PagerDuty | $Token
                Slack | Recipient: #incidents | Webhook Url: $webhook

-----

# O que falta

* Melhorar o dashboard do http status

* Verificar o trace distribuido, o span esta aparecendo apenas a chamada, e nao aparece banco, redis...

* Distributed tracing: Ao fazer uma requisição no evaluation-service, o APM deve mostrar o trace da requisição

* Service Map: o APM deve mostrar as dependencias dos 5 microserviços

* Instalar new relic gratuito -> Não precisa

# Evidências

* Código IaC/Gitops com a inclusão da stack de monitoramento
* Código fonte das aplicações com inclusão opentelemetry
* Script e automação para o automation runbook

* Print do Dashboard do Grafana.
* Print de um Trace distribuído no APM.
* Print da notificação de incidente no ChatOps.
* Print do log/execução da automação de Self-Healing.