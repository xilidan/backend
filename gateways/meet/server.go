package meet

import (
	"context"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	config "github.com/xilidan/backend/config/meet"
	firefliesClient "github.com/xilidan/backend/gateways/meet/clients/recall"
	scrumClient "github.com/xilidan/backend/gateways/meet/clients/scrum"
	"github.com/xilidan/backend/gateways/meet/handler"
	"github.com/xilidan/backend/gateways/meet/monitor"
)

type Server struct {
	cfg             *config.Config
	log             *slog.Logger
	firefliesClient *firefliesClient.Client
	scrumClient     *scrumClient.Client
	monitor         *monitor.MeetingMonitor
	handler         *handler.Handler
}

func New(cfg *config.Config, log *slog.Logger) (*Server, error) {
	log.Info("creating new meet server")
	log.Debug("server config", 
		slog.Int("port", cfg.Port),
		slog.String("fireflies_api_key_set", fmt.Sprintf("%t", cfg.FirefliesAPIKey != "")),
		slog.String("scrum_service_url", cfg.ScrumService.Url),
		slog.Int("scrum_service_port", cfg.ScrumService.Port))

	log.Debug("creating fireflies client")
	fireflies := firefliesClient.New(cfg.FirefliesAPIKey)
	log.Info("fireflies client created successfully")

	log.Debug("creating scrum master HTTP client")
	scrum := scrumClient.New(&cfg.ScrumService)
	log.Info("scrum client created successfully")

	log.Debug("creating meeting monitor")
	mon := monitor.New(fireflies, scrum, log)
	log.Info("meeting monitor created successfully")

	log.Debug("creating handler")
	h := handler.New(mon, log)
	log.Info("handler created successfully")

	log.Info("meet server instance created successfully")
	return &Server{
		cfg:             cfg,
		log:             log,
		firefliesClient: fireflies,
		scrumClient:     scrum,
		monitor:         mon,
		handler:         h,
	}, nil
}

func (s *Server) Start(ctx context.Context) error {
	s.log.Info("starting meet server")
	s.log.Debug("creating HTTP multiplexer")
	mux := http.NewServeMux()
	s.log.Debug("registering routes")
	s.handler.RegisterRoutes(mux)
	s.log.Info("routes registered successfully")

	addr := fmt.Sprintf(":%d", s.cfg.Port)
	s.log.Debug("creating HTTP server",
		slog.String("addr", addr),
		slog.Duration("read_timeout", 15*time.Second),
		slog.Duration("write_timeout", 15*time.Second),
		slog.Duration("idle_timeout", 60*time.Second))
	srv := &http.Server{
		Addr:         addr,
		Handler:      mux,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}
	s.log.Info("HTTP server configured")

	s.log.Debug("setting up shutdown signal handling")
	shutdown := make(chan os.Signal, 1)
	signal.Notify(shutdown, os.Interrupt, syscall.SIGTERM)
	s.log.Debug("shutdown signal handler configured")

	s.log.Debug("creating server error channel")
	serverErrors := make(chan error, 1)

	go func() {
		s.log.Info("meet gateway started", slog.String("address", srv.Addr))
		s.log.Debug("calling ListenAndServe")
		err := srv.ListenAndServe()
		if err != nil {
			s.log.Error("ListenAndServe error", slog.String("error", err.Error()))
		}
		serverErrors <- err
	}()

	s.log.Info("entering main server loop")
	select {
	case err := <-serverErrors:
		s.log.Error("server error received", slog.String("error", err.Error()))
		return fmt.Errorf("server error: %w", err)
	case sig := <-shutdown:
		s.log.Info("start shutdown", slog.String("signal", sig.String()))
		s.log.Debug("shutdown signal received, beginning graceful shutdown")
		
		s.log.Debug("creating shutdown timeout context", slog.Duration("timeout", 10*time.Second))
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()

		s.log.Info("shutting down HTTP server gracefully")
		if err := srv.Shutdown(ctx); err != nil {
			s.log.Error("graceful shutdown failed", slog.String("error", err.Error()))
			s.log.Warn("forcing server close")
			srv.Close()
			return fmt.Errorf("failed to gracefully shutdown server: %w", err)
		}
		s.log.Info("server shutdown completed successfully")
	case <-ctx.Done():
		s.log.Info("closing server due to context cancellation")
		s.log.Debug("context done signal received")
		
		s.log.Debug("creating shutdown timeout context", slog.Duration("timeout", 10*time.Second))
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()

		s.log.Info("shutting down HTTP server gracefully")
		if err := srv.Shutdown(ctx); err != nil {
			s.log.Error("graceful shutdown failed", slog.String("error", err.Error()))
			s.log.Warn("forcing server close")
			srv.Close()
			return fmt.Errorf("failed to gracefully shutdown server: %w", err)
		}
		s.log.Info("server shutdown completed successfully")
	}

	s.log.Info("server stopped cleanly")
	return nil
}
