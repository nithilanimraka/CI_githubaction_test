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

def post_review_comment(comments):
    """Post all review comments at once"""
    g = Github(os.getenv('GIT_TOKEN'))

    event_path = os.getenv('GITHUB_EVENT_PATH')
    with open(event_path, 'r') as f:
        event_data = json.load(f)

    repo = g.get_repo(event_data['repository']['full_name'])
    pr_number = event_data['pull_request']['number']
    pull_request = repo.get_pull(pr_number)
    head_sha = event_data['pull_request']['head']['sha']

    # Prepare review comments in GitHub's required format
    github_comments = []
    for comment in comments:
        try:
            github_comments.append({
                "path": comment['path'],
                "body": comment['body'],
                "line": comment.get('line', 1)  # Use 'line' instead of 'position'
            })
        except KeyError as e:
            print(f"Skipping invalid comment: {comment}")
            continue

    try:
        # Create review with all comments at once
        pull_request.create_review(
            commit=repo.get_commit(head_sha),
            body="AI Code Review Summary",
            comments=github_comments,
            event="COMMENT"
        )
    except Exception as e:
        print(f"Failed to post comments: {str(e)}")
        print(f"Problematic comments: {comments}")