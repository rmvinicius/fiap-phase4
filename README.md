# Fiap Phase 3 - Toggle Master

Projeto desenvolvido para o **Tech Challenge da FIAP (Fase 3)**, implementando uma arquitetura de microserviços baseada em Kubernetes (EKS) na AWS, com deploy automatizado via CI/CD utilizando GitOps (ArgoCD).

## Visão Geral

O **Toggle Master** é uma plataforma de *feature flags* e *targeting* que permite o gerenciamento dinâmico de funcionalidades em aplicações. A arquitetura é composta por cinco microserviços organizados em camadas:

| Microserviço | Linguagem | Banco de Dados | Descrição |
|---|---|---|---|
| **auth-service** | Go | RDS PostgreSQL (`auth_db`) | Autenticação e autorização de usuários |
| **flag-service** | Python (Flask) | RDS PostgreSQL (`flags_db`) | Criação e gerenciamento de feature flags |
| **targeting-service** | Python (Flask) | RDS PostgreSQL (`targeting_db`) | Regras de targeting e segmentação de usuários |
| **evaluation-service** | Go | Redis (cache) | Avaliação de flags e envio de eventos para SQS |
| **analytics-service** | Python (Flask) | DynamoDB | Processamento e análise de eventos de uso |

## Estrutura do Projeto

```
fiap-phase3/
├── terraform/          # Infraestrutura como código (AWS)
├── ms/                 # Microserviços da aplicação
├── helm/               # Charts Helm para Kubernetes
├── gitops/             # Configurações GitOps (ArgoCD)
├── eks/                # Manifestos e configurações do cluster EKS
├── .github/            # Workflows do GitHub Actions (CI/CD)
└── README.md           # Este arquivo
```

---

## terraform/

**Infraestrutura como Código (IaC)** utilizando Terraform para provisionar toda a infraestrutura na AWS (região `us-east-1`).

### Estrutura

```
terraform/
├── backend.tf                  # Configuração do backend (S3)
├── version.tf                  # Restrições de versão do Terraform e providers
├── provider.tf                 # Configuração do provider AWS
├── main.tf                     # Módulo raiz: instancia todos os módulos filhos
├── variables.tf                # Variáveis de entrada
├── outputs.tf                  # Outputs exportados
├── Dockerfile                  # Imagem Docker para testes locais
├── bootstrap/
│   └── remote/
│       └── dev-backend.tfvars  # Configuração de state remoto (S3)
├── environment/
│   └── dev.tfvars              # Valores das variáveis para ambiente DEV
├── modules/
│   ├── network/                # VPC, subnets, IGW, NAT, security groups
│   ├── ec2/                    # Instância EC2 para gerenciar eks + runner github actions
│   ├── sqs/                    # Fila SQS com dead-letter queue
│   ├── rds/                    # Instâncias RDS PostgreSQL (3 bancos)
│   ├── eks/                    # Cluster EKS com node groups gerenciados
│   ├── dynamodb/               # Tabela DynamoDB para analytics
│   ├── redis/                  # Cache ElastiCache Serverless (Redis)
│   └── ecr/                    # Repositórios ECR para imagens Docker
├── README.md                   # Documentação detalhada do Terraform
└── TODO.md                     # Instruções de uso (S3 + DynamoDB)
```

### Módulos

| Módulo | Recursos Criados | Principais Outputs |
|---|---|---|
| `network` | VPC, subnets (públicas, privadas, EKS, RDS), IGW, NAT Gateway, Elastic IP, tabelas de rotas, security groups | `vpc_id`, `subnet_ids`, `eks_subnet_ids`, `rds_subnet_ids`, `sg_private_id`, `sg_public_id` |
| `ec2` | Instância EC2 | `ec2_id`, `ec2_public_ip` |
| `sqs` | Fila SQS principal + dead-letter queue (DLQ) | `sqs_id` (URL da fila) |
| `rds` | 3 instâncias RDS PostgreSQL (`auth_db`, `flags_db`, `targeting_db`) | `database_endpoints`, `database_arns` |
| `eks` | Cluster EKS + node groups gerenciados + roles IAM | `cluster_endpoint`, `cluster_name`, `cluster_certificate_authority` |
| `dynamodb` | Tabela DynamoDB (`ToggleMasterAnalytics`) | — (ARN/ID acessível via recurso) |
| `redis` | Cache ElastiCache Serverless (Redis) | `redis_endpoint` |
| `ecr` | Repositórios ECR para imagens Docker | `ecr_repository_urls` |

