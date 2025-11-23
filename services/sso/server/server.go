package server

import (
	"context"

	config "github.com/xilidan/backend/config/sso"
	"github.com/xilidan/backend/services/sso/entity"
	"github.com/xilidan/backend/services/sso/usecase"
	pb "github.com/xilidan/backend/specs/proto/specs/proto/sso"
	"google.golang.org/grpc"
)

type Server struct {
	pb.UnimplementedSsoServiceServer

	cfg     *config.Config
	usecase usecase.Usecase
}

func NewServerOptions(cfg *config.Config, usecase usecase.Usecase) *Server {
	return &Server{
		cfg:     cfg,
		usecase: usecase,
	}
}

func (s *Server) NewServer() (*grpc.Server, error) {
	// TODO: Добавить здесь все options включая OpenTeleметory
	srv := grpc.NewServer()
	pb.RegisterSsoServiceServer(srv, s)

	return srv, nil
}

func (s *Server) Login(ctx context.Context, req *pb.LoginReq) (*pb.LoginResp, error) {
	result, err := s.usecase.Login(ctx, &entity.LoginRequest{
		Email:    req.Email,
		Password: req.Password,
	})
	if err != nil {
		return nil, err
	}

	return &pb.LoginResp{
		Token: result.Token,
	}, nil
}

func (s *Server) Register(ctx context.Context, req *pb.RegisterReq) (*pb.RegisterResp, error) {
	result, err := s.usecase.Register(ctx, &entity.RegitserRequest{
		Name:            req.Name,
		Surname:         req.Surname,
		Email:           req.Email,
		Password:        req.Password,
		PasswordConfirm: req.PasswordConfirm,
	})
	if err != nil {
		return nil, err
	}

	return &pb.RegisterResp{
		Token: result.Token,
	}, nil
}

func (s *Server) GetUser(ctx context.Context, req *pb.GetUserReq) (*pb.GetUserResp, error) {
	result, err := s.usecase.GetUser(ctx, &entity.GetUserRequest{
		ID: req.UserId,
	})
	if err != nil {
		return nil, err
	}

	job := ""
	if result.User.Job != nil {
		job = *result.User.Job
	}

	return &pb.GetUserResp{
		User: &pb.User{
			Id:      result.User.ID,
			Name:    result.User.Name,
			Surname: result.User.Surname,
			Email:   result.User.Email,
			Job:     job,
		},
	}, nil
}

func (s *Server) CreateOrganization(ctx context.Context, req *pb.CreateOrganizationReq) (*pb.CreateOrganizationResp, error) {
	postionsReq := make([]*entity.Position, len(req.Positions))
	for i, positionReq := range req.Positions {
		position := &entity.Position{
			ID:         int(positionReq.Id),
			Name:       positionReq.Name,
			IsReviewer: positionReq.IsReviewer,
		}

		postionsReq[i] = position
	}
	usersReq := make([]*entity.User, len(req.Users))
	for i, uReq := range req.Users {
		var surname *string
		if uReq.Surname != nil {
			surname = uReq.Surname
		}

		usersReq[i] = &entity.User{
			Name:    uReq.Name,
			Surname: surname,
			Email:   uReq.Email,
		}
	}
	result, err := s.usecase.CreateOrganization(ctx, &entity.CreateOrganizationReq{
		Name:      req.Name,
		Positions: postionsReq,
		Users:     usersReq,
	})
	if err != nil {
		return nil, err
	}

	// map positions
	pbPositions := make([]*pb.Position, len(result.Organization.Positions))
	for i, p := range result.Organization.Positions {
		pbPositions[i] = &pb.Position{
			Id:         int64(p.ID),
			Name:       p.Name,
			IsReviewer: p.IsReviewer,
		}
	}

	// map users
	pbUsers := make([]*pb.User, len(result.Organization.Users))
	for i, u := range result.Organization.Users {
		positionId := int64(0)
		if u.Position != nil {
			positionId = int64(u.Position.ID)
		}

		pbUsers[i] = &pb.User{
			Id:         u.ID,
			Name:       u.Name,
			Surname:    u.Surname,
			Email:      u.Email,
			PositionId: positionId,
			Job:        "",
		}
	}

	return &pb.CreateOrganizationResp{
		Organization: &pb.Organization{
			Id:        result.Organization.ID,
			Name:      result.Organization.Name,
			Positions: pbPositions,
			Users:     pbUsers,
		},
	}, nil
}

func (s *Server) GetOrganization(ctx context.Context, req *pb.GetOrganizationReq) (*pb.GetOrganizationResp, error) {
	result, err := s.usecase.GetOrganization(ctx, &entity.GetOrganizationReq{UserID: req.Id})
	if err != nil {
		return nil, err
	}

	// map positions
	pbPositions := make([]*pb.Position, len(result.Organization.Positions))
	for i, p := range result.Organization.Positions {
		pbPositions[i] = &pb.Position{
			Id:         int64(p.ID),
			Name:       p.Name,
			IsReviewer: p.IsReviewer,
		}
	}

	// map users
	pbUsers := make([]*pb.User, len(result.Organization.Users))
	for i, u := range result.Organization.Users {
		positionId := int64(0)
		if u.Position != nil {
			positionId = int64(u.Position.ID)
		}

		pbUsers[i] = &pb.User{
			Id:         u.ID,
			Name:       u.Name,
			Surname:    u.Surname,
			Email:      u.Email,
			PositionId: positionId,
			Job:        "",
		}
	}

	return &pb.GetOrganizationResp{
		Organization: &pb.Organization{
			Id:        result.Organization.ID,
			Name:      result.Organization.Name,
			Positions: pbPositions,
			Users:     pbUsers,
		},
	}, nil
}

func (s *Server) UpdateOrganization(ctx context.Context, req *pb.UpdateOrganizationReq) (*pb.UpdateOrganizationResp, error) {
	// map positions and users into entity.UpdateOrganizationReq
	pos := make([]entity.Position, len(req.Positions))
	for i, p := range req.Positions {
		pos[i] = entity.Position{
			ID:         int(p.Id),
			Name:       p.Name,
			IsReviewer: p.IsReviewer,
		}
	}

	users := make([]entity.User, len(req.Users))
	for i, u := range req.Users {
		var surname *string
		if u.Surname != nil {
			surname = u.Surname
		}
		users[i] = entity.User{
			Name:    u.Name,
			Surname: surname,
			Email:   u.Email,
		}
	}

	result, err := s.usecase.UpdateOrganization(ctx, &entity.UpdateOrganizationReq{
		ID:        req.Id,
		Name:      req.Name,
		Positions: pos,
		Users:     users,
	})
	if err != nil {
		return nil, err
	}

	// map response organization
	org := result.Organization

	pbPositions := make([]*pb.Position, len(org.Positions))
	for i, p := range org.Positions {
		pbPositions[i] = &pb.Position{
			Id:         int64(p.ID),
			Name:       p.Name,
			IsReviewer: p.IsReviewer,
		}
	}

	pbUsers := make([]*pb.User, len(org.Users))
	for i, u := range org.Users {
		posID := int64(0)
		if u.Position != nil {
			posID = int64(u.Position.ID)
		}
		pbUsers[i] = &pb.User{
			Id:         u.ID,
			Name:       u.Name,
			Surname:    u.Surname,
			Email:      u.Email,
			PositionId: posID,
			Job:        "",
		}
	}

	return &pb.UpdateOrganizationResp{
		Organization: &pb.Organization{
			Id:        org.ID,
			Name:      org.Name,
			Positions: pbPositions,
			Users:     pbUsers,
		},
	}, nil
}
