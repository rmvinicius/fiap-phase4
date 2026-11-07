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

# Execuções

* Ajustado no terraform a labrole para o EKS
* Adicionado as senhas do banco nas secrets do github actions
* Adicionado as credenciais de autenticação na aws no github actions
* Criado a branch develop

* Provisionado o terraform
* Acessado a maquina EC2 e instalado o runner self-hosted
* Instalado o psql 17 client https://dev.to/johndotowl/postgresql-17-installation-on-ubuntu-2404-5bfi

* Criado o usuário para a base auth_db
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

* Executar as pipelines:
    * Micro service / ALL
    * Helm CI/CD
    * Install Keda
    * Install Ingress Nginx
    * Install Argo CD

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

* Nova base para o grafana
    * Adicionado uma nova base no terraform, rds-dev-04 com database grafana_db
    * Configurar values.yaml do grafana-community helm chart
    * Criado o usuário para a base grafana_db
        CREATE USER grafana WITH PASSWORD '<senha>';
        GRANT ALL PRIVILEGES ON DATABASE grafana_db TO grafana;
        ALTER DATABASE grafana_db OWNER TO grafana;
        ALTER SCHEMA public OWNER TO grafana;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO grafana;
        ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO grafana;



# A fazer

* Tentar cria pvc local:

    Option 2: Use a Local Path Provisioner (For Dynamic PVC Testing)If your lab assignment specifically requires you to use a PVC (persistence.enabled: true), you can bypass AWS EBS completely by installing the Rancher Local Path Provisioner. It provisions storage directly onto the local worker node's disk without needing any AWS IAM permissions.
    
    1.Install Local Path Provisioner:Kubernetes Cluster.Apply the open-source provisioner manifest to your cluster:
    
    kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.30/deploy/local-path-storage.yaml

    Verification: Run kubectl get pods -n local-path-storage to ensure the provisioner pod is running.
    
    2.Set as Default Storage Class:Kubernetes Cluster.Make this local provisioner the default storage class for your cluster so PVCs bind to it automatically:
    
    kubectl patch storageclass local-path -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
    
    Verification: 
    
    Run kubectl get storageclass and check that local-path has (default) next to its name.
    
    3.Configure Storage Class in Helm:Grafana Helm Values.Update your Grafana values to explicitly request the local storage class:YAML
    
    persistence:
        enabled: true
        type: pvc
        storageClassName: local-path
        accessModes:
            - ReadWriteOnce
        size: 10Gi

    Verification: 
    
    Run kubectl get pvc after installing the chart and confirm the PVC status changes from Pending to Bound.

* Adicionar o addon kube-state-metrics no cluster

