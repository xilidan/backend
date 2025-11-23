package storage

import (
	"context"
	"fmt"

	"github.com/google/uuid"
	"github.com/xilidan/backend/pkg/logger"
	"github.com/xilidan/backend/services/sso/entity"
	"github.com/xilidan/backend/services/sso/storage/postgres/ent/user"
)

func (s *storage) CreateUser(ctx context.Context, req *entity.RegitserRequest) (*entity.User, error) {
	log := logger.FromContext(ctx)

	userCreate := s.User.Create().
		SetName(req.Name).
		SetNillableSurname(req.Surname).
		SetEmail(req.Email).
		SetPasswordHash(req.Password)

	// Only set position if it's provided (for organization users)
	if req.PositionID != 0 {
		userCreate = userCreate.SetPositionID(req.PositionID)
	}

	entUser, err := userCreate.Save(ctx)
	if err != nil {
		log.Error("failed to create user", "error", err)
		return nil, fmt.Errorf("failed to create user: %w", err)
	}
	log.Debug("created user", "user", entUser)

	return entity.MakeUserEntToEntity(entUser), nil
}

func (s *storage) GetUserByEmail(ctx context.Context, email string) (*entity.User, error) {
	log := logger.FromContext(ctx)
	entUser, err := s.User.Query().
		Where(
			user.Email(email),
		).First(ctx)
	if err != nil {
		log.Error("failed to get user by email", "error", err)
		return nil, fmt.Errorf("failed to get user by email: %w", err)
	}

	log.Debug("user", "user", entUser)

	return entity.MakeUserEntToEntity(entUser), nil
}

func (s *storage) GetUserByID(ctx context.Context, id string) (*entity.User, error) {
	log := logger.FromContext(ctx)
	uuid, err := uuid.Parse(id)
	if err != nil {
		log.Error("failed to genereate uuid", "error", err)
		return nil, fmt.Errorf("failed to generate uuid: %w", err)
	}

	entUser, err := s.User.Query().
		Where(
			user.ID(uuid),
		).First(ctx)
	if err != nil {
		log.Error("failed to get user by id", "error", err)
		return nil, fmt.Errorf("failed to get user by id: %w", err)
	}

	log.Debug("user", "user", entUser)

	return entity.MakeUserEntToEntity(entUser), nil
}
