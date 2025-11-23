package main

import (
	"fmt"
	"log/slog"
	"net/http"
	"os"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/go-chi/cors"
	config "github.com/xilidan/backend/config/web"
	"github.com/xilidan/backend/gateways/web/clients/sso"
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

	cfg := config.MustLoad()

	router := chi.NewRouter()
	router.Use(middleware.Logger)
	// router.Use(middleware.URLFormat) // Commented out - might interfere with .yaml extension
	router.Use(cors.Handler(cors.Options{
		AllowedOrigins:   []string{"*"},
		AllowedMethods:   []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowedHeaders:   []string{"Accept", "Authorization", "Content-Type", "X-CSRF-Token"},
		ExposedHeaders:   []string{"Link"},
		AllowCredentials: true,
		MaxAge:           300,
	}))

	ssoClient, err := sso.New(&cfg.SsoService)
	if err != nil {
		panic(err)
	}

	chatHandler := handler.NewHandler(ssoClient, cfg)

	// Test endpoint
	router.Get("/test", func(w http.ResponseWriter, r *http.Request) {
		w.Write([]byte("test works!"))
	})

	// Swagger documentation routes - register BEFORE api/v1 routes
	router.Get("/api.yaml", chatHandler.SwaggerHandler)
	router.Get("/swagger/api.yaml", chatHandler.SwaggerHandler)
	router.Get("/swagger", chatHandler.SwaggerUIHandler)

	router.Route("/api/v1", func(apiRouter chi.Router) {
		apiRouter.Route("/auth", func(authRouter chi.Router) {
			authRouter.Post("/login", chatHandler.LoginHandler)
			authRouter.Post("/register", chatHandler.RegisterHandler)
			authRouter.Get("/profile", chatHandler.GetUserHandler)
		})
		apiRouter.Route("/organization", func(organizationRouter chi.Router) {
			organizationRouter.Post("/", chatHandler.CreateOrganizationHandler)
			organizationRouter.Put("/", chatHandler.UpdateOrganizationHandler)
			organizationRouter.Get("/", chatHandler.GetOrganizationHandler)
		})
		apiRouter.Route("/chat", func(chatRouter chi.Router) {
			chatRouter.Post("/generate", chatHandler.GenerateHandler)
		})
	})

	log.Debug("server running", "port", 8080)
	err = http.ListenAndServe(fmt.Sprintf("0.0.0.0:%d", 8080), router)
	if err != nil {
		log.Error("failed to http.ListenAndServe", "error", err)
		return
	}
}
