package main

import (
	"fmt"
	"log/slog"
	"net/http"
	"os"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/go-chi/cors"
	"github.com/xilidan/backend/gateways/web/handler"
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

	router := chi.NewRouter()
	router.Use(middleware.Logger)
	router.Use(middleware.URLFormat)
	router.Use(cors.Handler(cors.Options{
		AllowedOrigins:   []string{"*"},
		AllowedMethods:   []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowedHeaders:   []string{"Accept", "Authorization", "Content-Type", "X-CSRF-Token"},
		ExposedHeaders:   []string{"Link"},
		AllowCredentials: true,
		MaxAge:           300,
	}))

	chatHandler := handler.NewHandler()

	router.Route("/api/v1", func(apiRouter chi.Router) {
		apiRouter.Route("/auth", func(authRouter chi.Router) {
		})
		apiRouter.Route("/chat", func(chatRouter chi.Router) {
			chatRouter.Post("/generate", chatHandler.GenerateHandler)
		})
	})

	log.Debug("server running", "port", 8080)
	err := http.ListenAndServe(fmt.Sprintf("0.0.0.0:%d", 8080), router)
	if err != nil {
		log.Error("failed to http.ListenAndServe", "error", err)
		return
	}
}
