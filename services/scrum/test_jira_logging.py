"""
Test script to verify Jira API integration with detailed logging.

This script will show you exactly what's being sent to Jira and what responses you're getting.
"""

import asyncio
import sys
sys.path.append('.')

from service import JiraScrumMasterService

async def test_jira_api():
    """Test the Jira API endpoints with detailed logging"""
    
    service = JiraScrumMasterService()
    
    # Replace with your actual token
    token = "your_auth_token_here"
    
    print("\n" + "🔧 "*40)
    print("JIRA API INTEGRATION TEST")
    print("🔧 "*40 + "\n")
    
    try:
        # Test 0: Fetch Organization Info (to verify new logging)
        print("\n📋 TEST 0: Fetching Organization Info")
        print("-" * 80)
        await service.get_organization_info(token)

        # Test 1: Create an Epic
        print("\n📋 TEST 1: Creating an Epic")
        print("-" * 80)
        epic_result = await service.create_epic(
            summary="Test Epic - User Authentication",
            token=token
        )
        
        # Test 2: Create a Task with assignee
        print("\n📋 TEST 2: Creating a Task with Assignee")
        print("-" * 80)
        task_result = await service.create_task(
            summary="Test Task - Design Login Page",
            assignee_email="john.doe@example.com",
            token=token
        )
        
        # Use the task key from the response for the subtask
        task_key = task_result.get('key', 'SCRUM-15')
        
        # Test 3: Create a Subtask
        print("\n📋 TEST 3: Creating a Subtask")
        print("-" * 80)
        subtask_result = await service.create_subtask(
            summary="Test Subtask - Create Login Form Component",
            parent_key=task_key,
            token=token
        )
        
        # Summary
        print("\n" + "="*80)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY!")
        print("="*80)
        print(f"\nCreated Items:")
        print(f"  1. Epic: {epic_result.get('key', 'N/A')}")
        print(f"  2. Task: {task_result.get('key', 'N/A')}")
        print(f"  3. Subtask: {subtask_result.get('key', 'N/A')}")
        print("\nYou can verify these in Jira at:")
        print(f"  Epic: {epic_result.get('self', 'N/A')}")
        print(f"  Task: {task_result.get('self', 'N/A')}")
        print(f"  Subtask: {subtask_result.get('self', 'N/A')}")
        print("\n" + "="*80 + "\n")
        
    except ValueError as e:
        print("\n" + "="*80)
        print("❌ TEST FAILED")
        print("="*80)
        print(f"Error: {e}")
        print("\nPlease check:")
        print("  1. Your authentication token is correct")
        print("  2. The Jira API URL is accessible")
        print("  3. You have permissions to create issues in Jira")
        print("="*80 + "\n")
        return False
    
    return True

if __name__ == "__main__":
    print("\n⚠️  IMPORTANT: Update the 'token' variable with your actual auth token!")
    print("You can find your token from the organization API or your auth service.\n")
    
    input("Press Enter to continue with the test (or Ctrl+C to cancel)...")
    
    success = asyncio.run(test_jira_api())
    
    sys.exit(0 if success else 1)
