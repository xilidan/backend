package handler

import (
	"encoding/json"
	"net/http"

	"log/slog"

	"github.com/xilidan/backend/gateways/meet/monitor"
)

type Handler struct {
	monitor *monitor.MeetingMonitor
	log     *slog.Logger
}

func New(monitor *monitor.MeetingMonitor, log *slog.Logger) *Handler {
	log.Debug("creating new handler")
	log.Debug("handler dependencies initialized")
	return &Handler{
		monitor: monitor,
		log:     log,
	}
}

type StartMeetingRequest struct {
	MeetingURL string `json:"meeting_url"`
}

type StartMeetingResponse struct {
	Success   bool   `json:"success"`
	MeetingID string `json:"meeting_id"`
	BotID     string `json:"bot_id"`
	Message   string `json:"message"`
}

type StopMeetingResponse struct {
	Success   bool   `json:"success"`
	MeetingID string `json:"meeting_id"`
	Message   string `json:"message"`
}

type GetTranscriptionResponse struct {
	Success   bool   `json:"success"`
	MeetingID string `json:"meeting_id"`
	FullText  string `json:"full_text"`
}

func (h *Handler) RegisterRoutes(mux *http.ServeMux) {
	h.log.Debug("registering HTTP routes")
	mux.HandleFunc("POST /api/v1/meetings/start", h.StartMeeting)
	h.log.Debug("registered route: POST /api/v1/meetings/start")
	mux.HandleFunc("POST /api/v1/meetings/{bot_id}/stop", h.StopMeeting)
	h.log.Debug("registered route: POST /api/v1/meetings/{bot_id}/stop")
	mux.HandleFunc("GET /api/v1/meetings/{bot_id}/transcription", h.GetTranscription)
	h.log.Debug("registered route: GET /api/v1/meetings/{bot_id}/transcription")
	mux.HandleFunc("GET /api/v1/health", h.HealthCheck)
	h.log.Debug("registered route: GET /api/v1/health")
	h.log.Info("all routes registered successfully")
}

func (h *Handler) HealthCheck(w http.ResponseWriter, r *http.Request) {
	h.log.Debug("health check request received",
		slog.String("method", r.Method),
		slog.String("remote_addr", r.RemoteAddr),
		slog.String("user_agent", r.UserAgent()))
	w.Header().Set("Content-Type", "application/json")
	h.log.Debug("sending health check response")
	json.NewEncoder(w).Encode(map[string]bool{"status": true})
	h.log.Debug("health check completed")
}

func (h *Handler) StartMeeting(w http.ResponseWriter, r *http.Request) {
	h.log.Info("start meeting request received",
		slog.String("method", r.Method),
		slog.String("remote_addr", r.RemoteAddr),
		slog.String("user_agent", r.UserAgent()))
	h.log.Debug("decoding request body")
	var req StartMeetingRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		h.log.Error("failed to decode request", slog.String("error", err.Error()))
		h.log.Warn("invalid request body received")
		http.Error(w, "invalid request body", http.StatusBadRequest)
		return
	}
	h.log.Debug("request decoded successfully", slog.String("meeting_url", req.MeetingURL))

	if req.MeetingURL == "" {
		h.log.Warn("meeting_url is empty")
		http.Error(w, "meeting_url is required", http.StatusBadRequest)
		return
	}
	h.log.Debug("meeting_url validated")

	h.log.Info("starting meeting", slog.String("meeting_url", req.MeetingURL))
	botID, meetingID, err := h.monitor.StartMeeting(req.MeetingURL)
	if err != nil {
		h.log.Error("failed to start meeting", slog.String("error", err.Error()))
		h.log.Error("monitor.StartMeeting returned error", 
			slog.String("error", err.Error()),
			slog.String("meeting_url", req.MeetingURL))
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	h.log.Info("meeting started successfully",
		slog.String("bot_id", botID),
		slog.String("meeting_id", meetingID))

	h.log.Debug("building response")
	resp := StartMeetingResponse{
		Success:   true,
		MeetingID: meetingID,
		BotID:     botID,
		Message:   "Bot joined meeting successfully. Feedback will be sent after 10 minutes.",
	}

	h.log.Debug("sending response")
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
	h.log.Info("start meeting response sent", slog.String("bot_id", botID))
}

func (h *Handler) StopMeeting(w http.ResponseWriter, r *http.Request) {
	h.log.Info("stop meeting request received",
		slog.String("method", r.Method),
		slog.String("remote_addr", r.RemoteAddr))
	h.log.Debug("extracting bot_id from path")
	botID := r.PathValue("bot_id")
	if botID == "" {
		h.log.Warn("bot_id is empty")
		http.Error(w, "bot_id is required", http.StatusBadRequest)
		return
	}
	h.log.Debug("bot_id extracted", slog.String("bot_id", botID))

	h.log.Info("stopping meeting", slog.String("bot_id", botID))
	if err := h.monitor.StopMeeting(botID); err != nil {
		h.log.Error("failed to stop meeting", slog.String("error", err.Error()))
		h.log.Error("monitor.StopMeeting returned error",
			slog.String("error", err.Error()),
			slog.String("bot_id", botID))
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	h.log.Info("meeting stopped successfully", slog.String("bot_id", botID))

	h.log.Debug("building stop response")
	resp := StopMeetingResponse{
		Success:   true,
		MeetingID: botID,
		Message:   "Bot left meeting successfully.",
	}

	h.log.Debug("sending stop response")
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
	h.log.Info("stop meeting response sent", slog.String("bot_id", botID))
}

func (h *Handler) GetTranscription(w http.ResponseWriter, r *http.Request) {
	h.log.Info("get transcription request received",
		slog.String("method", r.Method),
		slog.String("remote_addr", r.RemoteAddr))
	h.log.Debug("extracting bot_id from path")
	botID := r.PathValue("bot_id")
	if botID == "" {
		h.log.Warn("bot_id is empty")
		http.Error(w, "bot_id is required", http.StatusBadRequest)
		return
	}
	h.log.Debug("bot_id extracted", slog.String("bot_id", botID))

	h.log.Info("retrieving transcription", slog.String("bot_id", botID))
	transcription, err := h.monitor.GetTranscription(botID)
	if err != nil {
		h.log.Error("failed to get transcription", slog.String("error", err.Error()))
		h.log.Error("monitor.GetTranscription returned error",
			slog.String("error", err.Error()),
			slog.String("bot_id", botID))
		http.Error(w, "failed to get transcription", http.StatusInternalServerError)
		return
	}
	h.log.Info("transcription retrieved successfully",
		slog.String("bot_id", botID),
		slog.Int("transcription_length", len(transcription)))

	h.log.Debug("building transcription response")
	resp := GetTranscriptionResponse{
		Success:   true,
		MeetingID: botID,
		FullText:  transcription,
	}

	h.log.Debug("sending transcription response")
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
	h.log.Info("transcription response sent", slog.String("bot_id", botID))
}
