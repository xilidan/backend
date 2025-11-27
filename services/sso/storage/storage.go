package storage

import (
	"context"

	"github.com/google/uuid"
	"github.com/xilidan/backend/services/sso/entity"
	"github.com/xilidan/backend/services/sso/storage/postgres/ent"
)

type storage struct {
	*ent.Client
}

type Storage interface {
	CreateUser(ctx context.Context, req *entity.RegitserRequest) (*entity.User, error)
	GetUserByEmail(ctx context.Context, email string) (*entity.User, error)
	GetUserByID(ctx context.Context, id string) (*entity.User, error)

	CreateOrganization(ctx context.Context, req *entity.Organization, userIDs []uuid.UUID, creatorID uuid.UUID) (*entity.Organization, error)
	GetOrganization(ctx context.Context, id string) (*entity.Organization, error)
	UpdateOrganization(ctx context.Context, req *entity.Organization, userIDs []uuid.UUID) (*entity.Organization, error)

	CreatePosition(ctx context.Context, req *entity.Position) (*entity.Position, error)
}

func New(client *ent.Client) Storage {
	return &storage{
		Client: client,
	}
}
