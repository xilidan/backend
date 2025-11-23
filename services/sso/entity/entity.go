package entity

import (
	"time"

	"github.com/xilidan/backend/services/sso/storage/postgres/ent"
)

type (
	User struct {
		ID        string
		Name      string
		Surname   *string
		Email     string
		Password  string
		Job       *string
		Position  *Position
		CreatedAt time.Time
		UpdatedAt time.Time
	}

	Organization struct {
		ID        string
		Name      string
		Users     []*User
		Positions []*Position
	}

	Position struct {
		ID         int
		Name       string
		IsReviewer bool
	}
)

func MakeUserEntToEntity(user *ent.User) *User {
	var position *Position
	if user.Edges.Position != nil {
		position = MakePositionEntToEntity(user.Edges.Position)
	}

	return &User{
		ID:        user.ID.String(),
		Name:      user.Name,
		Surname:   user.Surname,
		Email:     user.Email,
		Password:  user.PasswordHash,
		Job:       user.Job,
		Position:  position,
		CreatedAt: user.CreatedAt,
		UpdatedAt: user.UpdatedAt,
	}
}

func MakePositionEntToEntity(position *ent.Position) *Position {
	if position == nil {
		return nil
	}
	return &Position{
		ID:         position.ID,
		Name:       position.Name,
		IsReviewer: position.IsReviewer,
	}
}

func MakeUsersArrayEntToEntity(users []*ent.User) []*User {
	usersEntity := make([]*User, len(users))
	for i, user := range users {
		userEntity := MakeUserEntToEntity(user)
		usersEntity[i] = userEntity
	}

	return usersEntity
}

func MakePositionsArrayEntToEntity(positions []*ent.Position) []*Position {
	postionsEntity := make([]*Position, len(positions))
	for i, position := range positions {
		postionEntity := MakePositionEntToEntity(position)
		postionsEntity[i] = postionEntity
	}

	return postionsEntity
}

func MakeOrganizationEntToEntity(organization *ent.Organization) *Organization {
	users := []*User{}
	if organization.Edges.Users != nil {
		for _, orgUser := range organization.Edges.Users {
			if orgUser.Edges.User != nil {
				users = append(users, MakeUserEntToEntity(orgUser.Edges.User))
			}
		}
	}

	return &Organization{
		ID:        organization.ID.String(),
		Name:      organization.Name,
		Positions: []*Position{},
		Users:     users,
	}
}
