package handler

import (
	"net/http"

	"github.com/xilidan/backend/pkg/json"
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

func (h *Handler) Webhook(w http.ResponseWriter, r *http.Request) {
	req := &Request{}
	json.ParseJSON(r, req)

	h.log.Debug("req", "req", req)

	response := &Response{
		Message: "test",
	}

	json.WriteJSON(w, http.StatusOK, response)
}
