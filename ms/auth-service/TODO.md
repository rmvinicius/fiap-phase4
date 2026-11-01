# todo auth-service

## Build da imagem base

docker build -t auth-service:1.0 .

## Criação de uma database local

Foi criado no docker-compose a estrutura do banco, disponível em ../local/docker-compose.yaml

A execução do init.sql esta configurado dentro do docker-compose

## Rodando sem docker-compose

cd ./auth-service/db/Dockerfile
docker build -t auth-service-postgres:17 .

psql -h localhost -p 5440 -U auth_service -d auth_db
psql -h localhost -p 5440 -U auth_service -d auth_db -f ./db/init.sql

## Problemas encontrados

Problema para realizar o a execução do go build
  - Necessário comentar no go.mod algumas linhas, handlers.go e main.go

main.go:

//"fmt"

handlers.go

	//"crypto/sha256"
	//"encoding/hex"



# Melhorias no template

unificar o template-go e template-python, criar condições para aplicar cada step conforme o tipo de serviço

