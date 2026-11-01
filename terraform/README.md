# FIAP Tech Challenge - Fase 3: Infraestrutura Terraform

Este projeto Terraform provisiona uma infraestrutura completa em nuvem na AWS para o Tech Challenge da FIAP (Fase 3). Ele constrói uma arquitetura multicamadas composta por uma VPC customizada, serviços gerenciados e um cluster EKS — tudo configurado para o ambiente de **desenvolvimento** na região **us-east-1**.

## Visão Geral da Arquitetura

A infraestrutura fornece:

- **Camada de rede**: Uma VPC dedicada com subnets públicas, privadas e para EKS distribuídas em duas Zonas de Disponibilidade, um Internet Gateway, um NAT Gateway e tabelas de rotas.
- **Camada de dados**: Instâncias RDS PostgreSQL (auth, flags, targeting), um cache Redis serverless (ElastiCache) e uma tabela DynamoDB para analytics.
- **Camada de mensageria**: Uma fila SQS com uma dead-letter queue para processamento de mensagens.
- **Camada de computação**: Um cluster Amazon EKS com node groups gerenciados.

## Estrutura do Projeto

```
terraform/
├── backend.tf                          # Configuração do backend Terraform (S3)
├── version.tf                          # Restrições de versão do Terraform e do provider
├── provider.tf                         # Configuração do provider AWS
├── main.tf                             # Módulo raiz: instancia todos os módulos filhos
├── variables.tf                        # Variáveis de entrada do root (consumidas pelo main.tf e pelos módulos)
├── outputs.tf                          # Outputs do root (re-exportados dos módulos)
├── Dockerfile                          # Imagem Docker com Terraform 1.16.0
├── bootstrap/
│   └── remote/
│       └── dev-backend.tfvars          # Configuração de state remoto S3 para dev
├── environment/
│   └── dev.tfvars                      # Valores das variáveis para o ambiente de desenvolvimento
├── modules/
│   ├── network/                        # VPC, subnets, roteamento e security groups
│   ├── sqs/                            # Fila SQS com dead-letter queue
│   ├── rds/                            # Instâncias RDS PostgreSQL e subnet group
│   ├── eks/                            # Cluster EKS, roles IAM e node groups
│   ├── dynamodb/                       # Tabela DynamoDB para analytics
│   └── redis/                          # Cache Redis serverless (ElastiCache)
├── README.md                           # Este arquivo
└── TODO.md                             # Instruções de bootstrap do bucket S3 de state
```

### Arquivos Raiz

| Arquivo | Descrição |
|---|---|
| `backend.tf` | Configura o backend do Terraform como um bucket S3. O bucket/key/region são injetados no `terraform init` via `bootstrap/remote/dev-backend.tfvars`. |
| `version.tf` | Fixa a versão do provider AWS em `~> 6.60.0` e declara os requisitos de versão do Terraform. |
| `provider.tf` | Configura o provider AWS usando a variável `aws_region`. |
| `main.tf` | Módulo raiz que conecta os seis módulos filhos. O módulo network é criado primeiro; seus IDs de subnet e security group são passados para os módulos RDS, EKS e Redis como dependências. |
| `variables.tf` | Declara todas as variáveis de entrada usadas no módulo raiz e passadas para os módulos filhos. |
| `outputs.tf` | Re-exporta valores selecionados de cada módulo filho (VPC ID, subnet IDs, cluster endpoint, endpoints de banco, etc.) para uso por outros workspaces Terraform ou consumidores externos. |

---

## Módulos

### 1. Módulo Network (`modules/network/`)

**Propósito**: Cria a camada fundamental de rede — uma VPC com subnets públicas e privadas, um Internet Gateway, um NAT Gateway, tabelas de rotas e dois security groups.

#### `main.tf` — Recursos Criados

