# todo analytics-service

## Build da imagem base

docker build -t analytics-service:1.0 .

## Pontos importantes

1- Para rodar localmente, foi necessário subir um serviço de SQS local usando a imagem do elasticmq e subir um dynamodb local.

2- Adicionado duas váriaveis novas para pegar o endpoint desses serviços.

AWS_DYNAMODB_ENDPOINT="http://dynamodb-local:8000"
AWS_SQS_ENDPOINT="http://localhost:9324"

3- Alterado no código app.py as variáveis

SQS_ENDPOINT = os.getenv("AWS_SQS_ENDPOINT") -> add essa linha
DYNAMODB_ENDPOINT = os.getenv("AWS_DYNAMODB_ENDPOINT") -> add essa linha

try:
    ...
    if SQS_ENDPOINT:
        sqs_kwargs["endpoint_url"] = SQS_ENDPOINT
    sqs_client = session.client("sqs", **sqs_kwargs)
    if DYNAMODB_ENDPOINT:
        dynamodb_kwargs["endpoint_url"] = DYNAMODB_ENDPOINT
    dynamodb_client = session.client("dynamodb", **dynamodb_kwargs)

4- No ../local/docker-compose.yaml, adicionado serviços para SQS local (elasticmq) e DynamoDB local.

## Problemas encontrados

Ao subir o serviço analytics-service, gerou o seguinte erro no log:

  File "/app/app.py", line 10, in <module>
    from flask import Flask, jsonify
  File "/opt/venv/lib/python3.11/site-packages/flask/__init__.py", line 5, in <module>
    from .app import Flask as Flask
  File "/opt/venv/lib/python3.11/site-packages/flask/app.py", line 30, in <module>
    from werkzeug.urls import url_quote
ImportError: cannot import name 'url_quote' from 'werkzeug.urls' (/opt/venv/lib/python3.11/site-packages/werkzeug/urls.py)
[2026-06-25 15:25:07 +0000] [7] [INFO] Worker exiting (pid: 7)
[2026-06-25 15:25:07 +0000] [1] [INFO] Shutting down: Master
[2026-06-25 15:25:07 +0000] [1] [INFO] Reason: Worker failed to boot.

5- Solução: Atualizar a versão do Flask ou downgratar o Werkzeug para uma versão compatível (Flask 2.3+ requer Werkzeug 2.3+).