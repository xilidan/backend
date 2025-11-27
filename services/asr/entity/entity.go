package entity

import "time"

type TranscribeAudioRequest struct {
	AudioData  []byte
	MeetingID  string
	Format     string
	SampleRate int32
}

type TranscribeAudioResponse struct {
	Text       string
	MeetingID  string
	Confidence float32
}

type GetTranscriptionRequest struct {
	MeetingID string
}

type GetTranscriptionResponse struct {
	MeetingID string
	FullText  string
	CreatedAt time.Time
	UpdatedAt time.Time
}

type SaveTranscriptionRequest struct {
	MeetingID string
	Text      string
}

type SaveTranscriptionResponse struct {
	Success   bool
	MeetingID string
}

type Transcription struct {
	ID        string
	MeetingID string
	Text      string
	CreatedAt time.Time
	UpdatedAt time.Time
}
