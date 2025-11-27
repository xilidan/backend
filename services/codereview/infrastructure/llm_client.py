import json
import logging
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI, AsyncAzureOpenAI
from anthropic import AsyncAnthropic

from domain import Comment, CommentSeverity, CommentType, FileDiff, ReviewRecommendation


logger = logging.getLogger(__name__)


class LLMClientImpl:
    
    def __init__(
        self,
        provider: str = "openai",
        api_key: str | None = None,
        model: str | None = None,
        azure_config_path: str | None = None,
    ):
        self.provider = provider.lower()
        self.api_key = api_key
        self.is_azure = False
        
        # Load Azure configuration if provider is azure_openai
        if self.provider == "azure_openai" or azure_config_path:
            self.is_azure = True
            azure_config = self._load_azure_config(azure_config_path or "instance.json")
            
            self.model = azure_config.get("deployment", model or "gpt-4")
            self.client = AsyncAzureOpenAI(
                azure_endpoint=azure_config["url"],
                api_key=azure_config["key"],
                api_version=azure_config.get("api_version", "2024-02-15-preview"),
            )
            logger.info(
                f"Azure OpenAI client initialized with deployment: {self.model} "
                f"at {azure_config['url']}"
            )
        elif model:
            self.model = model
            self._init_standard_client()
        elif self.provider == "openai":
            self.model = "gpt-4-turbo-preview"
            self._init_standard_client()
        elif self.provider == "anthropic":
            self.model = "claude-3-5-sonnet-20241022"
            self._init_standard_client()
        else:
            self.model = "gpt-4-turbo-preview"
            self._init_standard_client()
        
        if not self.is_azure:
            logger.info(f"LLM client initialized: {self.provider} with model {self.model}")
    
    def _load_azure_config(self, config_path: str) -> dict:
        """Load Azure OpenAI configuration from instance.json."""
        try:
            # Try relative to service directory first
            path = Path(config_path)
            if not path.is_absolute():
                path = Path(__file__).parent.parent / config_path
            
            with open(path, "r") as f:
                configs = json.load(f)
                # Take the first instance
                if isinstance(configs, list) and len(configs) > 0:
                    return configs[0]
                return configs
        except Exception as e:
            logger.error(f"Failed to load Azure config from {config_path}: {e}")
            raise ValueError(f"Could not load Azure configuration: {e}")
    
    def _init_standard_client(self):
        """Initialize standard OpenAI or Anthropic client."""
        if self.provider == "openai":
            self.client = AsyncOpenAI(api_key=self.api_key)
        elif self.provider == "anthropic":
            self.client = AsyncAnthropic(api_key=self.api_key)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    async def analyze_code(
        self,
        mr_title: str,
        mr_description: str,
        file_diffs: list[FileDiff],
        standards: list[str],
    ) -> tuple[list[Comment], str, ReviewRecommendation, int]:
        logger.info(f"Analyzing {len(file_diffs)} files with {self.provider}")
        
        prompt = self._build_analysis_prompt(
            mr_title, mr_description, file_diffs, standards
        )
        
        if self.provider == "openai" or self.provider == "azure_openai":
            response_text = await self._call_openai(prompt)
        elif self.provider == "anthropic":
            response_text = await self._call_anthropic(prompt)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
        
        comments, summary, recommendation, score = self._parse_response(response_text)
        
        logger.info(
            f"Analysis complete: {len(comments)} comments, "
            f"recommendation: {recommendation.value}, score: {score}"
        )
        
        return comments, summary, recommendation, score
    
    def _build_analysis_prompt(
        self,
        mr_title: str,
        mr_description: str,
        file_diffs: list[FileDiff],
        standards: list[str],
    ) -> str:
        diffs_text = "\n\n".join([
            f"### File: {diff.new_path}\n```diff\n{diff.diff}\n```"
            for diff in file_diffs
        ])
        
        standards_text = "\n".join([f"- {std}" for std in standards])
        
        prompt = f"""You are a senior code reviewer. Analyze the following merge request and provide detailed feedback.

**Merge Request Title:** {mr_title}

**Description:**
{mr_description}

**Development Standards to Check:**
{standards_text}

**Code Changes:**
{diffs_text}

**Instructions:**
1. Review the code changes carefully
2. Identify issues related to:
   - Style violations
   - Code smells and anti-patterns
   - Potential bugs
   - Security vulnerabilities
   - Performance issues
   - Best practice violations
   - Functional correctness

3. Rate the code quality on a scale of 0 to 100 (0=terrible, 100=perfect).

4. Provide your response in the following JSON format:
{{
  "comments": [
    {{
      "file_path": "path/to/file.py",
      "line": 42,
      "content": "Clear explanation of the issue",
      "severity": "critical|warning|info",
      "type": "bug|security|performance|style_issue|code_smell|best_practice|functional"
    }}
  ],
  "summary": "Overall summary of the review (2-3 sentences)",
  "recommendation": "merge|needs_fixes|reject",
  "quality_score": 85
}}

Be constructive, specific, and helpful in your feedback."""
        
        return prompt
    
    async def _call_openai(self, prompt: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert code reviewer. Always respond in valid JSON format.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content
    
    async def _call_anthropic(self, prompt: str) -> str:
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=0.3,
            messages=[
                {"role": "user", "content": prompt}
            ],
        )
        return response.content[0].text

    def _parse_response(
        self, response_text: str
    ) -> tuple[list[Comment], str, ReviewRecommendation, int]:
        try:
            # Try to extract JSON if it's wrapped in markdown
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()
            elif "```" in response_text:
                start = response_text.find("```") + 3
                end = response_text.find("```", start)
                response_text = response_text[start:end].strip()
            
            data = json.loads(response_text)
            
            # Parse comments
            comments = []
            for c in data.get("comments", []):
                try:
                    comment = Comment(
                        file_path=c["file_path"],
                        line=int(c["line"]),
                        content=c["content"],
                        severity=CommentSeverity(c["severity"]),
                        type=CommentType(c["type"]),
                    )
                    comments.append(comment)
                except Exception as e:
                    logger.warning(f"Failed to parse comment: {e}")
                    continue
            
            summary = data.get("summary", "No summary provided")
            recommendation = ReviewRecommendation(
                data.get("recommendation", "needs_fixes")
            )
            score = int(data.get("quality_score", 50))
            
            return comments, summary, recommendation, score
            
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.debug(f"Response text: {response_text}")
            
            # Return default values
            return (
                [],
                "Failed to analyze code due to parsing error.",
                ReviewRecommendation.NEEDS_FIXES,
                0,
            )


class MockLLMClient:
    
    async def analyze_code(
        self,
        mr_title: str,
        mr_description: str,
        file_diffs: list[FileDiff],
        standards: list[str],
    ) -> tuple[list[Comment], str, ReviewRecommendation]:
        logger.info("Using mock LLM client")
        
        comments = [
            Comment(
                file_path=file_diffs[0].new_path if file_diffs else "test.py",
                line=10,
                content="This is a mock comment for testing purposes.",
                severity=CommentSeverity.INFO,
                type=CommentType.BEST_PRACTICE,
            )
        ]
        
        summary = "Mock analysis completed. This is a test review."
        recommendation = ReviewRecommendation.MERGE
        
        return comments, summary, recommendation
