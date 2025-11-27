from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class CommentSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class CommentType(str, Enum):
    STYLE_ISSUE = "style_issue"
    CODE_SMELL = "code_smell"
    BUG = "bug"
    PERFORMANCE = "performance"
    SECURITY = "security"
    BEST_PRACTICE = "best_practice"
    FUNCTIONAL = "functional"


class ReviewRecommendation(str, Enum):
    MERGE = "merge"
    NEEDS_FIXES = "needs_fixes"
    REJECT = "reject"


@dataclass
class MergeRequest:
    id: int
    project_id: int
    iid: int
    title: str
    description: str
    source_branch: str
    target_branch: str
    author_id: int
    state: str
    created_at: datetime
    updated_at: datetime
    web_url: Optional[str] = None
    author_username: Optional[str] = None
    author_email: Optional[str] = None


@dataclass
class FileDiff:
    old_path: str
    new_path: str
    diff: str
    new_file: bool = False
    deleted_file: bool = False
    renamed_file: bool = False


@dataclass
class Comment:
    file_path: str
    line: int
    content: str
    severity: CommentSeverity
    type: CommentType
    
    def to_markdown(self) -> str:
        severity_emoji = {
            CommentSeverity.INFO: "ℹ️",
            CommentSeverity.WARNING: "⚠️",
            CommentSeverity.CRITICAL: "🚨"
        }
        emoji = severity_emoji.get(self.severity, "💡")
        return f"{emoji} **{self.type.value.replace('_', ' ').title()}**: {self.content}"


@dataclass
class ReviewResult:
    mr_id: int
    project_id: int
    comments: list[Comment]
    summary: str
    recommendation: ReviewRecommendation
    reviewed_at: datetime = field(default_factory=datetime.utcnow)
    quality_score: int = 0  # 0-100 score
    
    def to_summary_markdown(self) -> str:
        lines = [
            "## 🤖 AI Code Review Summary",
            "",
            f"**Recommendation**: {self.recommendation.value.replace('_', ' ').title()}",
            f"**Quality Score**: {self.quality_score}/100",
            "",
            self.summary,
            "",
            f"**Total Issues Found**: {len(self.comments)}",
        ]
        
        if self.comments:
            critical = [c for c in self.comments if c.severity == CommentSeverity.CRITICAL]
            warnings = [c for c in self.comments if c.severity == CommentSeverity.WARNING]
            info = [c for c in self.comments if c.severity == CommentSeverity.INFO]
            
            lines.extend([
                "",
                f"- 🚨 Critical: {len(critical)}",
                f"- ⚠️ Warnings: {len(warnings)}",
                f"- ℹ️ Info: {len(info)}",
            ])
        
        return "\n".join(lines)


@dataclass
class UserRating:
    email: str
    rating: int = 500
    review_count: int = 0
    last_updated: datetime = field(default_factory=datetime.utcnow)
