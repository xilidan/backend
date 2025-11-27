import logging
from datetime import datetime
from typing import Any

import gitlab
from gitlab.v4.objects import ProjectMergeRequest

from domain import MergeRequest, FileDiff, Comment, CommentSeverity


logger = logging.getLogger(__name__)


class GitLabClientImpl:
    
    def __init__(self, url: str, private_token: str):
        self.gl = gitlab.Gitlab(url, private_token=private_token)
        self.gl.auth()
        logger.info(f"GitLab client initialized for {url}")
    
    async def get_merge_request(self, project_id: int, mr_iid: int) -> MergeRequest:
        logger.debug(f"Fetching MR {project_id}/{mr_iid}")
        
        project = self.gl.projects.get(project_id)
        mr = project.mergerequests.get(mr_iid)
        author_email = mr.author.get('email') or mr.author.get('public_email') or f"{author_username}@gitlab.local"

        
        return MergeRequest(
            id=mr.id,
            project_id=mr.project_id,
            iid=mr.iid,
            title=mr.title,
            description=mr.description or "",
            source_branch=mr.source_branch,
            target_branch=mr.target_branch,
            author_id=mr.author['id'],
            state=mr.state,
            created_at=datetime.fromisoformat(mr.created_at.replace('Z', '+00:00')),
            updated_at=datetime.fromisoformat(mr.updated_at.replace('Z', '+00:00')),
            web_url=mr.web_url,
            author_username=mr.author.get('username'),
            # GitLab API might not expose email directly depending on visibility
            # Fallback to constructing one or using a placeholder
            author_email=author_email,
        )
    
    async def get_merge_request_diff(
        self, project_id: int, mr_iid: int
    ) -> list[FileDiff]:
        logger.debug(f"Fetching diff for MR {project_id}/{mr_iid}")
        
        project = self.gl.projects.get(project_id)
        mr = project.mergerequests.get(mr_iid)
        changes = mr.changes()
        
        file_diffs = []
        for change in changes.get('changes', []):
            file_diff = FileDiff(
                old_path=change.get('old_path', ''),
                new_path=change.get('new_path', ''),
                diff=change.get('diff', ''),
                new_file=change.get('new_file', False),
                deleted_file=change.get('deleted_file', False),
                renamed_file=change.get('renamed_file', False),
            )
            file_diffs.append(file_diff)
        
        logger.info(f"Retrieved {len(file_diffs)} file diffs")
        return file_diffs
    
    async def post_comment(
        self, project_id: int, mr_iid: int, comment: Comment
    ) -> None:
        logger.debug(f"Posting comment to MR {project_id}/{mr_iid}")
        
        project = self.gl.projects.get(project_id)
        mr = project.mergerequests.get(mr_iid)
        
        # Create a discussion (threaded comment) on the specific line
        try:
            # Try to create inline comment
            discussion_data = {
                'body': comment.to_markdown(),
                'position': {
                    'position_type': 'text',
                    'new_path': comment.file_path,
                    'new_line': comment.line,
                    'base_sha': mr.diff_refs['base_sha'],
                    'head_sha': mr.diff_refs['head_sha'],
                    'start_sha': mr.diff_refs['start_sha'],
                }
            }
            mr.discussions.create(discussion_data)
            logger.debug(f"Posted inline comment: {comment.file_path}:{comment.line}")
        except Exception as e:
            logger.warning(f"Failed to post inline comment, posting as note: {e}")
            note_text = f"**{comment.file_path}:{comment.line}**\n\n{comment.to_markdown()}"
            mr.notes.create({'body': note_text})
    
    async def update_labels(
        self, project_id: int, mr_iid: int, labels: list[str]
    ) -> None:
        logger.debug(f"Updating labels for MR {project_id}/{mr_iid}: {labels}")
        
        project = self.gl.projects.get(project_id)
        mr = project.mergerequests.get(mr_iid)
        
        # Get existing labels and merge with new ones
        existing_labels = mr.labels or []
        all_labels = list(set(existing_labels + labels))
        
        mr.labels = all_labels
        mr.save()
        
        logger.info(f"Updated labels: {all_labels}")
    
    async def post_summary_note(
        self, project_id: int, mr_iid: int, content: str
    ) -> None:
        logger.debug(f"Posting summary note to MR {project_id}/{mr_iid}")
        
        project = self.gl.projects.get(project_id)
        mr = project.mergerequests.get(mr_iid)
        
        mr.notes.create({'body': content})
        logger.info("Summary note posted")
