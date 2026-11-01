# STAGE BUILD
FROM golang:1.25-alpine AS builder

WORKDIR /app

COPY go.mod go.sum ./
COPY *.go ./
RUN go mod download && go mod tidy
RUN CGO_ENABLED=0 GOOS=linux go build -o /evaluation-service .

# STAGE RUN
FROM debian:12-slim

RUN apt-get update && apt-get install -y ca-certificates curl

WORKDIR /app

RUN useradd -u 10001 evaluation-service && chown -R evaluation-service:evaluation-service /app

COPY --from=builder /evaluation-service .

USER evaluation-service

EXPOSE 8004

CMD ["./evaluation-service"]