| Recurso | Descrição |
|---|---|
| `aws_vpc.vpc` | A VPC principal com bloco CIDR configurável e tenancy de instâncias. Marcada com o nome do ambiente. |
| `aws_subnet.subnets` | Todas as subnets definidas como um map (AKS, RDS, PVE/private e uma subnet pública). Cada subnet é marcada com seu nome-chave. |
| `aws_internet_gateway.igw` | Internet Gateway anexado à VPC, permitindo acesso à internet para as subnets públicas. |
| `aws_eip.nat_eip` | Um Elastic IP alocado para o NAT Gateway (criado somente quando `eip_enable_nat_gateway` é `true`). |
| `aws_nat_gateway.nat_gw` | NAT Gateway posicionado na subnet pública, fornecendo acesso de saída à internet para as subnets privadas (condicional a `eip_enable_nat_gateway`). |
| `aws_route_table.public` | Tabela de rotas com rota padrão (`0.0.0.0/0`) para o Internet Gateway. |
| `aws_route_table_association.public` | Associa a subnet pública à tabela de rotas pública. |
| `aws_route_table.private` | Tabela de rotas com uma rota padrão opcional para o NAT Gateway (rota dinâmica adicionada somente quando o NAT está habilitado). |
| `aws_route_table_association.private` | Associa todas as subnets não-públicas à tabela de rotas privada (usando um filtro `for_each`). |
| `aws_security_group.sg_private` | Security group para recursos privados (RDS, Redis) permitindo SSH a partir do CIDR da VPC e todo tráfego de saída. |
| `aws_security_group.sg_public` | Security group para recursos públicos permitindo HTTP a partir de um IP específico e todo tráfego de saída. |

#### `variables.tf` — Variáveis de Entrada

| Variável | Tipo | Descrição |
|---|---|---|
| `environment` | `string` | Nome do ambiente (ex: "Desenvolvimento"), adicionado como tag. |
| `vpc_name` | `string` | Tag de nome para a VPC. |
| `vpc_ipv4_block` | `string` | Bloco CIDR da VPC (ex: `10.0.0.0/16`). |
| `vpc_instance_tenancy` | `string` | Tenancy das instâncias na VPC (`default` ou `dedicated`). |
| `subnets` | `map(object)` | Map das definições de subnets, cada uma com campos `cidr` e `az`. Chaves como `snet-dev-aks-1a` são usadas para tagging e lookup. |
| `igw_name` | `string` | Tag de nome para o Internet Gateway. |
| `eip_name` | `string` | Tag de nome para o Elastic IP. |
| `nat_gateway_name` | `string` | Tag de nome para o NAT Gateway. |
| `route_table_public_name` | `string` | Tag de nome para a tabela de rotas pública. |
| `route_table_private_name` | `string` | Tag de nome para a tabela de rotas privada. |
| `eip_enable_nat_gateway` | `bool` | Se deve criar o NAT Gateway e o EIP (padrão: `true`). |
| `security_group_priv_name` | `string` | Nome do security group privado. |
| `security_group_priv_description` | `string` | Descrição do security group privado. |
| `security_group_pub_name` | `string` | Nome do security group público. |
| `security_group_pub_description` | `string` | Descrição do security group público. |

#### `outputs.tf` — Outputs

| Output | Descrição |
|---|---|
| `vpc_id` | ID da VPC. |
| `subnet_ids` | IDs de todas as subnets. |
| `igw_id` | ID do Internet Gateway. |
| `nat_gateway_id` | ID do NAT Gateway (ou `null` se desabilitado). |
| `public_route_table_id` | ID da tabela de rotas pública. |
| `private_route_table_id` | ID da tabela de rotas privada. |
| `public_subnet_ids` | Lista contendo o ID da subnet pública. |
| `private_subnet_ids` | Lista de IDs das subnets privadas (todas exceto a pública). |
| `sg_private_id` | ID do security group privado (usado pelos módulos RDS e Redis). |
| `sg_public_id` | ID do security group público. |
| `eks_subnet_ids` | IDs das subnets para o cluster EKS (subnets AKS). |
| `rds_subnet_ids` | IDs das subnets para RDS (subnets RDS). |
| `redis_subnet_ids` | IDs das subnets para Redis (subnets PVE/private). |

