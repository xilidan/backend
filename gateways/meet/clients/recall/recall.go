package recall

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"time"
)

type Client struct {
	apiKey     string
	baseURL    string
	httpClient *http.Client
	log        *slog.Logger
}

type CreateBotRequest struct {
	MeetingURL string `json:"meeting_url"`
	Title      string `json:"title,omitempty"`
}

type CreateBotResponse struct {
	BotID     string `json:"id"`
	MeetingID string `json:"meeting_id"`
	Status    string `json:"status"`
}

type TranscriptionResponse struct {
	MeetingID  string     `json:"meeting_id"`
	Transcript []Sentence `json:"sentences"`
	FullText   string     `json:"transcript_text"`
}

type Sentence struct {
	Text        string  `json:"text"`
	SpeakerName string  `json:"speaker_name"`
	SpeakerID   int     `json:"speaker_id"`
	StartTime   float64 `json:"start_time"`
	EndTime     float64 `json:"end_time"`
}

type MeetingInfo struct {
	ID           string    `json:"id"`
	Title        string    `json:"title"`
	MeetingURL   string    `json:"meeting_url"`
	StartTime    time.Time `json:"start_time"`
	EndTime      time.Time `json:"end_time"`
	Status       string    `json:"status"`
	TranscriptID string    `json:"transcript_id"`
}

func New(apiKey string) *Client {
	log := slog.Default()
	log.Debug("creating fireflies client",
		slog.String("base_url", "https://api.fireflies.ai/graphql"),
		slog.Bool("api_key_set", apiKey != ""))
	return &Client{
		apiKey:     apiKey,
		baseURL:    "https://api.fireflies.ai/graphql",
		httpClient: &http.Client{},
		log:        log,
	}
}

// CreateBot joins a meeting via URL using Fireflies.ai
func (c *Client) CreateBot(meetingURL string) (*CreateBotResponse, error) {
	c.log.Info("CreateBot called", slog.String("meeting_url", meetingURL))
	c.log.Debug("building GraphQL mutation")

	// 1. Send addToLiveMeeting mutation
	mutation := `
		mutation {
			addToLiveMeeting(meeting_link: "%s") {
				success
				message
			}
		}
	`

	c.log.Debug("preparing GraphQL mutation")
	graphqlQuery := map[string]string{
		"query": fmt.Sprintf(mutation, meetingURL),
	}

	jsonData, err := json.Marshal(graphqlQuery)
	if err != nil {
		c.log.Error("failed to marshal GraphQL mutation", slog.String("error", err.Error()))
		return nil, err
	}

	c.log.Debug("sending request to Fireflies API")
	resp, err := c.sendRequest(jsonData)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var result struct {
		Data struct {
			AddToLiveMeeting struct {
				Success bool   `json:"success"`
				Message string `json:"message"`
			} `json:"addToLiveMeeting"`
		} `json:"data"`
		Errors []struct {
			Message string `json:"message"`
		} `json:"errors"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		c.log.Error("failed to decode response", slog.String("error", err.Error()))
		return nil, err
	}

	if len(result.Errors) > 0 {
		c.log.Error("graphql errors", slog.String("error", result.Errors[0].Message))
		return nil, fmt.Errorf("graphql error: %s", result.Errors[0].Message)
	}

	if !result.Data.AddToLiveMeeting.Success {
		return nil, fmt.Errorf("failed to add bot to meeting: %s", result.Data.AddToLiveMeeting.Message)
	}

	c.log.Info("bot join request sent successfully", slog.String("message", result.Data.AddToLiveMeeting.Message))

	// 2. Poll active_meetings to get the ID
	// The bot might take a few seconds to appear in the active meetings list
	c.log.Info("polling for bot ID")

	for i := 0; i < 5; i++ {
		time.Sleep(2 * time.Second)
		id, err := c.findActiveMeetingID(meetingURL)
		if err != nil {
			c.log.Warn("failed to query active meetings", slog.String("error", err.Error()))
			continue
		}
		if id != "" {
			c.log.Info("bot ID found", slog.String("bot_id", id))
			return &CreateBotResponse{
				BotID:     id,
				MeetingID: id,
				Status:    "joining",
			}, nil
		}
		c.log.Debug("bot ID not found yet, retrying...")
	}

	return nil, fmt.Errorf("bot joined but failed to retrieve ID after polling")
}

func (c *Client) findActiveMeetingID(meetingURL string) (string, error) {
	query := `
		query {
			active_meetings {
				id
				meeting_link
			}
		}
	`
	graphqlQuery := map[string]string{
		"query": query,
	}

	jsonData, _ := json.Marshal(graphqlQuery)
	resp, err := c.sendRequest(jsonData)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	var result struct {
		Data struct {
			ActiveMeetings []struct {
				ID          string `json:"id"`
				MeetingLink string `json:"meeting_link"`
			} `json:"active_meetings"`
		} `json:"data"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return "", err
	}

	for _, meeting := range result.Data.ActiveMeetings {
		if meeting.MeetingLink == meetingURL {
			return meeting.ID, nil
		}
	}
	return "", nil
}