### Fluxo de Deploy

1. **Bootstrap**: criar bucket S3 para state e lock
2. **Init**: inicializar backend com `dev-backend.tfvars`
3. **Plan/Apply**: validar e aplicar com as variáveis de `dev.tfvars`

### GitHub Actions

- `terraform-ci.yml` — `plan` e `apply` automáticos
- `terraform-destroy.yml` — destruição da infraestrutura

### Secrets do GitHub

| Secret | Descrição |
|---|---|
| `AWS_ACCESS_KEY_ID_DEV` | Access key da AWS para DEV |
| `AWS_SECRET_ACCESS_KEY_DEV` | Secret key da AWS para DEV |
| `AWS_SESSION_TOKEN_DEV` | Session token (credenciais temporárias) |
| `RDS_PASSWORD_AUTH_DB_DEV` | Senha do banco `auth_db` |
| `RDS_PASSWORD_FLAGS_DB_DEV` | Senha do banco `flags_db` |
| `RDS_PASSWORD_TARGETING_DB_DEV` | Senha do banco `targeting_db` |

---

## ms/

**Microserviços** da aplicação Toggle Master, organizados por pasta. Cada serviço é independente, possui seu próprio `Dockerfile`, arquivo `.env` e configurações de deploy.

### Estrutura

```
ms/
├── analytics-service/          # Python/Flask — processamento de eventos
├── auth-service/               # Go — autenticação e autorização
├── evaluation-service/         # Go — avaliação de flags e envio para SQS
├── flag-service/               # Python/Flask — gerenciamento de feature flags
└── targeting-service/          # Python/Flask — regras de targeting
```

### Detalhes por Serviço

#### analytics-service
- **Linguagem**: Python 3.11 (Flask)
- **Banco**: DynamoDB
- **Estrutura**:
  - `app.py` — aplicação Flask
  - `requirements.txt` — dependências Python
  - `Dockerfile` — imagem Docker do serviço
  - `deploy/values.yaml` — valores do Helm para deploy
  - `tests/` — testes unitários

#### auth-service
- **Linguagem**: Go 1.25
- **Banco**: RDS PostgreSQL (`auth_db`)
- **Estrutura**:
  - `main.go` — ponto de entrada
  - `handlers.go` — handlers HTTP
  - `key.go` — manipulação de chaves JWT
  - `go.mod` / `go.sum` — dependências Go
  - `db/` — scripts de migração/inicialização do banco
  - `Dockerfile` — imagem Docker
  - `deploy/values.yaml` — valores do Helm

#### evaluation-service
- **Linguagem**: Go 1.25
- **Banco**: Redis (cache), SQS (mensageria)
- **Estrutura**:
  - `main.go` — ponto de entrada
  - `handlers.go` — handlers HTTP
  - `evaluator.go` — lógica de avaliação de flags
  - `types.go` — definições de tipos
  - `sqs.go` — integração com SQS
  - `Dockerfile` — imagem Docker
  - `deploy/values.yaml` — valores do Helm

#### flag-service
- **Linguagem**: Python 3.11 (Flask)
- **Banco**: RDS PostgreSQL (`flags_db`)
- **Estrutura**: idêntica ao `analytics-service`

#### targeting-service
- **Linguagem**: Python 3.11 (Flask)
- **Banco**: RDS PostgreSQL (`targeting_db`)
- **Estrutura**: idêntica ao `analytics-service`

### GitHub Actions

- `template-python.yml` — workflow reutilizável para serviços Python
- `template-go.yml` — workflow reutilizável para serviços Go
- `microservice.yml` — workflow orquestrador que detecta mudanças e dispara builds

---

## helm/

**Charts Helm** para deploy de microserviços no Kubernetes.

### Estrutura

