# github-webhook (Python/Flask)

Este é o serviço de relay de webhooks do projeto ToggleMaster. Ele recebe webhooks do Grafana/Alertmanager (quando o alerta `High5xxErrorRate` dispara) e dispara um `repository_dispatch` no GitHub Actions, que por sua vez executa o workflow `self-heal.yml` para reiniciar o microserviço com erro.

## 📦 Pré-requisitos (Local)

* [Python](https://www.python.org/downloads/) 3.11+
* [GitHub Personal Access Token](https://github.com/settings/tokens) com escopo `repo`

## 🚀 Rodando Localmente

1. **Clone o repositório** e entre na pasta `github-webhook`.

2. **Configure as Variáveis de Ambiente:**
   Crie um arquivo chamado `.env` na raiz desta pasta (`github-webhook/`) com o seguinte conteúdo:
   ```.env
   # Porta que o serviço irá rodar
   PORT="8080"

   # GitHub Personal Access Token com escopo 'repo'
   GH_PAT="seu_github_pat_aqui"

   # Repositório onde o dispatch será enviado
   GH_REPO="rmvinicius/fiap-phase4"

   # Tipo de evento de dispatch
   EVENT_TYPE="fiap-5xx-alert"

   # Endpoint do OpenTelemetry (Alloy)
   OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4318"
   ```

3. **Instale as Dependências:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Inicie o Serviço:**
   ```bash
   python app.py
   # ou com gunicorn
   gunicorn --bind 0.0.0.0:8080 app:app
   ```
   O servidor estará rodando em `http://localhost:8080`.

## 🧪 Testando os Endpoints

**1. Verifique a Saúde (Health Check):**
```bash
curl http://localhost:8080/health
```
Saída esperada: `{"status":"ok"}`

**2. Simule um webhook do Grafana/Alertmanager:**
```bash
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "status": "firing",
    "commonLabels": {
      "alertname": "High5xxErrorRate",
      "service": "auth-service",
      "namespace": "application",
      "severity": "critical"
    },
    "commonAnnotations": {
      "summary": "High 5xx error rate on auth-service",
      "description": "5xx error rate is 8.00% (> 5%) over the last 5 minutes"
    }
  }'
```

## 🏗️ Deploy no Kubernetes

O serviço é implantado via Helm (chart compartilhado `helm/microservice`) e ArgoCD. Os valores estão em `deploy/values.yaml` e a Application em `gitops/argocd/applications/github-webhook.yaml`.

Prometheus scraping está habilitado nas anotações do serviço e do pod (endpoint `/metrics`).
