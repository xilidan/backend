package handler

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"sync"

	jsonpkg "github.com/xilidan/backend/pkg/json"
)

type (
	Request struct {
		SessionID        string        `json:"session_id"`
		Trigger          string        `json:"trigger"`
		Title            string        `json:"title"`
		StartTime        string        `json:"start_time"`
		EndTime          string        `json:"end_time"`
		Participants     []Participant `json:"participants"`
		Owner            Participant   `json:"owner"`
		Summary          string        `json:"summary"`
		ActionItems      []TextItem    `json:"action_items"`
		KeyQuestions     []TextItem    `json:"key_questions"`
		Topics           []TextItem    `json:"topics"`
		ReportURL        string        `json:"report_url"`
		ChapterSummaries []Chapter     `json:"chapter_summaries"`
		Transcript       Transcript    `json:"transcript"`
	}
)

const (
	telegramToken = "8351689519:AAEi7mN_lZBjTZYlRh6WInEOryzqwE6UgIE"
)

var (
	chatID   string
	chatIDMu sync.RWMutex
)

type TextItem struct {
	Text string `json:"text"`
}

type Participant struct {
	Name  string `json:"name"`
	Email string `json:"email"`
}

type Chapter struct {
	Title       string     `json:"title"`
	Description string     `json:"description"`
	Topics      []TextItem `json:"topics"`
}

type Transcript struct {
	Speakers      []Speaker      `json:"speakers"`
	SpeakerBlocks []SpeakerBlock `json:"speaker_blocks"`
}

type Speaker struct {
	Name string `json:"name"`
}

type SpeakerBlock struct {
	StartTime string  `json:"start_time"`
	EndTime   string  `json:"end_time"`
	Speaker   Speaker `json:"speaker"`
	Words     string  `json:"words"`
}

type Response struct {
	Message string
}

type TelegramMessage struct {
	ChatID    string `json:"chat_id"`
	Text      string `json:"text"`
	ParseMode string `json:"parse_mode"`
}

type TelegramUpdate struct {
	UpdateID int `json:"update_id"`
	Message  struct {
		MessageID int `json:"message_id"`
		From      struct {
			ID        int64  `json:"id"`
			IsBot     bool   `json:"is_bot"`
			FirstName string `json:"first_name"`
			Username  string `json:"username"`
		} `json:"from"`
		Chat struct {
			ID    int64  `json:"id"`
			Title string `json:"title"`
			Type  string `json:"type"`
		} `json:"chat"`
		Date int    `json:"date"`
		Text string `json:"text"`
	} `json:"message"`
}

type TelegramUpdatesResponse struct {
	OK     bool             `json:"ok"`
	Result []TelegramUpdate `json:"result"`
}

type ChatIDResponse struct {
	ChatID      string `json:"chat_id"`
	IsConnected bool   `json:"is_connected"`
	Message     string `json:"message"`
}

type AnalyzeResponse struct {
	Text string `json:"text"`
}

func (h *Handler) Webhook(w http.ResponseWriter, r *http.Request) {
	req := &Request{}
	jsonpkg.ParseJSON(r, req)

	h.log.Debug("req", "req", req)

	// Send the same JSON to analyze-transcription endpoint
	analysisResponse, err := sendToAnalyze(req)
	if err != nil {
		h.log.Error("failed to send to analyze endpoint", "error", err)
	}

	// Send to Telegram if chat ID is set
	chatIDMu.RLock()
	currentChatID := chatID
	chatIDMu.RUnlock()

	if currentChatID != "" {
		// Send original meeting summary
		if err := sendToTelegram(req, currentChatID); err != nil {
			h.log.Error("failed to send to telegram", "error", err)
		}

		// Send analysis response if available
		if analysisResponse != nil && analysisResponse.Text != "" {
			if err := sendAnalysisToTelegram(analysisResponse.Text, currentChatID); err != nil {
				h.log.Error("failed to send analysis to telegram", "error", err)
			}
		}
	} else {
		h.log.Warn("telegram chat ID not set, skipping message send")
	}

	response := &Response{
		Message: "test",
	}

	jsonpkg.WriteJSON(w, http.StatusOK, response)
}

