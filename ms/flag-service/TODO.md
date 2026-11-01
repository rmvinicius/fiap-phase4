# todo flag-service

## Build da imagem base

docker build -t flag-service:1.0 .

## Criação de uma database local

Foi criado no docker-compose a estrutura do banco, disponível em ../local/docker-compose.yaml

A execução do init.sql esta configurado dentro do docker-compose

## Rodando sem docker-compose

cd ./flag-service/db/Dockerfile
docker build -t flag-service-postgres:17 .

psql -h localhost -p 5440 -U flag_service -d flags_db
psql -h localhost -p 5440 -U flag_service -d flags_db -f ./db/init.sql

## Problemas encontrados

Necessário adicionar Werkzeug==2.2.3 no requirements.txt, pois esta falhando para iniciar a aplicação.