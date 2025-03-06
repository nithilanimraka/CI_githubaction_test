# github_utils.py (updated)

import os
import requests
import json
from github import Github
from typing import Dict

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

def post_review_comment(comment: Dict, pull_request):
    """Post comment using GitHub API with correct parameters"""
    try:
        # Remove 'b/' prefix from path that appears in diff output
        clean_path = comment['path'].lstrip('b/')
        
        pull_request.create_review_comment(
            body=comment['body'],
            path=clean_path,
            position=comment['position'],
            commit_id=pull_request.head.sha  # Use the PR's head SHA directly
        )
    except Exception as e:
        print(f"Failed to post comment: {str(e)}")