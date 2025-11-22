package storage

import (
	"context"

	"github.com/xilidan/backend/services/sso/storage/postgres/ent"
)

type storage struct {
	*ent.Client
}

type Storage interface {
	CreateUser(ctx context.Context)
	GetUserByEmail(ctx context.Context, email string)
	GetUserByID(ctx context.Context, id string)
}

func New(client *ent.Client) Storage {
	return &storage{
		Client: client,
	}
}
