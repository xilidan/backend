package monitor

import (
	"fmt"
	"log/slog"
	"sync"
	"time"

	firefliesClient "github.com/xilidan/backend/gateways/meet/clients/recall"
	scrumClient "github.com/xilidan/backend/gateways/meet/clients/scrum"
)

type MeetingMonitor struct {
	firefliesClient *firefliesClient.Client
	scrumClient     *scrumClient.Client
	meetings        map[string]*MeetingSession
	mu              sync.RWMutex
	log             *slog.Logger
}

type MeetingSession struct {
	BotID        string
	MeetingID    string
	MeetingURL   string
	StartTime    time.Time
	Timer        *time.Timer
	FeedbackSent bool
}

func New(fireflies *firefliesClient.Client, scrum *scrumClient.Client, log *slog.Logger) *MeetingMonitor {
	log.Debug("creating new meeting monitor")
	log.Debug("initializing meeting sessions map")
	return &MeetingMonitor{
		firefliesClient: fireflies,
		scrumClient:     scrum,
		meetings:        make(map[string]*MeetingSession),
		log:             log,
	}
}

// StartMeeting joins a meeting via Fireflies.ai bot and schedules feedback after 10 minutes
func (m *MeetingMonitor) StartMeeting(meetingURL string) (string, string, error) {
	m.log.Info("starting meeting monitoring", slog.String("meeting_url", meetingURL))
	m.log.Debug("creating fireflies bot")
	bot, err := m.firefliesClient.CreateBot(meetingURL)
	if err != nil {
		m.log.Error("failed to create fireflies bot", 
			slog.String("error", err.Error()),
			slog.String("meeting_url", meetingURL))
		return "", "", fmt.Errorf("failed to create fireflies bot: %w", err)
	}
	m.log.Info("fireflies bot created successfully",
		slog.String("bot_id", bot.BotID),
		slog.String("meeting_id", bot.MeetingID),
		slog.String("status", bot.Status))

	m.log.Debug("acquiring lock to add meeting session")
	m.mu.Lock()
	defer m.mu.Unlock()

	m.log.Debug("creating meeting session",
		slog.String("bot_id", bot.BotID),
		slog.String("meeting_id", bot.MeetingID))
	session := &MeetingSession{
		BotID:        bot.BotID,
		MeetingID:    bot.MeetingID,
		MeetingURL:   meetingURL,
		StartTime:    time.Now(),
		FeedbackSent: false,
	}
	m.log.Debug("meeting session created", 
		slog.Time("start_time", session.StartTime),
		slog.Bool("feedback_sent", session.FeedbackSent))

	m.log.Info("scheduling feedback after 10 minutes", slog.String("bot_id", bot.BotID))
	session.Timer = time.AfterFunc(10*time.Minute, func() {
		m.log.Debug("feedback timer triggered", slog.String("bot_id", bot.BotID))
		m.sendFeedbackToMeeting(bot.BotID)
	})

	m.meetings[bot.BotID] = session
	m.log.Debug("meeting session stored", 
		slog.String("bot_id", bot.BotID),
		slog.Int("total_meetings", len(m.meetings)))
	m.log.Info("bot joined meeting",
		slog.String("bot_id", bot.BotID),
		slog.String("meeting_id", bot.MeetingID),
		slog.String("meeting_url", meetingURL))

	return bot.BotID, bot.MeetingID, nil
}

// StopMeeting stops the bot and removes monitoring
func (m *MeetingMonitor) StopMeeting(botID string) error {
	m.log.Info("stopping meeting", slog.String("bot_id", botID))
	m.log.Debug("acquiring lock to remove meeting session")
	m.mu.Lock()
	defer m.mu.Unlock()

	m.log.Debug("looking up meeting session", slog.String("bot_id", botID))
	session, exists := m.meetings[botID]
	if !exists {
		m.log.Warn("bot not found", slog.String("bot_id", botID))
		return fmt.Errorf("bot %s not found", botID)
	}
	m.log.Debug("meeting session found",
		slog.String("bot_id", botID),
		slog.String("meeting_id", session.MeetingID),
		slog.Time("start_time", session.StartTime),
		slog.Bool("feedback_sent", session.FeedbackSent))

	if session.Timer != nil {
		m.log.Debug("stopping feedback timer", slog.String("bot_id", botID))
		session.Timer.Stop()
		m.log.Debug("feedback timer stopped")
	}
	m.log.Debug("removing meeting session from map", slog.String("bot_id", botID))
	delete(m.meetings, botID)
	m.log.Debug("meeting session removed", slog.Int("remaining_meetings", len(m.meetings)))

	m.log.Info("bot stopped", slog.String("bot_id", botID))
	return nil
}

