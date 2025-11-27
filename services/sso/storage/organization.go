package storage

import (
	"context"

	"github.com/google/uuid"
	"github.com/xilidan/backend/services/sso/entity"
	"github.com/xilidan/backend/services/sso/storage/postgres/ent/organization"
	"github.com/xilidan/backend/services/sso/storage/postgres/ent/position"
	"github.com/xilidan/backend/services/sso/storage/postgres/ent/user"
)

func (s *storage) GetPositions(ctx context.Context, organizationID string) ([]*entity.Position, error) {
	orgUUID, err := uuid.Parse(organizationID)
	if err != nil {
		return nil, err
	}

	positions, err := s.Position.Query().
		Where(position.HasUsersWith(user.HasOrganizationsWith(organization.ID(orgUUID)))).
		All(ctx)
	if err != nil {
		return nil, err
	}

	return entity.MakePositionsArrayEntToEntity(positions), nil
}

func (s *storage) CreateOrganization(ctx context.Context, req *entity.Organization, userIDs []uuid.UUID, creatorID uuid.UUID) (*entity.Organization, error) {
	organization, err := s.Organization.Create().
		SetName(req.Name).
		SetCreatorID(creatorID).
		AddUserIDs(userIDs...).
		Save(ctx)
	if err != nil {
		return nil, err
	}

	return entity.MakeOrganizationEntToEntity(organization), nil
}

func (s *storage) GetOrganization(ctx context.Context, userID string) (*entity.Organization, error) {
	userUUID, err := uuid.Parse(userID)
	if err != nil {
		return nil, err
	}

	organizationEntity, err := s.Organization.
		Query().
		Where(organization.HasUsersWith(user.ID(userUUID))).
		WithUsers().
		First(ctx)
	if err != nil {
		return nil, err
	}

	return entity.MakeOrganizationEntToEntity(organizationEntity), nil
}

func (s *storage) UpdateOrganization(ctx context.Context, req *entity.Organization, userIDs []uuid.UUID) (*entity.Organization, error) {
	organizationUUID, err := uuid.Parse(req.ID)
	if err != nil {
		return nil, err
	}

	organization, err := s.Organization.UpdateOneID(organizationUUID).
		SetName(req.Name).
		ClearUsers().AddUserIDs(userIDs...).
		Save(ctx)

	return entity.MakeOrganizationEntToEntity(organization), nil
}

func (s *storage) CreatePosition(ctx context.Context, req *entity.Position) (*entity.Position, error) {
	position, err := s.Position.Create().
		SetName(req.Name).
		SetIsReviewer(req.IsReviewer).
		Save(ctx)
	if err != nil {
		return nil, err
	}

	return entity.MakePositionEntToEntity(position), nil
}