func (c *Client) sendRequest(jsonData []byte) (*http.Response, error) {
	req, err := http.NewRequest("POST", c.baseURL, bytes.NewBuffer(jsonData))
	if err != nil {
		c.log.Error("failed to create HTTP request", slog.String("error", err.Error()))
		return nil, err
	}

	req.Header.Set("Authorization", "Bearer "+c.apiKey)
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		c.log.Error("HTTP request failed", slog.String("error", err.Error()))
		return nil, err
	}

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		resp.Body.Close()
		c.log.Error("API request failed",
			slog.Int("status_code", resp.StatusCode),
			slog.String("body", string(body)))
		return nil, fmt.Errorf("API request failed with status %d: %s", resp.StatusCode, string(body))
	}

	return resp, nil
}

// GetTranscription retrieves the transcription from Fireflies.ai
func (c *Client) GetTranscription(botID string) (*TranscriptionResponse, error) {
	c.log.Info("GetTranscription called", slog.String("bot_id", botID))
	c.log.Debug("building GraphQL query")
	query := `
		query {
			transcript(id: "%s") {
				id
				title
				sentences {
					text
					speaker_name
					speaker_id
					start_time
					end_time
				}
			}
		}
	`

	c.log.Debug("preparing GraphQL query")
	graphqlQuery := map[string]string{
		"query": fmt.Sprintf(query, botID),
	}

	c.log.Debug("marshaling GraphQL query to JSON")
	jsonData, err := json.Marshal(graphqlQuery)
	if err != nil {
		c.log.Error("failed to marshal GraphQL query", slog.String("error", err.Error()))
		return nil, err
	}
	c.log.Debug("GraphQL query marshaled", slog.Int("json_size", len(jsonData)))

	c.log.Debug("creating HTTP POST request", slog.String("url", c.baseURL))
	req, err := http.NewRequest("POST", c.baseURL, bytes.NewBuffer(jsonData))
	if err != nil {
		c.log.Error("failed to create HTTP request", slog.String("error", err.Error()))
		return nil, err
	}
	c.log.Debug("HTTP request created")

	c.log.Debug("setting request headers")
	req.Header.Set("Authorization", "Bearer "+c.apiKey)
	req.Header.Set("Content-Type", "application/json")
	c.log.Debug("headers set")

	c.log.Info("sending request to Fireflies API")
	resp, err := c.httpClient.Do(req)
	if err != nil {
		c.log.Error("HTTP request failed", slog.String("error", err.Error()))
		return nil, err
	}
	defer resp.Body.Close()
	c.log.Debug("response received", slog.Int("status_code", resp.StatusCode))

	c.log.Debug("decoding response body")
	var result struct {
		Data struct {
			Transcript struct {
				ID        string     `json:"id"`
				Title     string     `json:"title"`
				Sentences []Sentence `json:"sentences"`
			} `json:"transcript"`
		} `json:"data"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		c.log.Error("failed to decode response", slog.String("error", err.Error()))
		return nil, err
	}
	c.log.Debug("response decoded successfully",
		slog.String("transcript_id", result.Data.Transcript.ID),
		slog.String("title", result.Data.Transcript.Title),
		slog.Int("sentences_count", len(result.Data.Transcript.Sentences)))

	c.log.Debug("building full text from sentences")
	var fullText string
	for i, sentence := range result.Data.Transcript.Sentences {
		fullText += fmt.Sprintf("[%s]: %s\n", sentence.SpeakerName, sentence.Text)
		if i < 3 {
			c.log.Debug("sentence processed",
				slog.Int("index", i),
				slog.String("speaker", sentence.SpeakerName),
				slog.Float64("start_time", sentence.StartTime),
				slog.Float64("end_time", sentence.EndTime))
		}
	}
	c.log.Info("transcription retrieved successfully",
		slog.String("bot_id", botID),
		slog.Int("sentences_count", len(result.Data.Transcript.Sentences)),
		slog.Int("full_text_length", len(fullText)))

	return &TranscriptionResponse{
		MeetingID:  result.Data.Transcript.ID,
		Transcript: result.Data.Transcript.Sentences,
		FullText:   fullText,
	}, nil
}
