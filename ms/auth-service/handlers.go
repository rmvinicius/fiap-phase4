package main

import (
	//"crypto/sha256"
	//"encoding/hex"
	"context"
	"encoding/json"
	"net/http"
	"strings"

	"go.opentelemetry.io/otel/trace"
	"go.uber.org/zap"
)

// Estrutura para o corpo da requisição de criação de chave
type CreateKeyRequest struct {
	Name string `json:"name"`
}

// Estrutura para a resposta da criação de chave
type CreateKeyResponse struct {
	Name    string `json:"name"`
	Key     string `json:"key"` // A chave em texto plano é retornada APENAS uma vez
	Message string `json:"message"`
}

// healthHandler é um simples endpoint de verificação de saúde
func (a *App) healthHandler(w http.ResponseWriter, r *http.Request) {
	log := logger.With(traceFields(r.Context())...)
	w.WriteHeader(http.StatusOK)
	if err := json.NewEncoder(w).Encode(map[string]string{"status": "ok"}); err != nil {
		log.Error("failed to encode health response", zap.Error(err))
	}
}

// validateKeyHandler verifica se uma chave de API (enviada via Header) é válida
func (a *App) validateKeyHandler(w http.ResponseWriter, r *http.Request) {
	log := logger.With(traceFields(r.Context())...)
	// Extrai a chave do header "Authorization: Bearer <key>"
	authHeader := r.Header.Get("Authorization")
	keyString := strings.TrimPrefix(authHeader, "Bearer ")

	if keyString == "" {
		http.Error(w, "Authorization header não encontrado", http.StatusUnauthorized)
		return
	}

	// Calcula o hash da chave recebida
	keyHash := hashAPIKey(keyString)

	// Verifica se o hash existe no banco de dados
	var id int
	err := a.DB.QueryRow("SELECT id FROM api_keys WHERE key_hash = $1 AND is_active = true", keyHash).Scan(&id)
	if err != nil {
		// Se não encontrar (sql.ErrNoRows), ou qualquer outro erro, a chave é inválida
		log.Warn("Falha na validação da chave", zap.String("key_hash_prefix", keyHash[:6]), zap.Error(err))
		http.Error(w, "Chave de API inválida ou inativa", http.StatusUnauthorized)
		return
	}

	// Chave válida
	w.WriteHeader(http.StatusOK)
	if err := json.NewEncoder(w).Encode(map[string]string{"message": "Chave válida"}); err != nil {
		log.Error("failed to encode validate response", zap.Error(err))
	}
}

// createKeyHandler cria uma nova chave de API
func (a *App) createKeyHandler(w http.ResponseWriter, r *http.Request) {
	log := logger.With(traceFields(r.Context())...)
	if r.Method != http.MethodPost {
		http.Error(w, "Método não permitido", http.StatusMethodNotAllowed)
		return
	}

	var req CreateKeyRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Corpo da requisição inválido", http.StatusBadRequest)
		return
	}

	if req.Name == "" {
		http.Error(w, "O campo 'name' é obrigatório", http.StatusBadRequest)
		return
	}

	// Gera uma nova chave e seu hash
	newKey, err := generateAPIKey()
	if err != nil {
		http.Error(w, "Erro ao gerar a chave", http.StatusInternalServerError)
		return
	}
	newKeyHash := hashAPIKey(newKey)

	// Salva o hash no banco de dados
	var newID int
	err = a.DB.QueryRow(
		"INSERT INTO api_keys (name, key_hash) VALUES ($1, $2) RETURNING id",
		req.Name, newKeyHash,
	).Scan(&newID)

	if err != nil {
		log.Error("Erro ao salvar a chave no banco", zap.Error(err))
		http.Error(w, "Erro ao salvar a chave", http.StatusInternalServerError)
		return
	}

	log.Info("Nova chave criada com sucesso", zap.Int("id", newID), zap.String("name", req.Name))
	w.WriteHeader(http.StatusCreated)
	if err := json.NewEncoder(w).Encode(CreateKeyResponse{
		Name:    req.Name,
		Key:     newKey, // Retorna a chave em texto plano pela última vez
		Message: "Guarde esta chave com segurança! Você não poderá vê-la novamente.",
	}); err != nil {
		log.Error("failed to encode create key response", zap.Error(err))
	}
}

// --- Middleware ---

// masterKeyAuthMiddleware protege endpoints que só podem ser acessados com a MASTER_KEY
func (a *App) masterKeyAuthMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		authHeader := r.Header.Get("Authorization")
		keyString := strings.TrimPrefix(authHeader, "Bearer ")

		if keyString != a.MasterKey {
			http.Error(w, "Acesso não autorizado", http.StatusForbidden)
			return
		}
		// Se a chave for válida, continua para o handler principal
		next.ServeHTTP(w, r)
	})
}