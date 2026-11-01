# STAGE BUILD
FROM golang:1.25-alpine AS builder

WORKDIR /app

COPY go.mod go.sum ./
COPY *.go ./
RUN go mod download && go mod tidy
RUN CGO_ENABLED=0 GOOS=linux go build -o /auth-service .

# STAGE RUN
FROM alpine:3.20

RUN apk --no-cache add ca-certificates curl

RUN adduser -D -u 10001 auth-service

WORKDIR /app

COPY --from=builder /auth-service .

USER auth-service

EXPOSE 8001

CMD ["./auth-service"]