---

### 2. Módulo SQS (`modules/sqs/`)

**Propósito**: Cria uma fila padrão SQS com uma redrive policy apontando para uma dead-letter queue (DLQ), garantindo que mensagens que falharem no processamento múltiplas vezes sejam movidas para a DLQ para inspeção.

#### `main.tf` — Recursos Criados

| Recurso | Descrição |
|---|---|
| `aws_sqs_queue.queue` | A fila SQS principal. Configurada com delay, tamanho máximo de mensagem, retenção, tempo de espera de recebimento, visibility timeout e uma redrive policy que envia mensagens com falha para a DLQ após `sqs_max_receive_count` tentativas. |
| `aws_sqs_queue.terraform_queue_deadletter` | A dead-letter queue. Recebe mensagens que excedem o número máximo de recebimentos na fila principal. Compartilha as configurações de retenção e timeout com a fila principal. |

#### `variables.tf` — Variáveis de Entrada

| Variável | Tipo | Descrição |
|---|---|---|
| `environment` | `string` | Nome do ambiente, adicionado como tag. |
| `sqs_name` | `string` | Nome da fila SQS principal. A DLQ é nomeada `<sqs_name>-deadletter`. |
| `sqs_delay_seconds` | `number` | Delay antes de uma mensagem ficar disponível para consumo (0–86400). |
| `sqs_max_message_size` | `number` | Tamanho máximo da mensagem em bytes (1024–262144). |
| `sqs_message_retention_seconds` | `number` | Por quanto tempo as mensagens são retidas na fila (60–1209600). |
| `sqs_receive_wait_time_seconds` | `number` | Duração do long polling (0–20). |
| `sqs_visibility_timeout_seconds` | `number` | Visibility timeout — por quanto tempo uma mensagem fica oculta após ser consumida (0–43200). |
| `sqs_max_receive_count` | `number` | Número de vezes que uma mensagem pode ser recebida antes de ser movida para a DLQ. |

#### `outputs.tf` — Outputs

| Output | Descrição |
|---|---|
| `sqs_id` | URL da fila principal. |

---

### 3. Módulo RDS (`modules/rds/`)

**Propósito**: Cria uma ou mais instâncias RDS PostgreSQL a partir de uma lista de definições, junto com um DB subnet group. Cada instância é criada a partir de um map chaveado pelo campo `name`, permitindo que múltiplos bancos de dados sejam implantados em um único módulo.

#### `main.tf` — Recursos Criados

| Recurso | Descrição |
|---|---|
| `aws_db_instance.rds` | Instâncias RDS PostgreSQL. Criadas usando `for_each` sobre `rds_database_instances`, de modo que uma instância é provisionada por entrada da lista. Cada instância usa o storage, engine, versão, instance class, credenciais, parameter group e subnet group especificados. |
| `aws_db_subnet_group.rds-subnet` | DB subnet group contendo os IDs das subnets RDS, permitindo que as instâncias RDS sejam distribuídas em múltiplas AZs. |

#### `variables.tf` — Variáveis de Entrada

| Variável | Tipo | Descrição |
|---|---|---|
| `environment` | `string` | Nome do ambiente, adicionado como tag. |
| `rds_database_instances` | `list(object)` | Lista de definições de instâncias RDS. Cada objeto tem `name`, `db_name`, `username` e `password` (deixado em branco no `.tfvars`; preenchido dinamicamente via `locals` no módulo raiz). |
| `rds_allocated_storage` | `number` | Storage alocado inicial em GB. |
| `rds_instance_class` | `string` | Classe da instância (ex: `db.t3.micro`). |
| `rds_engine` | `string` | Engine do banco (ex: `postgres`). |
| `rds_engine_version` | `string` | Versão da engine (ex: `17`). |
| `rds_parameter_group_name` | `string` | Nome do parameter group (ex: `default.postgres17`). |
| `rds_skip_final_snapshot` | `bool` | Se deve pular o snapshot final no destroy. |
| `rds_subnet_name` | `string` | Nome do DB subnet group. |
| `rds_subnet_ids` | `list(string)` | IDs das subnets para o DB subnet group (passados do módulo network). |