```
helm/
└── microservice/
    ├── Chart.yaml        # Metadados do chart (nome, versão, appVersion)
    ├── values.yaml       # Valores de configuração padrão
    └── templates/        # Templates Kubernetes (Deployment, Service, HPA, etc.)
```

### chart `microservice`

Chart genérico reutilizável para todos os microserviços. Configure-o sobrescrevendo os valores em `deploy/values.yaml` de cada serviço.

#### Configurações principais (`values.yaml`)

| Chave | Descrição |
|---|---|
| `name` | Nome do microserviço |
| `namespace` | Namespace Kubernetes (`application`) |
| `port` | Porta do container |
| `replicas` | Número de réplicas iniciais |
| `resources` | Limites e requests de CPU/memória |
| `image` | Repositório, nome da imagem e tag (ECR) |
| `configmap` | Variáveis de ambiente configuráveis |
| `secrets` | Secrets do Kubernetes (injetados no container) |
| `probes` | Configurações de liveness, readiness e startup probes |
| `service.type` | Tipo de serviço Kubernetes (`ClusterIP`) |
| `hpa` | Horizontal Pod Autoscaler (CPU/memória) |
| `keda` | Auto-scaling baseado em eventos SQS (fila de mensagens) |

---

## gitops/

**GitOps** — configurações do ArgoCD para deploy automatizado dos microserviços.

### Estrutura

```
gitops/
└── argocd/
    └── applications/
        ├── analytics-service.yaml
        ├── auth-service.yaml
        ├── evaluation-service.yaml
        ├── flag-service.yaml
        └── targeting-service.yaml
```

### Application Manifests

Cada arquivo YAML define uma **Application do ArgoCD** que sincroniza automaticamente os microserviços do repositório Git com o cluster Kubernetes. Cada application referencia:

- O repositório Git de origem
- O caminho do chart Helm (`helm/microservice`)
- O arquivo `deploy/values.yaml` específico de cada microserviço
- O namespace de destino (`application`)

---

## eks/

**Configurações complementares do cluster EKS** — manifestos e configurações para componentes instalados no cluster.

### Estrutura

```
eks/
├── argo-cd/
│   ├── README.md       # Documentação da instalação do ArgoCD
│   └── values.yaml     # Valores customizados do Helm chart do ArgoCD
├── ingress-nginx/
│   ├── README.md       # Documentação do ingress-nginx
│   ├── values.yaml     # Valores do ingress-nginx
│   ├── argocd-ingress.yaml    # Ingress para o serviço ArgoCD
│   ├── microservice-ingress.yaml   # Ingress para os microserviços
│   └── route-service.yaml     # Configuração de Route Service (Service)
├── keda/
│   └── README.md       # Documentação do KEDA (auto-scaling)
└── TODO.md             # Instruções de setup (self-hosted runner, repo ArgoCD)
```

### Componentes

| Pasta | Componente | Descrição |
|---|---|---|
| `argo-cd` | Argo CD | Ferramenta GitOps para deploy contínuo no Kubernetes |
| `ingress-nginx` | NGINX Ingress Controller | Gerencia acesso HTTP/S externo aos serviços |
| `keda` | KEDA | Auto-scaling baseado em eventos (SQS, CPU, memória) |

### Setup

Veja `eks/TODO.md` para instruções de:
- Configuração de self-hosted runner no EKS
- Conexão do ArgoCD com o repositório Git (via CLI ou UI)

---

## .github/

**Workflows do GitHub Actions** — pipeline de CI/CD completo.

### Estrutura

```
.github/
└── workflows/
    ├── microservice.yml         # Orquestrador: build de todos os microserviços
    ├── template-python.yml      # Workflow reutilizável: build + deploy Python
    ├── template-go.yml          # Workflow reutilizável: build + deploy Go
    ├── terraform-ci.yml         # CI/CD: plan + apply do Terraform
    ├── terraform-destroy.yml    # CI/CD: destroy do Terraform
    ├── helm-ms.yml              # Deploy de Helm charts
    ├── gitops.yml               # Sincronização GitOps
    ├── argo-cd-install.yml      # Instalação do ArgoCD no EKS
    ├── ingress-nginx.yml        # Instalação do ingress-nginx
    └── keda.yml                 # Instalação do KEDA
```

