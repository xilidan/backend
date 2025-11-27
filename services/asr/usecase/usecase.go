package usecase

import (
	"context"
	"fmt"

	"github.com/xilidan/backend/services/asr/entity"
	"github.com/xilidan/backend/services/asr/storage"
)

type Usecase interface {
	TranscribeAudio(ctx context.Context, req *entity.TranscribeAudioRequest) (*entity.TranscribeAudioResponse, error)
	GetTranscription(ctx context.Context, req *entity.GetTranscriptionRequest) (*entity.GetTranscriptionResponse, error)
	SaveTranscription(ctx context.Context, req *entity.SaveTranscriptionRequest) (*entity.SaveTranscriptionResponse, error)
}

type usecase struct {
	storage storage.Storage
}

func New(storage storage.Storage) Usecase {
	return &usecase{
		storage: storage,
	}
}

func (u *usecase) TranscribeAudio(ctx context.Context, req *entity.TranscribeAudioRequest) (*entity.TranscribeAudioResponse, error) {
	// TODO: Integrate with actual speech-to-text API (Google Cloud Speech, Azure, Whisper, etc.)
	// For now, return mock transcription
	mockText := fmt.Sprintf("Transcribed audio for meeting %s (sample rate: %d)", req.MeetingID, req.SampleRate)

	// Append to existing transcription
	err := u.storage.UpdateTranscription(ctx, req.MeetingID, mockText)
	if err != nil {
		return nil, err
	}

	return &entity.TranscribeAudioResponse{
		Text:       mockText,
		MeetingID:  req.MeetingID,
		Confidence: 0.95,
	}, nil
}

func (u *usecase) GetTranscription(ctx context.Context, req *entity.GetTranscriptionRequest) (*entity.GetTranscriptionResponse, error) {
	transcription, err := u.storage.GetTranscription(ctx, req.MeetingID)
	if err != nil {
		return nil, err
	}

	return &entity.GetTranscriptionResponse{
		MeetingID: transcription.MeetingID,
		FullText:  transcription.Text,
		CreatedAt: transcription.CreatedAt,
		UpdatedAt: transcription.UpdatedAt,
	}, nil
}

func (u *usecase) SaveTranscription(ctx context.Context, req *entity.SaveTranscriptionRequest) (*entity.SaveTranscriptionResponse, error) {
	_, err := u.storage.SaveTranscription(ctx, req)
	if err != nil {
		return &entity.SaveTranscriptionResponse{
			Success:   false,
			MeetingID: req.MeetingID,
		}, err
	}

	return &entity.SaveTranscriptionResponse{
		Success:   true,
		MeetingID: req.MeetingID,
	}, nil
}
