package storage

import (
	"context"
	"time"

	"github.com/google/uuid"
	"github.com/xilidan/backend/services/asr/entity"
)

type Storage interface {
	SaveTranscription(ctx context.Context, req *entity.SaveTranscriptionRequest) (*entity.Transcription, error)
	GetTranscription(ctx context.Context, meetingID string) (*entity.Transcription, error)
	UpdateTranscription(ctx context.Context, meetingID, text string) error
}

type storage struct {
	transcriptions map[string]*entity.Transcription
}

func New() Storage {
	return &storage{
		transcriptions: make(map[string]*entity.Transcription),
	}
}

func (s *storage) SaveTranscription(ctx context.Context, req *entity.SaveTranscriptionRequest) (*entity.Transcription, error) {
	transcription := &entity.Transcription{
		ID:        uuid.New().String(),
		MeetingID: req.MeetingID,
		Text:      req.Text,
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
	}

	s.transcriptions[req.MeetingID] = transcription
	return transcription, nil
}

func (s *storage) GetTranscription(ctx context.Context, meetingID string) (*entity.Transcription, error) {
	transcription, exists := s.transcriptions[meetingID]
	if !exists {
		// Return empty transcription if not found
		return &entity.Transcription{
			MeetingID: meetingID,
			Text:      "",
			CreatedAt: time.Now(),
			UpdatedAt: time.Now(),
		}, nil
	}
	return transcription, nil
}

func (s *storage) UpdateTranscription(ctx context.Context, meetingID, text string) error {
	transcription, exists := s.transcriptions[meetingID]
	if !exists {
		// Create new if doesn't exist
		transcription = &entity.Transcription{
			ID:        uuid.New().String(),
			MeetingID: meetingID,
			Text:      text,
			CreatedAt: time.Now(),
			UpdatedAt: time.Now(),
		}
		s.transcriptions[meetingID] = transcription
		return nil
	}

	transcription.Text += " " + text
	transcription.UpdatedAt = time.Now()
	return nil
}