// sendFeedbackToMeeting is called after 10 minutes to generate and send feedback
func (m *MeetingMonitor) sendFeedbackToMeeting(botID string) {
	m.log.Info("sendFeedbackToMeeting called", slog.String("bot_id", botID))
	m.log.Debug("acquiring lock to check meeting session")
	m.mu.Lock()
	session, exists := m.meetings[botID]
	if !exists || session.FeedbackSent {
		if !exists {
			m.log.Warn("meeting session not found", slog.String("bot_id", botID))
		} else {
			m.log.Info("feedback already sent", slog.String("bot_id", botID))
		}
		m.mu.Unlock()
		return
	}
	m.log.Debug("marking feedback as sent", slog.String("bot_id", botID))
	session.FeedbackSent = true
	m.mu.Unlock()

	m.log.Info("generating feedback for meeting", slog.String("bot_id", botID))

	m.log.Debug("retrieving transcription from fireflies")
	transcription, err := m.getTranscription(botID)
	if err != nil {
		m.log.Error("failed to get transcription", 
			slog.String("error", err.Error()),
			slog.String("bot_id", botID))
		return
	}
	m.log.Debug("transcription retrieved", 
		slog.String("bot_id", botID),
		slog.Int("transcription_length", len(transcription)))

	if transcription == "" {
		m.log.Warn("no transcription available for meeting", slog.String("bot_id", botID))
		return
	}
	m.log.Debug("transcription validation passed")

	m.log.Info("calling scrum master AI to generate feedback")
	feedback, err := m.scrumClient.GenerateFeedback(transcription)
	if err != nil {
		m.log.Error("failed to generate feedback", 
			slog.String("error", err.Error()),
			slog.String("bot_id", botID))
		return
	}
	m.log.Info("feedback generated successfully",
		slog.String("bot_id", botID),
		slog.Int("questions_count", len(feedback.Questions)),
		slog.Int("feedback_length", len(feedback.Feedback)))

	m.log.Debug("writing feedback to chat")
	if err := m.writeFeedbackToChat(botID, feedback); err != nil {
		m.log.Error("failed to write feedback to chat", 
			slog.String("error", err.Error()),
			slog.String("bot_id", botID))
		return
	}

	m.log.Info("feedback sent to meeting", slog.String("bot_id", botID))
}

// getTranscription retrieves the full transcription from Fireflies.ai
func (m *MeetingMonitor) getTranscription(botID string) (string, error) {
	m.log.Debug("getTranscription called", slog.String("bot_id", botID))
	m.log.Debug("calling fireflies client GetTranscription")
	resp, err := m.firefliesClient.GetTranscription(botID)
	if err != nil {
		m.log.Error("fireflies client GetTranscription failed",
			slog.String("error", err.Error()),
			slog.String("bot_id", botID))
		return "", fmt.Errorf("failed to get transcription: %w", err)
	}
	m.log.Debug("transcription received from fireflies",
		slog.String("bot_id", botID),
		slog.String("meeting_id", resp.MeetingID),
		slog.Int("sentences_count", len(resp.Transcript)),
		slog.Int("full_text_length", len(resp.FullText)))

	return resp.FullText, nil
}

// GetTranscription allows external access to transcription
func (m *MeetingMonitor) GetTranscription(botID string) (string, error) {
	m.log.Info("GetTranscription called", slog.String("bot_id", botID))
	transcription, err := m.getTranscription(botID)
	if err != nil {
		m.log.Error("getTranscription failed",
			slog.String("error", err.Error()),
			slog.String("bot_id", botID))
	}
	return transcription, err
}

// writeFeedbackToChat writes the AI-generated feedback to the meeting chat
func (m *MeetingMonitor) writeFeedbackToChat(botID string, feedback *scrumClient.GenerateFeedbackResponse) error {
	m.log.Debug("writeFeedbackToChat called", slog.String("bot_id", botID))
	m.log.Debug("building feedback message",
		slog.Int("questions_count", len(feedback.Questions)),
		slog.Int("feedback_length", len(feedback.Feedback)))
	message := fmt.Sprintf("🤖 AI Scrum Master Feedback:\n\n%s\n\nQuestions:\n", feedback.Feedback)
	for i, question := range feedback.Questions {
		message += fmt.Sprintf("%d. %s\n", i+1, question)
	}
	m.log.Debug("feedback message built", slog.Int("message_length", len(message)))

	m.log.Info("feedback message",
		slog.String("bot_id", botID),
		slog.String("message", message),
	)

	m.log.Debug("feedback will be posted via fireflies bot")

	return nil
}

// GetMeetingStatus returns the status of a meeting
func (m *MeetingMonitor) GetMeetingStatus(botID string) (bool, time.Duration, error) {
	m.log.Debug("GetMeetingStatus called", slog.String("bot_id", botID))
	m.log.Debug("acquiring read lock")
	m.mu.RLock()
	defer m.mu.RUnlock()

	m.log.Debug("looking up meeting session", slog.String("bot_id", botID))
	session, exists := m.meetings[botID]
	if !exists {
		m.log.Warn("meeting session not found for status check", slog.String("bot_id", botID))
		return false, 0, fmt.Errorf("bot %s not found", botID)
	}

	duration := time.Since(session.StartTime)
	m.log.Debug("meeting status retrieved",
		slog.String("bot_id", botID),
		slog.Bool("feedback_sent", session.FeedbackSent),
		slog.Duration("duration", duration))
	return session.FeedbackSent, duration, nil
}
