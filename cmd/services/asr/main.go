package main

import (
	"context"
	"fmt"
	"log/slog"
	"net"
	"os"
	"os/signal"
	"syscall"

	config "github.com/xilidan/backend/config/asr"
	"github.com/xilidan/backend/pkg/logger"
	"github.com/xilidan/backend/services/asr/server"
	"github.com/xilidan/backend/services/asr/storage"
	"github.com/xilidan/backend/services/asr/usecase"
)

func main() {
	log := logger.Default()

	log = logger.New(logger.Config{
		Level:      slog.LevelDebug,
		Output:     os.Stderr,
		AddSource:  true,
		JSONFormat: false,
	})

	cfg := config.MustLoad()

	ctx := logger.WithContext(context.Background(), log)

	rootCtx, cancel := signal.NotifyContext(ctx, syscall.SIGTERM)
	defer cancel()

	if err := run(rootCtx, cfg, log); err != nil {
		log.Error("failed to run()", slog.String("error", err.Error()))
		return
	}
}

func run(ctx context.Context, cfg *config.Config, log *slog.Logger) error {
	stg := storage.New()
	usc := usecase.New(stg)

	srv := server.NewServerOptions(usc)
	grpcServer, err := srv.NewServer()
	if err != nil {
		log.Error("failed to create grpc server", slog.String("error", err.Error()))
		return err
	}

	shutdown := make(chan os.Signal, 1)
	signal.Notify(shutdown, os.Interrupt, syscall.SIGTERM)

	serverErrors := make(chan error, 1)

	address := fmt.Sprintf(":%d", cfg.Port)
	grpcListener, err := net.Listen("tcp", address)
	if err != nil {
		log.Error("failed to listen on grpc port", slog.String("error", err.Error()))
		return fmt.Errorf("failed to listen on grpc port: %w", err)
	}

	go func() {
		serverErrors <- grpcServer.Serve(grpcListener)
	}()
	log.Info("asr grpc service started", slog.String("address", address))

	select {
	case err := <-serverErrors:
		log.Info("grpc server has closed")
		return fmt.Errorf("grpc server has closed: %w", err)
	case sig := <-shutdown:
		log.Info("start shutdown", slog.String("signal", sig.String()))
		grpcServer.GracefulStop()
	case <-ctx.Done():
		log.Info("closing grpc server due to context cancellation")
		grpcServer.GracefulStop()
		return nil
	}

	return nil
}
