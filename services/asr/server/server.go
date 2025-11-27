package server

import (
	"context"

	"github.com/xilidan/backend/services/asr/entity"
	"github.com/xilidan/backend/services/asr/usecase"
	pb "github.com/xilidan/backend/specs/proto/asr"
	"google.golang.org/grpc"
)

type Server struct {
	pb.UnimplementedAsrServiceServer

	usecase usecase.Usecase
}

func NewServerOptions(usecase usecase.Usecase) *Server {
	return &Server{
		usecase: usecase,
	}
}

func (s *Server) NewServer() (*grpc.Server, error) {
	srv := grpc.NewServer()
	pb.RegisterAsrServiceServer(srv, s)
	return srv, nil
}

func (s *Server) HealthCheck(ctx context.Context, req *pb.HealthCheckReq) (*pb.HealthCheckResp, error) {
	return &pb.HealthCheckResp{
		Status: true,
	}, nil
}

func (s *Server) TranscribeAudio(ctx context.Context, req *pb.TranscribeAudioReq) (*pb.TranscribeAudioResp, error) {
	result, err := s.usecase.TranscribeAudio(ctx, &entity.TranscribeAudioRequest{
		AudioData:  req.AudioData,
		MeetingID:  req.MeetingId,
		Format:     req.Format,
		SampleRate: req.SampleRate,
	})
	if err != nil {
		return nil, err
	}

	return &pb.TranscribeAudioResp{
		Text:       result.Text,
		MeetingId:  result.MeetingID,
		Confidence: result.Confidence,
	}, nil
}

func (s *Server) GetTranscription(ctx context.Context, req *pb.GetTranscriptionReq) (*pb.GetTranscriptionResp, error) {
	result, err := s.usecase.GetTranscription(ctx, &entity.GetTranscriptionRequest{
		MeetingID: req.MeetingId,
	})
	if err != nil {
		return nil, err
	}

	return &pb.GetTranscriptionResp{
		MeetingId: result.MeetingID,
		FullText:  result.FullText,
		CreatedAt: result.CreatedAt.Unix(),
		UpdatedAt: result.UpdatedAt.Unix(),
	}, nil
}

func (s *Server) SaveTranscription(ctx context.Context, req *pb.SaveTranscriptionReq) (*pb.SaveTranscriptionResp, error) {
	result, err := s.usecase.SaveTranscription(ctx, &entity.SaveTranscriptionRequest{
		MeetingID: req.MeetingId,
		Text:      req.Text,
	})
	if err != nil {
		return nil, err
	}

	return &pb.SaveTranscriptionResp{
		Success:   result.Success,
		MeetingId: result.MeetingID,
	}, nil
}
