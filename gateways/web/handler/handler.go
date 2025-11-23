package handler

import (
	"net/http"
	"os"
	"path/filepath"

	config "github.com/xilidan/backend/config/web"
	"github.com/xilidan/backend/gateways/web/clients/sso"
)

type handler struct {
	SsoClient *sso.Client
	cfg       *config.Config
}

type Handler interface {
	GenerateHandler(w http.ResponseWriter, r *http.Request)
	LoginHandler(w http.ResponseWriter, r *http.Request)
	RegisterHandler(w http.ResponseWriter, r *http.Request)
	GetUserHandler(w http.ResponseWriter, r *http.Request)
	CreateOrganizationHandler(w http.ResponseWriter, r *http.Request)
	UpdateOrganizationHandler(w http.ResponseWriter, r *http.Request)
	GetOrganizationHandler(w http.ResponseWriter, r *http.Request)
	SwaggerHandler(w http.ResponseWriter, r *http.Request)
	SwaggerUIHandler(w http.ResponseWriter, r *http.Request)
}

func NewHandler(ssoClient *sso.Client, cfg *config.Config) Handler {
	return &handler{
		SsoClient: ssoClient,
		cfg:       cfg,
	}
}

// SwaggerHandler serves the OpenAPI spec YAML file
func (h *handler) SwaggerHandler(w http.ResponseWriter, r *http.Request) {
	// Try multiple possible paths for the spec file
	possiblePaths := []string{
		"/app/specs/openapi/web/api.yaml",
		filepath.Join("specs", "openapi", "web", "api.yaml"),
		"./specs/openapi/web/api.yaml",
	}

	var data []byte
	var err error
	var successPath string

	for _, specPath := range possiblePaths {
		data, err = os.ReadFile(specPath)
		if err == nil {
			successPath = specPath
			break
		}
	}

	if err != nil {
		http.Error(w, "OpenAPI spec not found: "+err.Error(), http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/x-yaml")
	w.Header().Set("X-Spec-Path", successPath)
	w.WriteHeader(http.StatusOK)
	w.Write(data)
} // SwaggerUIHandler serves a simple Swagger UI HTML page
func (h *handler) SwaggerUIHandler(w http.ResponseWriter, r *http.Request) {
	html := `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Xilidan API Documentation</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5.10.0/swagger-ui.css">
    <style>
        body {
            margin: 0;
            padding: 0;
        }
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5.10.0/swagger-ui-bundle.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@5.10.0/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {
            window.ui = SwaggerUIBundle({
                url: "/api.yaml",
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout"
            });
        };
    </script>
</body>
</html>`

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.WriteHeader(http.StatusOK)
	w.Write([]byte(html))
}
