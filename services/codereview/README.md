# Code Review Service

AI-powered code review assistant for GitLab Merge Requests.

## Features

- **Automated Code Analysis**: Analyzes merge request diffs using AI (OpenAI/Anthropic)
- **Intelligent Comments**: Posts inline comments with severity levels and categorization
- **Smart Recommendations**: Provides merge/needs-fixes/reject recommendations
- **Label Management**: Automatically updates MR labels based on review results
- **GitLab Integration**: Seamless integration via webhooks
- **Flexible Storage**: Supports in-memory and Redis storage

## Architecture

```
services/codereview/
├── domain/              # Domain entities and interfaces
│   ├── entities.py     # MergeRequest, Comment, ReviewResult
│   └── interfaces.py   # GitLabClient, LLMClient, ReviewRepository
├── usecase/            # Business logic
│   └── review_usecase.py
├── infrastructure/     # External integrations
│   ├── gitlab_client.py
│   ├── llm_client.py
│   └── repository.py
├── delivery/           # HTTP handlers
│   └── http_handler.py
├── config.py           # Configuration
├── main.py            # Application entry point
└── requirements.txt   # Dependencies
```

## Installation

1. Install dependencies:
```bash
cd services/codereview
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
cp env.example .env
# Edit .env with your GitLab token and LLM API key
```

## Configuration

See `env.example` for all available configuration options:

- **GitLab**: Set `GITLAB_URL` and `GITLAB_TOKEN`
- **LLM Provider**: Choose `openai` or `anthropic` and set `LLM_API_KEY`
- **Storage**: Use `memory` (default) or `redis`
- **Mock Mode**: Set `USE_MOCK_LLM=true` for testing without API calls

## Running the Service

```bash
# Development mode
python main.py

# Or with uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The service will be available at `http://localhost:8000`

## API Endpoints

### Webhook
- `POST /api/v1/webhooks/gitlab` - GitLab webhook endpoint

### Reviews
- `GET /api/v1/reviews/{project_id}/{mr_iid}` - Get review result
- `POST /api/v1/reviews/{project_id}/{mr_iid}/trigger` - Manually trigger review

### Health
- `GET /api/v1/health` - Health check
- `GET /` - Service info

## GitLab Webhook Setup

1. Go to your GitLab project → Settings → Webhooks
2. Add webhook URL: `http://your-server:8000/api/v1/webhooks/gitlab`
3. Select trigger: **Merge request events**
4. Save webhook

## Development Standards

The service checks code against these standards (configurable):
- Follow PEP 8 style guide
- Write clear and concise comments
- Ensure proper error handling
- Avoid code duplication
- Write unit tests for new functionality
- Use type hints
- Follow SOLID principles
- Ensure code is secure and follows best practices

## Example Review Flow

1. Developer creates/updates MR in GitLab
2. GitLab sends webhook to Code Review Service
3. Service fetches MR details and diff
4. Service sends code to LLM for analysis
5. LLM returns comments, summary, and recommendation
6. Service posts comments inline in GitLab
7. Service posts summary note
8. Service updates MR labels (e.g., `ready-for-merge`, `needs-review`)

## Comment Types

- **Style Issue**: Code style violations
- **Code Smell**: Anti-patterns and design issues
- **Bug**: Potential bugs
- **Security**: Security vulnerabilities
- **Performance**: Performance concerns
- **Best Practice**: Best practice violations
- **Functional**: Functional correctness issues

## Comment Severities

- 🚨 **Critical**: Must be fixed
- ⚠️ **Warning**: Should be reviewed
- ℹ️ **Info**: Informational

## Testing

Run with mock LLM client:
```bash
USE_MOCK_LLM=true python main.py
```

Test webhook endpoint:
```bash
curl -X POST http://localhost:8000/api/v1/webhooks/gitlab \
  -H "Content-Type: application/json" \
  -d @test_webhook.json
```

## License

MIT