// GetChatID endpoint to retrieve and set the chat ID
func (h *Handler) GetChatID(w http.ResponseWriter, r *http.Request) {
	url := fmt.Sprintf("https://api.telegram.org/bot%s/getUpdates", telegramToken)
	resp, err := http.Get(url)
	if err != nil {
		h.log.Error("failed to get updates", "error", err)
		jsonpkg.WriteJSON(w, http.StatusInternalServerError, ChatIDResponse{
			Message: "Failed to fetch updates from Telegram",
		})
		return
	}
	defer resp.Body.Close()

	var updates TelegramUpdatesResponse
	if err := json.NewDecoder(resp.Body).Decode(&updates); err != nil {
		h.log.Error("failed to decode updates", "error", err)
		jsonpkg.WriteJSON(w, http.StatusInternalServerError, ChatIDResponse{
			Message: "Failed to parse Telegram response",
		})
		return
	}

	// Find the most recent group chat
	var foundChatID int64
	var chatTitle string
	for i := len(updates.Result) - 1; i >= 0; i-- {
		update := updates.Result[i]
		if update.Message.Chat.Type == "group" || update.Message.Chat.Type == "supergroup" {
			foundChatID = update.Message.Chat.ID
			chatTitle = update.Message.Chat.Title
			break
		}
	}

	if foundChatID == 0 {
		jsonpkg.WriteJSON(w, http.StatusOK, ChatIDResponse{
			IsConnected: false,
			Message:     "No group chat found. Please send a message in the group with the bot.",
		})
		return
	}

	// Save the chat ID
	chatIDMu.Lock()
	chatID = fmt.Sprintf("%d", foundChatID)
	chatIDMu.Unlock()

	h.log.Info("chat ID set", "chatID", chatID, "title", chatTitle)

	// Send confirmation message to the group
	confirmMsg := TelegramMessage{
		ChatID:    chatID,
		Text:      "✅ <b>Bot Connected!</b>\n\nThis group will now receive meeting summaries.",
		ParseMode: "HTML",
	}

	jsonData, _ := json.Marshal(confirmMsg)
	http.Post(
		fmt.Sprintf("https://api.telegram.org/bot%s/sendMessage", telegramToken),
		"application/json",
		bytes.NewBuffer(jsonData),
	)

	jsonpkg.WriteJSON(w, http.StatusOK, ChatIDResponse{
		ChatID:      chatID,
		IsConnected: true,
		Message:     fmt.Sprintf("Successfully connected to group: %s", chatTitle),
	})
}

// SetChatID endpoint to manually set the chat ID
func (h *Handler) SetChatID(w http.ResponseWriter, r *http.Request) {
	var req struct {
		ChatID string `json:"chat_id"`
	}

	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		jsonpkg.WriteJSON(w, http.StatusBadRequest, ChatIDResponse{
			Message: "Invalid request body",
		})
		return
	}

	chatIDMu.Lock()
	chatID = req.ChatID
	chatIDMu.Unlock()

	h.log.Info("chat ID manually set", "chatID", chatID)

	jsonpkg.WriteJSON(w, http.StatusOK, ChatIDResponse{
		ChatID:      chatID,
		IsConnected: true,
		Message:     "Chat ID set successfully",
	})
}

