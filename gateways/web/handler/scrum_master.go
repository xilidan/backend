package handler

import (
	"encoding/json"
	"net/http"
	"time"
)

type (
	GenerateRequest struct {
		Prompt string `json:"prompt"`
	}

	GenerateResponse struct {
		Content string `json:"content"`
		IsEnd   bool   `json:"is_end"`
	}
)

var (
	mockMessage = "Microservices are a software architecture style where a system is composed of small, independent services that communicate over APIs and can be deployed separately."
)

func (h *handler) GenerateHandler(w http.ResponseWriter, r *http.Request) {
	var req GenerateRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Transfer-Encoding", "chunked")
	w.WriteHeader(http.StatusOK)

	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "Streaming unsupported", http.StatusInternalServerError)
		return
	}

	chunkSize := 25
	for i := 0; i < len(mockMessage); i += chunkSize {
		end := i + chunkSize
		if end > len(mockMessage) {
			end = len(mockMessage)
		}

		chunk := GenerateResponse{
			Content: mockMessage[i:end],
			IsEnd:   false,
		}

		_ = json.NewEncoder(w).Encode(chunk)
		flusher.Flush()

		time.Sleep(300 * time.Millisecond)
	}

	final := GenerateResponse{
		Content: "",
		IsEnd:   true,
	}

	_ = json.NewEncoder(w).Encode(final)
	flusher.Flush()
}
