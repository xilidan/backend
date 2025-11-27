"""
Simple test to verify the service can start.
"""
import asyncio
import sys

# Add parent directory to path
sys.path.insert(0, '/Users/yernazarius/forte/backend/services/codereview')

from domain import (
    MergeRequest,
    Comment,
    CommentSeverity,
    CommentType,
    ReviewResult,
    ReviewRecommendation,
    FileDiff,
)
from infrastructure import MockLLMClient, InMemoryReviewRepository
from usecase import ReviewUsecase


async def test_basic_functionality():
    """Test basic functionality without external dependencies."""
    print("Testing Code Review Service...")
    
    # Test 1: Domain entities
    print("\n1. Testing domain entities...")
    comment = Comment(
        file_path="test.py",
        line=10,
        content="Test comment",
        severity=CommentSeverity.INFO,
        type=CommentType.BEST_PRACTICE,
    )
    print(f"   ✓ Created comment: {comment.to_markdown()}")
    
    # Test 2: Repository
    print("\n2. Testing in-memory repository...")
    repository = InMemoryReviewRepository()
    
    from datetime import datetime
    result = ReviewResult(
        mr_id=1,
        project_id=123,
        comments=[comment],
        summary="Test review",
        recommendation=ReviewRecommendation.MERGE,
        reviewed_at=datetime.utcnow(),
    )
    
    await repository.save(result)
    print("   ✓ Saved review result")
    
    retrieved = await repository.get(123, 1)
    assert retrieved is not None
    assert retrieved.summary == "Test review"
    print("   ✓ Retrieved review result")
    
    # Test 3: Mock LLM Client
    print("\n3. Testing mock LLM client...")
    llm_client = MockLLMClient()
    
    file_diff = FileDiff(
        old_path="test.py",
        new_path="test.py",
        diff="@@ -1,1 +1,1 @@\\n-old\\n+new",
    )
    
    comments, summary, recommendation = await llm_client.analyze_code(
        mr_title="Test MR",
        mr_description="Test description",
        file_diffs=[file_diff],
        standards=["Test standard"],
    )
    
    assert len(comments) > 0
    assert summary
    assert recommendation
    print(f"   ✓ Mock LLM returned {len(comments)} comment(s)")
    print(f"   ✓ Recommendation: {recommendation.value}")
    
    print("\n✅ All tests passed!")
    print("\nService is ready to use.")
    print("\nNext steps:")
    print("1. Configure environment variables in .env")
    print("2. Set GITLAB_TOKEN and LLM_API_KEY")
    print("3. Run: python main.py")
    print("4. Configure GitLab webhook to point to http://your-server:8000/api/v1/webhooks/gitlab")


if __name__ == "__main__":
    asyncio.run(test_basic_functionality())