func sendToTelegram(req *Request, targetChatID string) error {
	message := formatMessage(req)

	telegramMsg := TelegramMessage{
		ChatID:    targetChatID,
		Text:      message,
		ParseMode: "HTML",
	}

	jsonData, err := json.Marshal(telegramMsg)
	if err != nil {
		return fmt.Errorf("failed to marshal telegram message: %w", err)
	}

	url := fmt.Sprintf("https://api.telegram.org/bot%s/sendMessage", telegramToken)
	resp, err := http.Post(url, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return fmt.Errorf("failed to send telegram message: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("telegram API returned status: %d", resp.StatusCode)
	}

	return nil
}

func formatMessage(req *Request) string {
	var sb strings.Builder

	sb.WriteString(fmt.Sprintf("<b>📝 Meeting Summary</b>\n\n"))
	sb.WriteString(fmt.Sprintf("<b>Title:</b> %s\n", escapeHTML(req.Title)))
	sb.WriteString(fmt.Sprintf("<b>Session ID:</b> %s\n", escapeHTML(req.SessionID)))
	sb.WriteString(fmt.Sprintf("<b>Time:</b> %s - %s\n\n", escapeHTML(req.StartTime), escapeHTML(req.EndTime)))

	// Owner
	if req.Owner.Name != "" {
		sb.WriteString(fmt.Sprintf("<b>Owner:</b> %s", escapeHTML(req.Owner.Name)))
		if req.Owner.Email != "" {
			sb.WriteString(fmt.Sprintf(" (%s)", escapeHTML(req.Owner.Email)))
		}
		sb.WriteString("\n\n")
	}

	// Participants
	if len(req.Participants) > 0 {
		sb.WriteString("<b>Participants:</b>\n")
		for _, p := range req.Participants {
			sb.WriteString(fmt.Sprintf("• %s", escapeHTML(p.Name)))
			if p.Email != "" {
				sb.WriteString(fmt.Sprintf(" (%s)", escapeHTML(p.Email)))
			}
			sb.WriteString("\n")
		}
		sb.WriteString("\n")
	}

	// Summary
	if req.Summary != "" {
		sb.WriteString(fmt.Sprintf("<b>Summary:</b>\n%s\n\n", escapeHTML(req.Summary)))
	}

	// Action Items
	if len(req.ActionItems) > 0 {
		sb.WriteString("<b>Action Items:</b>\n")
		for i, item := range req.ActionItems {
			sb.WriteString(fmt.Sprintf("%d. %s\n", i+1, escapeHTML(item.Text)))
		}
		sb.WriteString("\n")
	}

	// Key Questions
	if len(req.KeyQuestions) > 0 {
		sb.WriteString("<b>Key Questions:</b>\n")
		for i, item := range req.KeyQuestions {
			sb.WriteString(fmt.Sprintf("%d. %s\n", i+1, escapeHTML(item.Text)))
		}
		sb.WriteString("\n")
	}

	// Topics
	if len(req.Topics) > 0 {
		sb.WriteString("<b>Topics:</b>\n")
		for _, item := range req.Topics {
			sb.WriteString(fmt.Sprintf("• %s\n", escapeHTML(item.Text)))
		}
		sb.WriteString("\n")
	}

	// Report URL
	if req.ReportURL != "" {
		sb.WriteString(fmt.Sprintf("<b>Report:</b> <a href=\"%s\">View Full Report</a>\n", escapeHTML(req.ReportURL)))
	}

	return sb.String()
}

func escapeHTML(s string) string {
	s = strings.ReplaceAll(s, "&", "&amp;")
	s = strings.ReplaceAll(s, "<", "&lt;")
	s = strings.ReplaceAll(s, ">", "&gt;")
	return s
}

func sendToAnalyze(req *Request) (*AnalyzeResponse, error) {
	jsonData, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	url := "https://scrum.azed.kz/analyze-transcription"
	resp, err := http.Post(url, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to send to analyze endpoint: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("analyze endpoint returned status: %d", resp.StatusCode)
	}

	var analyzeResp AnalyzeResponse
	if err := json.NewDecoder(resp.Body).Decode(&analyzeResp); err != nil {
		return nil, fmt.Errorf("failed to decode analyze response: %w", err)
	}

	return &analyzeResp, nil
}

func sendAnalysisToTelegram(text string, targetChatID string) error {
	message := fmt.Sprintf("<b>🤖 AI Analysis</b>\n\n%s", escapeHTML(text))

	telegramMsg := TelegramMessage{
		ChatID:    targetChatID,
		Text:      message,
		ParseMode: "HTML",
	}

	jsonData, err := json.Marshal(telegramMsg)
	if err != nil {
		return fmt.Errorf("failed to marshal telegram message: %w", err)
	}

	url := fmt.Sprintf("https://api.telegram.org/bot%s/sendMessage", telegramToken)
	resp, err := http.Post(url, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return fmt.Errorf("failed to send telegram message: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("telegram API returned status: %d", resp.StatusCode)
	}

	return nil
}
