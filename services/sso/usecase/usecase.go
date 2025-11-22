package usecase

import (
	"context"

	"github.com/google/uuid"
	config "github.com/xilidan/backend/config/sso"
	"github.com/xilidan/backend/pkg/jwt"
	"github.com/xilidan/backend/services/sso/entity"
	"github.com/xilidan/backend/services/sso/storage"
	"golang.org/x/crypto/bcrypt"
)

type usecase struct {
	cfg     *config.Config
	Storage storage.Storage
}

type Usecase interface {
	Login(ctx context.Context, req *entity.LoginRequest) (*entity.LoginResponse, error)
	Register(ctx context.Context, req *entity.RegitserRequest) (*entity.RegisterResponse, error)
	GetUser(ctx context.Context, req *entity.GetUserRequest) (*entity.GetUserResponse, error)
	CreateOrganization(ctx context.Context, req *entity.CreateOrganizationReq) (*entity.CreateOrganizationResp, error)
	UpdateOrganization(ctx context.Context, req *entity.UpdateOrganizationReq) (*entity.UpdateOrgnaizationResp, error)
	GetOrganization(ctx context.Context, req *entity.GetOrganizationReq) (*entity.GetOrganizationResp, error)
}

func New(cfg *config.Config, storage storage.Storage) Usecase {
	return &usecase{
		cfg:     cfg,
		Storage: storage,
	}
}

func (u *usecase) Login(ctx context.Context, req *entity.LoginRequest) (*entity.LoginResponse, error) {
	user, err := u.Storage.GetUserByEmail(ctx, req.Email)
	if err != nil {
		return nil, err
	}

	if err := bcrypt.CompareHashAndPassword([]byte(user.Password), []byte(req.Password)); err != nil {
		return nil, err
	}

	token, err := jwt.Generate(ctx, user.ID, u.cfg.JWTSecret)
	if err != nil {
		return nil, err
	}

	return &entity.LoginResponse{
		Token: token,
	}, nil
}

func (u *usecase) Register(ctx context.Context, req *entity.RegitserRequest) (*entity.RegisterResponse, error) {
	passwordHash, err := bcrypt.GenerateFromPassword([]byte(req.Password), bcrypt.DefaultCost)
	if err != nil {
		return nil, err
	}

	req.Password = string(passwordHash)

	user, err := u.Storage.CreateUser(ctx, req)
	if err != nil {
		return nil, err
	}

	token, err := jwt.Generate(ctx, user.ID, u.cfg.JWTSecret)
	if err != nil {
		return nil, err
	}

	return &entity.RegisterResponse{
		Token: token,
	}, nil
}

func (u *usecase) GetUser(ctx context.Context, req *entity.GetUserRequest) (*entity.GetUserResponse, error) {
	user, err := u.Storage.GetUserByID(ctx, req.ID)
	if err != nil {
		return nil, err
	}

	return &entity.GetUserResponse{
		User: user,
	}, nil
}

func (u *usecase) CreateOrganization(ctx context.Context, req *entity.CreateOrganizationReq) (*entity.CreateOrganizationResp, error) {
	positions := make([]*entity.Position, len(req.Positions))
	for i, position := range req.Positions {
		entPosition, err := u.Storage.CreatePosition(ctx, position)
		if err != nil {
			return nil, err
		}
		positions[i] = entPosition
	}

	userIDs := make([]uuid.UUID, len(req.Users))
	for i, user := range req.Users {
		entUser, err := u.Storage.CreateUser(ctx, &entity.RegitserRequest{
			Name:       user.Name,
			Surname:    user.Surname,
			Email:      user.Email,
			PositionID: positions[i].ID,
			Password:   "",
		})
		if err != nil {
			return nil, err
		}

		userUUID, err := uuid.Parse(entUser.ID)
		userIDs[i] = userUUID
	}

	organization, err := u.Storage.CreateOrganization(
		ctx,
		&entity.Organization{
			Name: req.Name,
		},
		userIDs,
	)
	if err != nil {
		return nil, err
	}

	return &entity.CreateOrganizationResp{
		Organization: organization,
	}, nil
}

func (u *usecase) UpdateOrganization(ctx context.Context, req *entity.UpdateOrganizationReq) (*entity.UpdateOrgnaizationResp, error) {
	return nil, nil
}

func (u *usecase) GetOrganization(ctx context.Context, req *entity.GetOrganizationReq) (*entity.GetOrganizationResp, error) {
	organization, err := u.Storage.GetOrganization(ctx, req.UserID)
	if err != nil {
		return nil, err
	}

	return &entity.GetOrganizationResp{
		Organization: organization,
	}, nil
}
