# todo evaluating-service

## Build da imagem base

docker build -t evaluating-service:1.0 .

## Criação de uma database local

Foi criado no docker-compose a estrutura do banco, disponível em ../local/docker-compose.yaml

A execução do init.sql esta configurado dentro do docker-compose

## Rodando sem docker-compose

cd ./auth-service/db/Dockerfile
docker build -t auth-service-postgres:17 .

psql -h localhost -p 5440 -U auth_service -d auth_db
psql -h localhost -p 5440 -U auth_service -d auth_db -f ./db/init.sql

## Problemas encontrados

Encontrado erro ao buildar a aplicação:

 > [builder 6/6] RUN CGO_ENABLED=0 GOOS=linux go build -o /evaluation-service .:
7.298 # evaluation-service
7.298 ./evaluator.go:4:2: "context" imported and not used
7.298 ./evaluator.go:106:12: undefined: os
7.298 ./evaluator.go:133:12: undefined: os

Necessário comentar:

evaluator.go

import (
	//"context"
  "os" // Adicionar

Para testes via minikube, precisei aumentar o timeout para a requisição pro flag, que estava levando 6s localmente:

	// Cliente HTTP (com timeout)
	httpClient := &http.Client{
		Timeout: 30 * time.Second,
	}

Precisei alterar a imagem Dockerfile para o usuário evaluation-service, pois ao chamar a api do flags via service, nao conseguia resolver o dns interno, para isso, usei uma imagem debian de base.

FROM debian:12-slim