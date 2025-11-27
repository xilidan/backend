package storage

import (
	"context"

	"github.com/google/uuid"
	"github.com/xilidan/backend/services/sso/entity"
	"github.com/xilidan/backend/services/sso/storage/postgres/ent/organizationusers"
	"github.com/xilidan/backend/services/sso/storage/postgres/ent/user"
)

func (s *storage) CreateOrganization(ctx context.Context, req *entity.Organization, userIDs []uuid.UUID, creatorID uuid.UUID) (*entity.Organization, error) {
	// Remove users from any existing organizations first
	// This is necessary because of the Unique() constraint on organization_users.user edge
	for _, userID := range userIDs {
		_, err := s.OrganizationUsers.Delete().
			Where(organizationusers.HasUserWith(user.ID(userID))).
			Exec(ctx)
		if err != nil {
			// Continue even if deletion fails (user might not be in any org)
			// This is not critical for the operation
		}
	}

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

	organizationEntity, err := s.OrganizationUsers.
		Query().
		Where(organizationusers.HasUserWith(user.ID(userUUID))).
		QueryOrganization().
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
