package main

import (
	"context"
	"log/slog"
	"os"

	"github.com/xilidan/backend/pkg/logger"
)

func main() {
	log := logger.Default()

	log = logger.New(logger.Config{
		Level:      slog.LevelDebug,
		Output:     os.Stderr,
		AddSource:  true,
		JSONFormat: false,
	})

	ctx := logger.WithContext(context.Background(), log)
}
