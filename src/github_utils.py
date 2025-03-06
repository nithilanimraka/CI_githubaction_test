# github_utils.py (updated)

import os
from typing import Dict
import requests
import json
from github import Github

def get_pull_request_diff():
    """Fetch diff content and PR metadata"""
    g = Github(os.getenv('GITHUB_TOKEN'))
    
    with open(os.getenv('GITHUB_EVENT_PATH'), 'r') as f:
        event_data = json.load(f)
    
    repo = g.get_repo(event_data['repository']['full_name'])
    pr = repo.get_pull(event_data['pull_request']['number'])
    
    return (
        requests.get(pr.diff_url).text,
        pr.head.sha,
        pr
    )
# commit=repo.get_commit(head_sha),

def post_review_comment(comment: Dict, pull_request):
    """Post comment using GitHub API"""
    try:
        pull_request.create_review(
            body=comment['body'],
            commit=comment['commit_id'],
            path=comment['path'],
            event="COMMENT"
        )
    except Exception as e:
        print(f"Failed to post comment: {str(e)}")