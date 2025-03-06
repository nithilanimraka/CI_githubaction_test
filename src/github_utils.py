# github_utils.py (updated)

import os
import github
import requests
import json
from github import Github
from typing import Dict

def get_pull_request_diff():
    """Fetch diff content and PR metadata"""
    g = Github(os.getenv('GIT_TOKEN'))
    
    with open(os.getenv('GITHUB_EVENT_PATH'), 'r') as f:
        event_data = json.load(f)
    
    repo = g.get_repo(event_data['repository']['full_name'])
    pr = repo.get_pull(event_data['pull_request']['number'])
    
    return (
        requests.get(pr.diff_url).text,
        pr.head.sha,
        pr
    )

def post_review_comment(comment: Dict, pull_request, head_commit_sha):
    """Post comment using GitHub API with correct parameters"""
    try:
        # GitHub API requires line number instead of position
        pull_request.create_review(
            commit=github.Commit.Commit(pull_request.repository, head_commit_sha),
            body="🤖 AI Code Review",
            event="COMMENT",
            comments=[{
                'path': comment['path'].lstrip('b/'),
                'body': comment['body'],
                'line': comment['position']
            }]
        )
    except Exception as e:
        print(f"Failed to post comment: {str(e)}")