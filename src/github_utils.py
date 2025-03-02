import json
import os
import requests
from github import Github

def get_pull_request_diff():
    """Fetch the pull request diff content from GitHub"""
    g = Github(os.getenv('GIT_TOKEN'))

    # Parse GitHub event context
    event_path = os.getenv('GITHUB_EVENT_PATH')
    with open(event_path, 'r') as f:
        event_data = json.load(f)

    repo = g.get_repo(event_data['repository']['full_name'])
    pr_number = event_data['pull_request']['number']
    pull_request = repo.get_pull(pr_number)

    # Get diff content
    diff_url = pull_request.diff_url
    response = requests.get(diff_url)
    return response.text

def post_review_comment(comment):
    """Post a review comment back to the pull request"""
    g = Github(os.getenv('GIT_TOKEN'))

    event_path = os.getenv('GITHUB_EVENT_PATH')
    with open(event_path, 'r') as f:
        event_data = json.load(f)

    repo = g.get_repo(event_data['repository']['full_name'])
    pr_number = event_data['pull_request']['number']
    pull_request = repo.get_pull(pr_number)
    head_sha = event_data['pull_request']['head']['sha']

    #Create review comment
    try:
        # Get the actual Commit object using the SHA
        commit = repo.get_commit(head_sha)

        # Create draft review with correct parameters
        review = pull_request.create_review(
            commit=commit,
            body="AI Code Review Comments",
            event="COMMENT"  # Change to "APPROVE" or "REQUEST_CHANGES" if needed
        )
        
        # Create review comment with correct parameters
        review.create_comment(
            body=comment['body'],
            path=comment['path'],
            line=comment['position']  # Changed from 'position' to 'line'
        )
        
    except Exception as e:
        print(f"Failed to post comment: {str(e)}")
        print(f"Problematic comment data: {comment}")