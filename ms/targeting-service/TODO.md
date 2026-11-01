# todo targeting-service

## Build da imagem base

docker build -t targeting-service:1.0 .

## Criação de uma database local

Foi criado no docker-compose a estrutura do banco, disponível em ../local/docker-compose.yaml

A execução do init.sql esta configurado dentro do docker-compose

## Rodando sem docker-compose

cd ./targeting-service/db/Dockerfile
docker build -t targeting-service-postgres:17 .

psql -h localhost -p 5440 -U targeting_service -d targeting_db
psql -h localhost -p 5440 -U targeting_service -d targeting_db -f ./db/init.sql

## Problemas encontrados

Erro ao rodar:

  File "/app/app.py", line 8, in <module>
    from flask import Flask, request, jsonify
  File "/opt/venv/lib/python3.11/site-packages/flask/__init__.py", line 5, in <module>
    from .app import Flask as Flask
  File "/opt/venv/lib/python3.11/site-packages/flask/app.py", line 30, in <module>
    from werkzeug.urls import url_quote
ImportError: cannot import name 'url_quote' from 'werkzeug.urls' (/opt/venv/lib/python3.11/site-packages/werkzeug/urls.py)

Necessário adicionar Werkzeug==2.2.3 no requirements.txt, pois esta falhando para iniciar a aplicação.