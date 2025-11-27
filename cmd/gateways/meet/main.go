package main

import (
	"context"
	"log/slog"
	"os"
	"os/signal"
	"syscall"

	config "github.com/xilidan/backend/config/meet"
	"github.com/xilidan/backend/gateways/meet"
	"github.com/xilidan/backend/pkg/logger"
)

func main() {
	log := logger.Default()
	log.Info("initializing meet gateway")
	log.Debug("creating default logger")

	log = logger.New(logger.Config{
		Level:      slog.LevelDebug,
		Output:     os.Stderr,
		AddSource:  true,
		JSONFormat: false,
	})
	log.Info("logger configured",
		slog.String("level", slog.LevelDebug.String()),
		slog.Bool("add_source", true),
		slog.Bool("json_format", false))

	log.Debug("loading configuration")
	cfg := config.MustLoad()
	log.Info("configuration loaded successfully",
		slog.Int("port", cfg.Port),
		slog.String("fireflies_api_key_set", func() string {
			if cfg.FirefliesAPIKey != "" {
				return "true"
			}
			return "false"
		}()),
		slog.String("scrum_url", cfg.ScrumService.Url),
		slog.Int("scrum_port", cfg.ScrumService.Port))

	log.Debug("creating context with logger")
	ctx := logger.WithContext(context.Background(), log)
	log.Debug("context created successfully")

	log.Info("setting up signal handling for graceful shutdown")
	rootCtx, cancel := signal.NotifyContext(ctx, syscall.SIGTERM)
	defer func() {
		log.Info("canceling root context")
		cancel()
	}()
	log.Debug("signal notification context created")

	log.Info("starting meet gateway application")
	if err := run(rootCtx, cfg, log); err != nil {
		log.Error("failed to run()", slog.String("error", err.Error()))
		log.Error("application terminated with error", slog.String("error", err.Error()))
		return
	}
	log.Info("application terminated successfully")
}

func run(ctx context.Context, cfg *config.Config, log *slog.Logger) error {
	log.Info("run function started")
	log.Debug("creating meet server instance",
		slog.Int("port", cfg.Port))
	
	srv, err := meet.New(cfg, log)
	if err != nil {
		log.Error("failed to create server", slog.String("error", err.Error()))
		log.Error("server initialization failed", 
			slog.String("error", err.Error()),
			slog.String("error_type", "server_creation"))
		return err
	}
	log.Info("meet server instance created successfully")
	log.Debug("server object initialized", slog.Any("server", srv))

	log.Info("starting meet server")
	log.Debug("calling server.Start with context")
	err = srv.Start(ctx)
	if err != nil {
		log.Error("server start failed", slog.String("error", err.Error()))
		return err
	}
	log.Info("server started and stopped gracefully")
	return nil
}
