package main

import (
	"context"
	"database/sql"
	"net/http"
	"os"
	"strconv"
	"time"

	_ "github.com/jackc/pgx/v4/stdlib"
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

// App struct (para injeção de dependência)
type App struct {
	DB        *sql.DB
	MasterKey string
}

func main() {
	// Carrega o .env para desenvolvimento local. Em produção, isso não fará nada.
	_ = godotenv.Load()

	// --- Configuração ---
	port := os.Getenv("PORT")
	if port == "" {
		port = "8001" // Porta padrão
	}

	databaseURL := os.Getenv("DATABASE_URL")
	if databaseURL == "" {
		logger.Fatal("DATABASE_URL deve ser definida")
	}

	masterKey := os.Getenv("MASTER_KEY")
	if masterKey == "" {
		logger.Fatal("MASTER_KEY deve ser definida")
	}

	// --- Conexão com o Banco ---
	db, err := connectDB(databaseURL)
	if err != nil {
		logger.Fatal("Não foi possível conectar ao banco de dados", zap.Error(err))
	}
	defer db.Close()

	// --- OpenTelemetry ---
	if endpoint := os.Getenv("OTEL_EXPORTER_OTLP_ENDPOINT"); endpoint != "" {
		ctx := context.Background()
		exp, err := otlptracehttp.New(ctx, otlptracehttp.WithEndpointURL(endpoint+"/v1/traces"))
		if err == nil {
			res, _ := resource.New(ctx, resource.WithAttributes(semconv.ServiceName("auth-service")))
			tp := sdktrace.NewTracerProvider(sdktrace.WithBatcher(exp), sdktrace.WithResource(res))
			otel.SetTracerProvider(tp)
			otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(propagation.TraceContext{}, propagation.Baggage{}))
			defer func() { _ = tp.Shutdown(ctx) }()
		}
	}

	app := &App{
		DB:        db,
		MasterKey: masterKey,
	}

	// --- Rotas da API ---
	mux := http.NewServeMux()
	mux.Handle("/metrics", promhttp.Handler())
	mux.Handle("/health", instrument("/health", http.HandlerFunc(app.healthHandler)))

	// Endpoint público para validar uma chave
	mux.Handle("/validate", instrument("/validate", http.HandlerFunc(app.validateKeyHandler)))

	// Endpoints de "admin" para criar/gerenciar chaves
	// Eles são protegidos pelo middleware de autenticação
	mux.Handle("/admin/keys", instrument("/admin/keys", app.masterKeyAuthMiddleware(http.HandlerFunc(app.createKeyHandler))))

	logger.Info("Serviço de Autenticação (Go) rodando na porta", zap.String("port", port))
	if err := http.ListenAndServe(":"+port, otelhttp.NewHandler(mux, "auth-service")); err != nil {
		logger.Fatal("Erro ao iniciar servidor", zap.Error(err))
	}
}

// connectDB inicializa e testa a conexão com o PostgreSQL
func connectDB(databaseURL string) (*sql.DB, error) {
	db, err := sql.Open("pgx", databaseURL)
	if err != nil {
		return nil, err
	}

	if err = db.Ping(); err != nil {
		return nil, err
	}

	logger.Info("Conectado ao PostgreSQL com sucesso!")
	return db, nil
}