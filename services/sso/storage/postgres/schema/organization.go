package schema

import (
	"time"

	"entgo.io/ent"
	"entgo.io/ent/schema/edge"
	"entgo.io/ent/schema/field"
	"github.com/google/uuid"
	"github.com/xilidan/backend/pkg/gen"
)

type Organization struct {
	ent.Schema
}

func (Organization) Fields() []ent.Field {
	return []ent.Field{
		field.UUID("id", uuid.UUID{}).
			Default((func() uuid.UUID)(gen.UUID())),
		field.String("name"),
		field.UUID("creator_id", uuid.UUID{}),
		field.Time("created_at").Default(time.Now()),
		field.Time("updated_at").Default(time.Now()),
	}
}

func (Organization) Edges() []ent.Edge {
	return []ent.Edge{
		edge.To("users", User.Type),
	}
}
