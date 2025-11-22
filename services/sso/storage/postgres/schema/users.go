package schema

import (
	"time"

	"entgo.io/ent"
	"entgo.io/ent/schema/field"
	"github.com/google/uuid"
	"github.com/xilidan/backend/pkg/gen"
)

type User struct {
	ent.Schema
}

func (User) Fields() []ent.Field {
	return []ent.Field{
		field.UUID("id", uuid.UUID{}).
			Default((func() uuid.UUID)(gen.UUID())),
		field.String("email").Unique(),
		field.String("name"),
		field.String("surname").Optional().Nillable(),
		field.String("password_hash").Sensitive(),
		field.Time("created_at").Default(time.Now()),
		field.Time("updated_at").Default(time.Now()),
	}
}
