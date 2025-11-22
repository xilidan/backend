package schema

import (
	"time"

	"entgo.io/ent"
	"entgo.io/ent/schema/edge"
	"entgo.io/ent/schema/field"
)

type Position struct {
	ent.Schema
}

func (Position) Fields() []ent.Field {
	return []ent.Field{
		field.String("name"),
		field.Bool("is_reviewer"),
		field.Time("created_at").Default(time.Now()),
		field.Time("updated_at").Default(time.Now()),
	}
}

func (Position) Edges() []ent.Edge {
	return []ent.Edge{
		edge.From("users", User.Type).
			Ref("position"),
	}
}
