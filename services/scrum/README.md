# AI Scrum Master Service

## Quick Start

### Build and Run with Docker Compose

```bash
# Build and start all services (including scrum-ai-service)
docker-compose up --build

# Run only the scrum service
docker-compose up --build scrum-ai-service

# Run in detached mode
docker-compose up -d

# Stop the service
docker-compose down

# View logs
docker-compose logs -f scrum-ai-service
```

### Environment Variables

Make sure you have a `.env` file in `services/scrum/` with:

```env
AZURE_OPENAI_ENDPOINT=https://oina-east-us-1.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4.1-mini
API_VERSION=2024-02-15-preview
BACKEND_API_URL=https://api.azed.kz/api/v1
```

### Access the Service

- **API Documentation (Swagger UI)**: http://localhost:8000/docs
- **API Endpoint**: http://localhost:8000/decompose

### Testing

```bash
# Upload a file and get task decomposition
curl -X POST "http://localhost:8000/decompose" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@path/to/your/document.docx"
```

### Health Check

```bash
curl http://localhost:8000/docs
```
