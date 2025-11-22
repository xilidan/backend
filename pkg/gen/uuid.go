package gen

import (
	"github.com/google/uuid"
)

type UUIDGenerator func() uuid.UUID

func UUID() UUIDGenerator {
	return func() uuid.UUID {
		return uuid.Must(uuid.NewUUID())
	}
}

func (g UUIDGenerator) Next() uuid.UUID {
	if g == nil {
		return uuid.Nil
	}

	return g()
}
