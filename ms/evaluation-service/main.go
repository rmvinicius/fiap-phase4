package main

import (
	"context"
	"net/http"
	"os"
	"strconv"
	"time"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/sqs"
	"github.com/go-redis/redis/v8"
	"github.com/joho/godotenv"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.21.0"
	"go.opentelemetry.io/otel/trace"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
)

var (
	httpRequestsTotal = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "http_requests_total",
			Help: "Total number of HTTP requests.",
		},
		[]string{"method", "path", "status"},
	)
	httpRequestDuration = prometheus.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "http_request_duration_seconds",
			Help:    "HTTP request duration in seconds.",
			Buckets: prometheus.DefBuckets,
		},
		[]string{"method", "path", "status"},
	)
	logger *zap.Logger
)

func init() {
	prometheus.MustRegister(httpRequestsTotal, httpRequestDuration)

	cfg := zap.NewProductionConfig()
	cfg.Encoding = "json"
	cfg.EncoderConfig.TimeKey = "timestamp"
	cfg.EncoderConfig.EncodeTime = zapcore.ISO8601TimeEncoder
	cfg.EncoderConfig.LevelKey = "level"
	cfg.EncoderConfig.MessageKey = "message"
	cfg.EncoderConfig.CallerKey = "caller"
	cfg.EncoderConfig.StacktraceKey = "stacktrace"

	var err error
	logger, err = cfg.Build()
	if err != nil {
		panic(err)
	}
}

// traceFields extracts trace_id and span_id from OpenTelemetry context for logging
func traceFields(ctx context.Context) []zap.Field {
	span := trace.SpanFromContext(ctx)
	if !span.SpanContext().IsValid() {
		return nil
	}
	sc := span.SpanContext()
	return []zap.Field{
		zap.String("trace_id", sc.TraceID().String()),
		zap.String("span_id", sc.SpanID().String()),
	}
}

type statusRecorder struct {
	http.ResponseWriter
	status int
}

func (r *statusRecorder) WriteHeader(code int) {
	r.status = code
	r.ResponseWriter.WriteHeader(code)
}

func instrument(path string, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}
		next.ServeHTTP(rec, r)
		status := strconv.Itoa(rec.status)
		httpRequestsTotal.WithLabelValues(r.Method, path, status).Inc()
		httpRequestDuration.WithLabelValues(r.Method, path, status).Observe(time.Since(start).Seconds())
	})
}

// Contexto global para o Redis
var ctx = context.Background()

// App struct para injeção de dependência
type App struct {
	RedisClient         *redis.Client
	SqsSvc              *sqs.SQS
	SqsQueueURL         string
	HttpClient          *http.Client
	FlagServiceURL      string
	TargetingServiceURL string
}

func main() {
	_ = godotenv.Load() // Carrega .env para dev local

	// --- Configuração ---
	port := os.Getenv("PORT")
	if port == "" {
		port = "8004"
	}

	redisURL := os.Getenv("REDIS_URL")
	if redisURL == "" {
		logger.Fatal("REDIS_URL deve ser definida (ex: redis://localhost:6379)")
	}

	flagSvcURL := os.Getenv("FLAG_SERVICE_URL")
	if flagSvcURL == "" {
		logger.Fatal("FLAG_SERVICE_URL deve ser definida")
	}

	targetingSvcURL := os.Getenv("TARGETING_SERVICE_URL")
	if targetingSvcURL == "" {
		logger.Fatal("TARGETING_SERVICE_URL deve ser definida")
	}

	// SQS é opcional no dev local, mas obrigatório em prod
	sqsQueueURL := os.Getenv("AWS_SQS_URL")
	awsRegion := os.Getenv("AWS_REGION")
	sqsEndpoint := os.Getenv("AWS_SQS_ENDPOINT")
	if sqsQueueURL == "" {
		logger.Warn("Atenção: AWS_SQS_URL não definida. Eventos não serão enviados.")
	}
	if awsRegion == "" && sqsQueueURL != "" {
		logger.Fatal("AWS_REGION deve ser definida para usar SQS")
	}

	// --- Inicializa Clientes ---

	// Cliente Redis
	opt, err := redis.ParseURL(redisURL)
	if err != nil {
		logger.Fatal("Não foi possível parsear a URL do Redis", zap.Error(err))
	}
	rdb := redis.NewClient(opt)
	if _, err := rdb.Ping(ctx).Result(); err != nil {
		logger.Fatal("Não foi possível conectar ao Redis", zap.Error(err))
	}
	logger.Info("Conectado ao Redis com sucesso!")

	// Cliente SQS (AWS SDK)
	var sqsSvc *sqs.SQS
	if sqsQueueURL != "" {
		awsConfig := &aws.Config{
			Region:   aws.String(awsRegion),
			Endpoint: aws.String(sqsEndpoint),
		}
		sess, err := session.NewSession(awsConfig)
		if err != nil {
			logger.Fatal("Não foi possível criar sessão AWS", zap.Error(err))
		}
		sqsSvc = sqs.New(sess)
		logger.Info("Cliente SQS inicializado com sucesso.")
	}

	// Cliente HTTP (com timeout)
	httpClient := &http.Client{
		Timeout: 30 * time.Second,
	}

	// Cria a instância da App
	// --- OpenTelemetry ---
	if endpoint := os.Getenv("OTEL_EXPORTER_OTLP_ENDPOINT"); endpoint != "" {
		ctx := context.Background()
		exp, err := otlptracehttp.New(ctx, otlptracehttp.WithEndpointURL(endpoint+"/v1/traces"))
		if err == nil {
			res, _ := resource.New(ctx, resource.WithAttributes(semconv.ServiceName("evaluation-service")))
			tp := sdktrace.NewTracerProvider(sdktrace.WithBatcher(exp), sdktrace.WithResource(res))
			otel.SetTracerProvider(tp)
			otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(propagation.TraceContext{}, propagation.Baggage{}))
			defer func() { _ = tp.Shutdown(ctx) }()
		}
	}

	app := &App{
		RedisClient:         rdb,
		SqsSvc:              sqsSvc,
		SqsQueueURL:         sqsQueueURL,
		HttpClient:          httpClient,
		FlagServiceURL:      flagSvcURL,
		TargetingServiceURL: targetingSvcURL,
	}

	// --- Rotas ---
	mux := http.NewServeMux()
	mux.Handle("/metrics", promhttp.Handler())
	mux.Handle("/health", instrument("/health", http.HandlerFunc(app.healthHandler)))
	mux.Handle("/evaluate", instrument("/evaluate", http.HandlerFunc(app.evaluationHandler)))

	logger.Info("Serviço de Avaliação (Go) rodando na porta", zap.String("port", port))
	if err := http.ListenAndServe(":"+port, otelhttp.NewHandler(mux, "evaluation-service")); err != nil {
		logger.Fatal("Erro ao iniciar servidor", zap.Error(err))
	}
}