#### `outputs.tf` — Outputs

| Output | Descrição |
|---|---|
| `database_endpoints` | Map do nome da instância para o endereço do endpoint. |
| `database_arns` | Map do nome da instância para o ARN. |

---

### 4. Módulo EKS (`modules/eks/`)

**Propósito**: Cria um cluster Amazon EKS com uma role IAM gerenciada e um ou mais node groups gerenciados com auto-scaling. As roles IAM e anexos de policy tanto para o cluster quanto para os worker nodes são provisionados inline.

#### `main.tf` — Recursos Criados

| Recurso | Descrição |
|---|---|
| `aws_eks_cluster.main` | O cluster EKS. Configurado com uma role IAM, modo de autenticação API, VPC config com IDs das subnets e versionamento. Marcado com o nome do cluster e do ambiente. |
| `aws_iam_role.cluster` | Role IAM para o serviço do cluster EKS. Usa uma trust policy permitindo que `eks.amazonaws.com` a assuma. |
| `aws_iam_role_policy_attachment.cluster_AmazonEKSClusterPolicy` | Anexa a managed policy `AmazonEKSClusterPolicy` à role do cluster. |
| `aws_eks_node_group.nodes` | Node groups gerenciados. Criados usando `for_each` sobre `eks_node_groups`. Cada node group é configurado com scaling (desired, min, max), update config (max unavailable), instance types e tags. Os IDs das subnets vêm do módulo network. |
| `aws_iam_role.node` | Role IAM para os worker nodes EKS. Usa uma trust policy permitindo que `ec2.amazonaws.com` a assuma. |
| `aws_iam_role_policy_attachment.node_AmazonEKSWorkerNodePolicy` | Anexa a managed policy `AmazonEKSWorkerNodePolicy` à role do node. |
| `aws_iam_role_policy_attachment.node_AmazonEC2ContainerRegistryReadOnly` | Permite que os nodes leiam do ECR. |
| `aws_iam_role_policy_attachment.node_AmazonEKS_CNI_Policy` | Anexa a `AmazonEKS_CNI_Policy` para networking dos pods. |

#### `variables.tf` — Variáveis de Entrada

| Variável | Tipo | Descrição |
|---|---|---|
| `environment` | `string` | Nome do ambiente, adicionado como tag. |
| `eks_cluster_name` | `string` | Nome do cluster EKS. |
| `eks_cluster_version` | `string` | Versão do Kubernetes (ex: `1.36`). |
| `eks_subnet_ids` | `list(string)` | IDs das subnets para o VPC config do cluster EKS (passados do módulo network). |
| `eks_node_groups` | `list(object)` | Lista de definições dos node groups. Cada objeto tem `name`, `instance_type`, `desired_size`, `min_size` e `max_size`. |

#### `outputs.tf` — Outputs

| Output | Descrição |
|---|---|
| `cluster_endpoint` | URL do endpoint da API do cluster EKS. |
| `cluster_certificate_authority` | Dados da autoridade certificadora (certificate authority) do cluster, codificados em base64. |
| `cluster_name` | Nome do cluster EKS. |
| `cluster_arn` | ARN do cluster EKS. |

---

### 5. Módulo DynamoDB (`modules/dynamodb/`)

**Propósito**: Cria uma tabela DynamoDB com uma partition key configurável, uma sort key opcional e um conjunto dinâmico de definições de atributos. Suporta tanto billing mode on-demand quanto provisionado.

