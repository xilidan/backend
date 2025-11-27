package scrum

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"

	config "github.com/xilidan/backend/config/meet"
)

type Client struct {
	baseURL    string
	httpClient *http.Client
	log        *slog.Logger
}

type GenerateFeedbackRequest struct {
	Transcription string `json:"transcription"`
}

type GenerateFeedbackResponse struct {
	Feedback  string   `json:"feedback"`
	Questions []string `json:"questions"`
}

func New(cfg *config.ServiceConfig) *Client {
	log := slog.Default()
	baseURL := fmt.Sprintf("http://%s:%d", cfg.Url, cfg.Port)
	log.Debug("creating scrum client",
		slog.String("base_url", baseURL),
		slog.String("service_url", cfg.Url),
		slog.Int("service_port", cfg.Port))
	return &Client{
		baseURL:    baseURL,
		httpClient: &http.Client{},
		log:        log,
	}
}

func (c *Client) GenerateFeedback(transcription string) (*GenerateFeedbackResponse, error) {
	c.log.Info("GenerateFeedback called", slog.Int("transcription_length", len(transcription)))
	c.log.Debug("building request body")
	reqBody := GenerateFeedbackRequest{
		Transcription: transcription,
	}

	c.log.Debug("marshaling request to JSON")
	jsonData, err := json.Marshal(reqBody)
	if err != nil {
		c.log.Error("failed to marshal request", slog.String("error", err.Error()))
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}
	c.log.Debug("request marshaled", slog.Int("json_size", len(jsonData)))

	url := c.baseURL + "/api/v1/generate-feedback"
	c.log.Info("sending POST request to scrum service", slog.String("url", url))
	c.log.Debug("calling httpClient.Post")
	resp, err := c.httpClient.Post(
		url,
		"application/json",
		bytes.NewBuffer(jsonData),
	)
	if err != nil {
		c.log.Error("HTTP request failed", 
			slog.String("error", err.Error()),
			slog.String("url", url))
		return nil, fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()
	c.log.Debug("response received", slog.Int("status_code", resp.StatusCode))

	if resp.StatusCode != http.StatusOK {
		c.log.Warn("unexpected status code", slog.Int("status_code", resp.StatusCode))
		body, _ := io.ReadAll(resp.Body)
		c.log.Error("scrum service returned error",
			slog.Int("status_code", resp.StatusCode),
			slog.String("response_body", string(body)))
		return nil, fmt.Errorf("unexpected status code: %d, body: %s", resp.StatusCode, string(body))
	}

	c.log.Debug("decoding response body")
	var result GenerateFeedbackResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		c.log.Error("failed to decode response", slog.String("error", err.Error()))
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}
	c.log.Debug("response decoded successfully",
		slog.Int("feedback_length", len(result.Feedback)),
		slog.Int("questions_count", len(result.Questions)))

	c.log.Info("feedback generated successfully",
		slog.Int("questions_count", len(result.Questions)),
		slog.Int("feedback_length", len(result.Feedback)))
	return &result, nil
}