### Pipeline de Microserviços

1. **`microservice.yml`** (orquestrador) — detecta quais serviços tiveram mudanças (via `paths-filter`) e dispara os workflows reutilizáveis.
2. **`template-python.yml`** — build da imagem Docker, push para ECR, deploy via Helm no ambiente correspondente (`develop` → DEV, `staging` → STG, `main` → PRD).
3. **`template-go.yml`** — mesmo fluxo para serviços em Go.

### Pipeline de Infraestrutura

4. **`terraform-ci.yml`** — `terraform fmt`, `validate`, `plan` e `apply` automáticos no branch `develop`.
5. **`terraform-destroy.yml`** — `terraform destroy` para limpeza de recursos.

### Pipeline de Componentes EKS

6. **`argo-cd-install.yml`** — instalação/atualização do ArgoCD via Helm.
7. **`ingress-nginx.yml`** — instalação/atualização do NGINX Ingress Controller.
8. **`keda.yml`** — instalação/atualização do KEDA.
9. **`gitops.yml`** — sincronização de aplicações ArgoCD.
10. **`helm-ms.yml`** — deploy de manifests Helm para microserviços.

---

## Detalhamento dos Workflows (CI/CD)

### microservice.yml — Orquestrador de Microserviços

Workflow orquestrador que detecta quais microserviços tiveram alterações e dispara os builds apropriados.

**Gatilhos**: `push` ou `pull_request` para `develop`, `staging`, `main`; ou `workflow_dispatch` manual.

**Resolução de ambiente**:
| Branch | Ambiente |
|---|---|
| `develop` | DEV |
| `staging` | STG |
| `main` | PRD |

**Etapas**:
1. **Checkout** — clona o repositório com histórico completo (`fetch-depth: 0`).
2. **Resolve environment** — mapeia o branch para DEV/STG/PRD.
3. **Set ECR registry** — obtém o registry do ECR da secret `ECR_REGISTRY`.
4. **Filter changed paths** — usa `dorny/paths-filter` para detectar quais serviços sofreram alteração.
5. **Jobs paralelos** — para cada microserviço alterado, dispara o workflow reutilizável (`template-python.yml` para serviços Python, `template-go.yml` para serviços Go), passando como parâmetros: `service-name`, `working-dir`, `environment`, `push-image` (true apenas no `main`), `ecr-registry`, e versão da linguagem.

### template-python.yml — Build de Microserviços Python

Workflow reutilizável (`workflow_call`) para serviços em Python (analytics-service, flag-service, targeting-service).

**Etapas**:
1. **Checkout** — clona o repositório.
2. **Setup Python** — instala a versão especificada (padrão 3.12) com cache de dependências.
3. **Install dependencies** — `pip install -r requirements.txt`.
4. **Lint (ruff)** — análise estática de código.
5. **SAST (bandit)** — escaneamento de vulnerabilidades de segurança em código Python.
6. **SCA (trivy fs)** — escaneamento de vulnerabilidades em dependências do filesystem.
7. **Test (pytest)** — execução de testes unitários.
8. **Configure AWS** — configurado com credenciais baseadas no ambiente (DEV/STG/PRD).
9. **Login to ECR** — autenticação no Amazon ECR.
10. **Build Image** — `docker build` com tag `v1.0.0-${SHA}-${ENV}`.
11. **Scan image vulnerabilities (trivy)** — escaneamento de vulnerabilidades na imagem Docker.
12. **Push Image** — envio da imagem para o ECR.
13. **Update Image Tag in values.yaml** — atualiza a tag da imagem no arquivo `deploy/values.yaml` do serviço e faz push do commit (com retry de 3 tentativas em caso de conflito).

### template-go.yml — Build de Microserviços Go

Workflow reutilizável (`workflow_call`) para serviços em Go (auth-service, evaluation-service).

