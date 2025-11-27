package schema

import (
	"time"

	"entgo.io/ent"
	"entgo.io/ent/schema/edge"
	"entgo.io/ent/schema/field"
	"github.com/google/uuid"
	"github.com/xilidan/backend/pkg/gen"
)

type OrganizationUsers struct {
	ent.Schema
}

func (OrganizationUsers) Fields() []ent.Field {
	return []ent.Field{
		field.UUID("id", uuid.UUID{}).
			Default((func() uuid.UUID)(gen.UUID())),
		field.Time("created_at").Default(time.Now()),
		field.Time("updated_at").Default(time.Now()),
	}
}

func (OrganizationUsers) Edges() []ent.Edge {
	return []ent.Edge{
		edge.From("user", User.Type).
			Ref("organizations").
			Unique().
			Required(),
		edge.From("organization", Organization.Type).
			Ref("users").
			Unique().
			Required(),
	}
}
