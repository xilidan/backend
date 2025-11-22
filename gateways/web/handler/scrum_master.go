package handler

import (
	"encoding/json"
	"net/http"
	"time"
)

type (
	GenerateRequest struct {
		Prompt string `json:"prompt"`
	}

	GenerateResponse struct {
		Content string `json:"content"`
		IsEnd   bool   `json:"is_end"`
	}
)

var (
	mockMessage = `# 📌 AI Team Lead — Jira Specification Output
Below is the generated analysis for the provided input:
> **Raw Input:**
> %s
---
## 🧩 Task Breakdown (Example)
- **Epic:** AI Team Lead Automation System
- **Tasks:**
  - Create Jira ticket generator based on TS
  - Build meeting transcription and action extraction
  - Implement MR analyzer with inline comments
  - Add deadline reminder service
---
## 🔗 Useful Links
- Jira REST API: https://developer.atlassian.com/cloud/jira/platform/rest/v3/
- GitLab MR API: https://docs.gitlab.com/ee/api/merge_requests.html
- Markdown Cheat Sheet: https://www.markdownguide.org/cheat-sheet/
---
## 🧪 Code Block Example
` + "```" + `ts
// Jira issue payload example
const issue = {
  fields: {
    summary: "Implement authentication flow",
    project: { key: "PROJ" },
    issuetype: { name: "Task" }
  }
};
` + "```" + `
---
## 📊 Table Example
| Feature               | Status | Notes                          |
|-----------------------|--------|--------------------------------|
| Jira creation         | ✅     | Working as expected            |
| Meeting transcription | ⚠️     | Needs noise filtering          |
| MR analysis           | ✅     | Stable, accurate               |
| Deadline reminders    | 🟡     | Requires timezone handling     |
---
## 💬 Final Recommendation
` + "```" + `md
### 🔍 Merge Request Summary
Status: needs fixes
- Missing null-checks
- Tests incomplete
- API mismatch with TS
` + "```" + `
---
If all sections above render properly, your **<ReactMarkdown> integration is fully working**.`
)

func (h *handler) GenerateHandler(w http.ResponseWriter, r *http.Request) {
	var req GenerateRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Transfer-Encoding", "chunked")
	w.WriteHeader(http.StatusOK)

	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "Streaming unsupported", http.StatusInternalServerError)
		return
	}

	chunkSize := 25
	for i := 0; i < len(mockMessage); i += chunkSize {
		end := i + chunkSize
		if end > len(mockMessage) {
			end = len(mockMessage)
		}

		chunk := GenerateResponse{
			Content: mockMessage[i:end],
			IsEnd:   false,
		}

		_ = json.NewEncoder(w).Encode(chunk)
		flusher.Flush()

		time.Sleep(300 * time.Millisecond)
	}

	final := GenerateResponse{
		Content: "",
		IsEnd:   true,
	}

	_ = json.NewEncoder(w).Encode(final)
	flusher.Flush()
}