#### `main.tf` — Recursos Criados

| Recurso | Descrição |
|---|---|
| `aws_dynamodb_table.dynamodb` | Uma única tabela DynamoDB. Usa um bloco dinâmico para definir os atributos a partir da lista `dynamodb_attributes`. Suporta `hash_key` (partition key) e `range_key` opcional (sort key). Marcada com o nome da tabela e do ambiente. |

#### `variables.tf` — Variáveis de Entrada

| Variável | Tipo | Descrição |
|---|---|---|
| `environment` | `string` | Nome do ambiente, adicionado como tag. |
| `dynamodb_table_name` | `string` | Nome da tabela DynamoDB. |
| `dynamodb_billing_mode` | `string` | Billing mode: `PROVISIONED` ou `PAY_PER_REQUEST`. |
| `dynamodb_read_capacity` | `number` | Unidades de read capacity (usado quando o billing mode é `PROVISIONED`). |
| `dynamodb_write_capacity` | `number` | Unidades de write capacity (usado quando o billing mode é `PROVISIONED`). |
| `dynamodb_hash_key` | `string` | Nome do atributo da partition key. |
| `dynamodb_range_key` | `string` | Nome do atributo da sort key (definido como `null` se não usado). |
| `dynamodb_attributes` | `list(object)` | Lista de definições de atributos, cada uma com `name` e `type` (ex: `S` para string). A primeira entrada deve corresponder à hash key; uma segunda entrada pode definir a range key. |

#### `outputs.tf` — Outputs

Não existe arquivo de output para este módulo. O ARN e ID da tabela podem ser acessados via o recurso `aws_dynamodb_table.dynamodb` caso necessário em atualizações futuras.

---

### 6. Módulo Redis (`modules/redis/`)

**Propósito**: Cria um cache Amazon ElastiCache Serverless usando Redis (ou Valkey) como engine. Isso fornece um cache in-memory serverless gerenciado para armazenamento de sessões ou camadas de cache.

#### `main.tf` — Recursos Criados

| Recurso | Descrição |
|---|---|
| `aws_elasticache_serverless_cache.redis` | Um cache Elasticache serverless. Configurado com o nome do cache, descrição, tipo de engine, versão principal da engine, IDs dos security groups (do SG privado do módulo network) e IDs das subnets (das subnets Redis do módulo network). Marcado com o nome do cache e do ambiente. |

#### `variables.tf` — Variáveis de Entrada

| Variável | Tipo | Descrição |
|---|---|---|
| `environment` | `string` | Nome do ambiente, adicionado como tag. |
| `redis_cache_name` | `string` | Nome do cache Redis. |
| `redis_description` | `string` | Descrição do cache. |
| `redis_security_group_ids` | `list(string)` | IDs dos security groups para o cache (passados do módulo network). |
| `redis_subnet_ids` | `list(string)` | IDs das subnets para o cache (passados do módulo network). |
| `redis_engine` | `string` | Engine do cache: `redis` ou `valkey`. |
| `redis_version` | `string` | Versão principal da engine (ex: `7.2`). |

#### `outputs.tf` — Outputs

| Output | Descrição |
|---|---|
| `redis_endpoint` | Endereço do endpoint do cache Redis. |

---

## Referência de Variáveis

Todas as variáveis são declaradas no `variables.tf` raiz. O arquivo `environment/dev.tfvars` fornece valores concretos para o ambiente de desenvolvimento.

### Variáveis Raiz de Ambiente

| Variável | Tipo | Arquivo de Origem | Descrição |
|---|---|---|---|
| `environment` | `string` | `dev.tfvars` | Label do ambiente (ex: "Desenvolvimento"). |
| `aws_region` | `string` | `dev.tfvars` | Região AWS (`us-east-1`). |

### Variáveis de Network