**Etapas** (equivalentes ao template Python, adaptadas para Go):
1. **Checkout** — clona o repositório.
2. **Setup Go** — instala a versão especificada (padrão 1.23) com cache de módulos.
3. **Download modules** — `go mod tidy` e `go mod download`.
4. **Lint (golangci-lint)** — análise estática de código Go.
5. **SAST (gosec)** — escaneamento de vulnerabilidades de segurança em código Go.
6. **SCA (trivy fs)** — escaneamento de vulnerabilidades em dependências.
7. **Test** — `go test ./...`.
8. **Configure AWS** — credenciais AWS baseadas no ambiente.
9. **Login to ECR** — autenticação no ECR.
10. **Build Image** — `docker build` com tag `v1.0.0-${SHA}-${ENV}`.
11. **Scan image vulnerabilities (trivy)** — escaneamento de vulnerabilidades na imagem.
12. **Push Image** — envio para o ECR.
13. **Update Image Tag in values.yaml** — atualização da tag no `deploy/values.yaml` e push do commit (com retry).

### terraform-ci.yml — CI/CD do Terraform

Workflow para provisionamento automático da infraestrutura AWS via Terraform.

**Gatilhos**: `push` ou `pull_request` para `develop`, `staging`, `main` (apenas se arquivos em `terraform/**` mudarem); ou `workflow_dispatch` manual.

**Job `terraform-plan`** (executado em todos os gatilhos):
1. **Checkout** — clona o repositório.
2. **Resolve environment** — mapeia branch/environment para DEV/STG/PRD e converte para lowercase.
3. **Setup Terraform** — instala o Terraform via `hashicorp/setup-terraform@v3`.
4. **Configure AWS** — credenciais dinâmicas via `secrets[format('AWS_ACCESS_KEY_ID_{0}', ENV)]`.
5. **Tflint** — instala, inicializa e valida o linter (`continue-on-error: true`).
6. **Checkov** — escaneamento de segurança CIS para Terraform (`continue-on-error: true`).
7. **Format Check** — `terraform fmt -check -recursive`.
8. **Init** — `terraform init` com backend config dinâmico (`bootstrap/remote/${ENV_LOWER}-backend.tfvars`).
9. **Validate** — `terraform validate`.
10. **Plan** — `terraform plan` com variáveis de senha do RDS injetadas como `TF_VAR_rds_password_*` (secrets). Salva o plano como artefato (`tfplan`).

**Job `terraform-apply`** (executado **apenas** em `workflow_dispatch` manual, após `terraform-plan`):
1. **Checkout** — clona o repositório.
2. **Resolve environment** — usa o input manual do `workflow_dispatch`.
3. **Setup Terraform** + **Configure AWS** — mesmos passos do plan.
4. **Init** — inicializa o backend.
5. **Download tfplan artifact** — baixa o plano salvo pelo job anterior.
6. **Apply** — `terraform apply -auto-approve tfplan` executa o plano validado.

### terraform-destroy.yml — Destruição da Infraestrutura

Workflow para destruição seletiva da infraestrutura via Terraform (execução manual).

**Gatilho**: `workflow_dispatch` apenas (exige input de ambiente: DEV/STG/PRD).

**Etapas**:
1. **Checkout** — clona o repositório.
2. **Resolve environment** — converte o input para lowercase.
3. **Setup Terraform** — instala o Terraform.
4. **Configure AWS** — credenciais do ambiente selecionado.
5. **Init** — `terraform init` com backend dinâmico.
6. **Plan destroy** — `terraform plan -destroy` gera e salva o plano de destruição (`tfplan-destroy`).
7. **Apply destroy** — `terraform apply -auto-approve tfplan-destroy` destrói todos os recursos.

### helm-ms.yml — CI/CD dos Charts Helm

Workflow para lint, versionamento e publicação do chart Helm no ECR (como OCI registry).

**Gatilhos**: `push` ou `pull_request` para `develop`, `staging`, `main` (apenas se arquivos em `helm/**` mudarem); ou `workflow_dispatch`.

**Job `changes`**:
1. **Checkout** — clona com histórico completo.
2. **Resolve environment** — mapeia branch para DEV/STG/PRD.

**Job `lint`** (necessita de `changes`):
3. **Checkout** — clona o repositório.
4. **Setup Helm** — instala Helm v3.14.4.
5. **Lint chart** — `helm lint .` dentro de `helm/microservice`.

