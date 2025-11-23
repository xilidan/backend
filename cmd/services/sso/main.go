package main

import (
	"context"
	"fmt"
	"log/slog"
	"net"
	"os"
	"os/signal"
	"syscall"

	_ "github.com/lib/pq"
	config "github.com/xilidan/backend/config/sso"
	"github.com/xilidan/backend/pkg/logger"
	"github.com/xilidan/backend/services/sso/server"
	"github.com/xilidan/backend/services/sso/storage"
	"github.com/xilidan/backend/services/sso/storage/postgres/ent"
	"github.com/xilidan/backend/services/sso/usecase"
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
	entPsqlConnect := fmt.Sprintf("host=%s port=%d user=%s dbname=%s password=%s sslmode=%s",
		cfg.Database.Host,
		cfg.Database.Port,
		cfg.Database.User,
		cfg.Database.Name,
		cfg.Database.Password,
		cfg.Database.SSLMode,
	)
	client, err := ent.Open("postgres", entPsqlConnect)
	if err != nil {
		panic(err)
	}
	defer client.Close()

	if err := client.Schema.Create(context.Background()); err != nil {
		panic(err)
	}

	stg := storage.New(client)
	usc := usecase.New(cfg, stg)

	srv := server.NewServerOptions(cfg, usc)
	server, err := srv.NewServer()
	if err != nil {
		log.Error("failed to create grpc server", slog.String("error", err.Error()))
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
		serverErrors <- server.Serve(grpcListener)
	}()
	log.Info("grpc service started", slog.String("address", address))

	select {
	case err := <-serverErrors:
		log.Info("grpc server has closed")
		return fmt.Errorf("grpc server has closed: %w", err)
	case sig := <-shutdown:
		log.Info("start shutdown", slog.String("signal", sig.String()))
		server.GracefulStop()
	case <-ctx.Done():
		log.Info("closing grpc server due to context cancellation")
		server.GracefulStop()

		return nil
	}

	return nil
}