| Variável | Tipo | Arquivo de Origem | Descrição |
|---|---|---|---|
| `vpc_name` | `string` | `dev.tfvars` | Tag de nome da VPC. |
| `vpc_ipv4_block` | `string` | `dev.tfvars` | Bloco CIDR da VPC (`10.0.0.0/16`). |
| `vpc_instance_tenancy` | `string` | `dev.tfvars` | Tenancy das instâncias (`default`). |
| `subnets` | `map(object)` | `dev.tfvars` | Map de todas as subnets com CIDR e AZ. Inclui subnets AKS, RDS, PVE (privada) e pública. |
| `eip_enable_nat_gateway` | `bool` | `dev.tfvars` | Habilita o NAT Gateway (`true`). |
| `igw_name` | `string` | `dev.tfvars` | Nome do Internet Gateway. |
| `eip_name` | `string` | `dev.tfvars` | Nome do Elastic IP. |
| `nat_gateway_name` | `string` | `dev.tfvars` | Nome do NAT Gateway. |
| `route_table_public_name` | `string` | `dev.tfvars` | Nome da tabela de rotas pública. |
| `route_table_private_name` | `string` | `dev.tfvars` | Nome da tabela de rotas privada. |
| `security_group_priv_name` | `string` | `dev.tfvars` | Nome do security group privado. |
| `security_group_priv_description` | `string` | `dev.tfvars` | Descrição do security group privado. |
| `security_group_pub_name` | `string` | `dev.tfvars` | Nome do security group público. |
| `security_group_pub_description` | `string` | `dev.tfvars` | Descrição do security group público. |

### Variáveis de SQS

| Variável | Tipo | Arquivo de Origem | Descrição |
|---|---|---|---|
| `sqs_name` | `string` | `dev.tfvars` | Nome da fila. |
| `sqs_delay_seconds` | `number` | `dev.tfvars` | Delay antes do consumo (90). |
| `sqs_max_message_size` | `number` | `dev.tfvars` | Tamanho máximo da mensagem em bytes (2048). |
| `sqs_message_retention_seconds` | `number` | `dev.tfvars` | Período de retenção da mensagem (86400). |
| `sqs_receive_wait_time_seconds` | `number` | `dev.tfvars` | Tempo de espera do long polling (10). |
| `sqs_visibility_timeout_seconds` | `number` | `dev.tfvars` | Visibility timeout (30). |
| `sqs_max_receive_count` | `number` | `dev.tfvars` | Máximo de recebimentos antes da DLQ (4). |

### Variáveis de RDS

| Variável | Tipo | Arquivo de Origem | Descrição |
|---|---|---|---|
| `rds_database_instances` | `list(object)` | `dev.tfvars` | Lista de 3 instâncias RDS (auth_db, flags_db, targeting_db). Password deixado em branco — preenchido via `locals` no módulo raiz. |
| `rds_allocated_storage` | `number` | `dev.tfvars` | Storage em GB (20). |
| `rds_instance_class` | `string` | `dev.tfvars` | Classe da instância (`db.t3.micro`). |
| `rds_engine` | `string` | `dev.tfvars` | Engine (`postgres`). |
| `rds_engine_version` | `string` | `dev.tfvars` | Versão da engine (`17`). |
| `rds_parameter_group_name` | `string` | `dev.tfvars` | Parameter group (`default.postgres17`). |
| `rds_skip_final_snapshot` | `bool` | `dev.tfvars` | Pula o snapshot final no destroy (`true`). |
| `rds_subnet_name` | `string` | `dev.tfvars` | Nome do DB subnet group. |
| `rds_password_auth_db` | `string` | **env/`TF_VAR`** | **Sensitive.** Password para `auth_db`. |
| `rds_password_flags_db` | `string` | **env/`TF_VAR`** | **Sensitive.** Password para `flags_db`. |
| `rds_password_targeting_db` | `string` | **env/`TF_VAR`** | **Sensitive.** Password para `targeting_db`. |