**Job `push`** (necessita de `lint` e `changes`):
6. **Checkout** — clona o repositório.
7. **Setup Helm** — instala Helm v3.14.4.
8. **Configure AWS** — credenciais do ambiente.
9. **Login to ECR** — autenticação no ECR.
10. **Package and Push Helm Chart**:
    - Lê nome e versão do `Chart.yaml` via `yq`.
    - Faz login no registry Helm via `helm registry login`.
    - Empacota o chart: `helm package .`.
    - Publica como OCI: `helm push <chart>.tgz oci://<REGISTRY>/helm`.

### gitops.yml — Sincronização GitOps

Workflow para aplicar os manifests Git do ArgoCD no cluster EKS.

**Gatilhos**: `push` ou `pull_request` para `develop`, `staging`, `main` (apenas se arquivos em `gitops/argocd/applications/**` mudarem); ou `workflow_dispatch`.

**Job `changes`**:
1. **Checkout** — clona com histórico completo.
2. **Resolve environment** — mapeia branch para DEV/STG/PD.

**Job `install-gitops`** (necessita de `changes`):
3. **Runs-on**: `[self-hosted, eks, private]` — runner self-hosted dentro do cluster EKS (conforme configurado em `eks/TODO.md`).
4. **Checkout** — clona o repositório.
5. **Configure AWS** — credenciais do ambiente.
6. **Setup Helm** — instala Helm v3.14.4.
7. **Configure kubectl for EKS** — `aws eks update-kubeconfig` usando o nome do cluster da secret `EKS_CLUSTER_NAME_${ENV}`.
8. **Verify Connection** — `kubectl get nodes` para confirmar conectividade.
9. **Install Gitops** — `kubectl apply -f gitops/argocd/applications/` aplica todas as Application manifests do ArgoCD no cluster.

---

### Fluxo de Secrets do GitHub

Todos os workflows resolvem dinamicamente as credenciais baseadas no ambiente:

```
secrets[format('AWS_ACCESS_KEY_ID_{0}', ENV)]       # DEV / STG / PRD
secrets[format('AWS_SECRET_ACCESS_KEY_{0}', ENV)]
secrets[format('AWS_SESSION_TOKEN_{0}', ENV)]
secrets[format('RDS_PASSWORD_AUTH_DB_{0}', ENV)]     # apenas terraform
secrets[format('RDS_PASSWORD_FLAGS_DB_{0}', ENV)]
secrets[format('RDS_PASSWORD_TARGETING_DB_{0}', ENV)]
secrets[format('ECR_REGISTRY')]                      # apenas microservice
secrets[format('EKS_CLUSTER_NAME_{0}', ENV)]        # apenas gitops
```

---

## Como Executar

### Pré-requisitos

- Conta AWS (região `us-east-1`)
- Docker
- kubectl + eksctl (para acesso ao cluster EKS)
- ArgoCD CLI (opcional)

### 1. Provisionar Infraestrutura (Terraform)

```bash
cd terraform
docker build -t terraform-local:1.0 .
docker run -it \
  -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
  -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
  -e AWS_SESSION_TOKEN="$AWS_SESSION_TOKEN" \
  -v ./:/workspace \
  terraform-local:1.0 /bin/bash

# Dentro do container:
terraform init -backend-config="bootstrap/remote/dev-backend.tfvars"
export TF_VAR_rds_password_auth_db="Senha123"
export TF_VAR_rds_password_flags_db="Senha456"
export TF_VAR_rds_password_targeting_db="Senha789"
terraform apply -var-file="environment/dev.tfvars"
```

### 2. Deploy dos Microserviços (CI/CD)

O deploy automático é feito via GitHub Actions. Ao fazer `push` para `develop`, `staging` ou `main`, os workflows criam imagens Docker, enviam para ECR e atualizam os manifests via ArgoCD.

### 3. Acesso ao Cluster EKS

```bash
aws eks update-kubeconfig --name eks-dev-01 --region us-east-1
kubectl get nodes
kubectl get pods -n application
```

### 4. Acesso ao ArgoCD

```bash
argocd login <argo-cd-endpoint> --username admin --password <password>
argocd app sync <app-name>
```

Consulte `eks/TODO.md` para mais detalhes sobre o setup do ArgoCD e do ingress-nginx.