### Variáveis de EKS

| Variável | Tipo | Arquivo de Origem | Descrição |
|---|---|---|---|
| `eks_cluster_name` | `string` | `dev.tfvars` | Nome do cluster EKS (`eks-dev-01`). |
| `eks_cluster_version` | `string` | `dev.tfvars` | Versão do Kubernetes (`1.36`). |
| `eks_node_groups` | `list(object)` | `dev.tfvars` | Um node group (`dev01`) com instâncias `t3.medium`. |

### Variáveis de DynamoDB

| Variável | Tipo | Arquivo de Origem | Descrição |
|---|---|---|---|
| `dynamodb_table_name` | `string` | `dev.tfvars` | Nome da tabela (`ToggleMasterAnalytics`). |
| `dynamodb_billing_mode` | `string` | `dev.tfvars` | Billing mode (`PROVISIONED`). |
| `dynamodb_read_capacity` | `number` | `dev.tfvars` | Unidades de read capacity (1). |
| `dynamodb_write_capacity` | `number` | `dev.tfvars` | Unidades de write capacity (1). |
| `dynamodb_hash_key` | `string` | `dev.tfvars` | Partition key (`event_id`). |
| `dynamodb_range_key` | `string` | `dev.tfvars` | Sort key (`null` — sem sort key). |
| `dynamodb_attributes` | `list(object)` | `dev.tfvars` | Definições de atributos (uma: `event_id` do tipo `S`). |

### Variáveis de Redis

| Variável | Tipo | Arquivo de Origem | Descrição |
|---|---|---|---|
| `redis_cache_name` | `string` | `dev.tfvars` | Nome do cache (`redis-dev-01`). |
| `redis_description` | `string` | `dev.tfvars` | Descrição do cache. |
| `redis_engine` | `string` | `dev.tfvars` | Engine (`redis`). |
| `redis_version` | `string` | `dev.tfvars` | Versão da engine (`7.2`). |

---

## Como Executar no Lab AWS

Este projeto é projetado para ser executado dentro de um container Docker com o Terraform 1.16.0 pré-instalado. O arquivo `TODO.md` contém os passos de bootstrap para configurar o bucket S3 de state e a tabela DynamoDB de lock antes de rodar o Terraform.

### Pré-requisitos

1. **Credenciais do AWS Lab** — Obtenha `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` e `AWS_SESSION_TOKEN` do ambiente AWS Lab.
2. **Docker** — Instalado em sua máquina.
3. **Bucket S3 de state e tabela DynamoDB de lock** — Criados uma única vez através dos passos em `TODO.md`.

### Passo 1: Fazer o Bootstrap do Backend S3 (Setup Inicial)

Execute os comandos do `TODO.md` localmente (fora do Docker) para criar o bucket S3 e a tabela DynamoDB de lock:

```bash
export BUCKET_NAME="tfstate-tech-challenge-lab-aws"

aws s3api create-bucket --bucket $BUCKET_NAME --region us-east-1
aws s3api put-bucket-versioning --bucket $BUCKET_NAME \
  --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption --bucket $BUCKET_NAME \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

aws dynamodb create-table \
  --table-name terraform-dev-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

### Passo 2: Construir a Imagem Docker do Terraform

A partir do diretório raiz do projeto (`terraform/`):

```bash
docker build -t terraform-local:1.0 .
```

### Passo 3: Rodar o Container com as Credenciais AWS

```bash
docker run -it \
  -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
  -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
  -e AWS_SESSION_TOKEN="$AWS_SESSION_TOKEN" \
  -v ./:/workspace \
  terraform-local:1.0 /bin/bash
```

### Passo 4: Inicializar o Terraform (dentro do container)

Inicialize o backend usando a configuração do state remoto:

```bash
terraform init -backend-config="bootstrap/remote/dev-backend.tfvars"
```

> Se for trocar de ambiente, use `--reconfigure` para reinicializar:
> ```bash
> terraform init -backend-config="bootstrap/remote/dev-backend.tfvars" --reconfigure
> ```

### Passo 5: Validar a Configuração

```bash
terraform validate
```

### Passo 6: Revisar o Plano de Execução

As senhas do RDS (uma por banco) são definidas via variáveis de ambiente `TF_VAR_` (não armazenadas no `.tfvars`):

```bash
export TF_VAR_rds_password_auth_db="Senha123"
export TF_VAR_rds_password_flags_db="Senha456"
export TF_VAR_rds_password_targeting_db="Senha789"
terraform plan -var-file="environment/dev.tfvars"
```

### Passo 7: Aplicar a Infraestrutura

```bash
export TF_VAR_rds_password_auth_db="Senha123"
export TF_VAR_rds_password_flags_db="Senha456"
export TF_VAR_rds_password_targeting_db="Senha789"
terraform apply -var-file="environment/dev.tfvars"
```

Confirme com `yes` quando solicitado.

### Passo 8: Destruir a Infraestrutura (quando não for mais necessária)

```bash
export TF_VAR_rds_password_auth_db="Senha123"
export TF_VAR_rds_password_flags_db="Senha456"
export TF_VAR_rds_password_targeting_db="Senha789"
terraform plan -destroy -var-file="environment/dev.tfvars"
terraform destroy -var-file="environment/dev.tfvars"
```

### Fluxo de Dependência entre Módulos

Os módulos possuem dependências explícitas definidas no `main.tf`:

```
network ──┬──> rds        (rds_subnet_ids)
          ├──> eks        (eks_subnet_ids)
          ├──> redis      (redis_subnet_ids, sg_private_id)
          └──> re-exportação de outputs (subnet_ids, vpc_id, sg_*_id, etc.)
```

SQS e DynamoDB são módulos independentes que não dependem do módulo network.

### Configuração do Backend

O state do Terraform é armazenado no S3 com a seguinte configuração (`bootstrap/remote/dev-backend.tfvars`):

| Configuração | Valor |
|---|---|
| `bucket` | `tfstate-tech-challenge-lab-aws` |
| `key` | `terraform/dev/tech-challenge-3.tfstate` |
| `region` | `us-east-1` |
| `encrypt` | `true` (criptografia AES256 server-side) |
| `use_lockfile` | `true` (state locking via S3, sem necessidade de DynamoDB) |

---

## GitHub Actions — Secrets Necessários

Os workflows em `.github/workflows/terraform-ci.yml` e `.github/workflows/terraform-destroy.yml` consumem os seguintes secrets do GitHub:

| Secret | Descrição |
|---|---|
| `AWS_ACCESS_KEY_ID_DEV` | AWS access key ID para o ambiente DEV. |
| `AWS_SECRET_ACCESS_KEY_DEV` | AWS secret access key para o ambiente DEV. |
| `AWS_SESSION_TOKEN_DEV` | AWS session token (se usando credenciais temporárias, ex: AWS Lab). |
| `RDS_PASSWORD_AUTH_DB_DEV` | Master password para o banco `auth_db`. Definido como `TF_VAR_rds_password_auth_db` durante `plan` e `apply`. |
| `RDS_PASSWORD_FLAGS_DB_DEV` | Master password para o banco `flags_db`. Definido como `TF_VAR_rds_password_flags_db` durante `plan` e `apply`. |
| `RDS_PASSWORD_TARGETING_DB_DEV` | Master password para o banco `targeting_db`. Definido como `TF_VAR_rds_password_targeting_db` durante `plan` e `apply`. |

Use apenas caracteres ASCII impríveis (exceto `/`, `@`, `"`, ` `).

Para ambientes STG e PRD, crie os equivalents (`AWS_ACCESS_KEY_ID_STG`, `RDS_PASSWORD_AUTH_DB_STG`, etc.).