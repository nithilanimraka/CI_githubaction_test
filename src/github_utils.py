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
    #print(response.text)
    return response.text


def get_valid_hunks(diff_content):
    """Parse diff to track valid line ranges"""
    hunks = []
    current_hunk = None
    
    for line in diff_content.split('\n'):
        if line.startswith('diff --git'):
            current_hunk = {
                'file': line.split(' b/')[1].split()[0],
                'start': None,
                'end': None,
                'lines': []
            }
            hunks.append(current_hunk)
        elif line.startswith('@@'):
            try:
                new_part = line.split('+')[1].split()[0]
                start = int(new_part.split(',')[0])
                count = int(new_part.split(',')[1])
                current_hunk['start'] = start
                current_hunk['end'] = start + count - 1
            except (IndexError, ValueError):
                current_hunk = None
        elif current_hunk and line.startswith(('+', ' ')):
            current_hunk['lines'].append(line)
    
    return hunks


def validate_comment(comment, hunks):
    """Validate line range within a single hunk"""
    for hunk in hunks:
        if (hunk['file'] == comment['path'] and
            comment['start_line'] >= hunk['start'] and
            comment['end_line'] <= hunk['end']):
            
            return {
                'path': comment['path'],
                'start_line': comment['start_line'],
                'line': comment['end_line'],
                'body': comment['body'],
                'start_side': 'RIGHT',
                'side': 'RIGHT'
            }
    return None



def post_review_comment(comments, diff_content):
    """Post validated review comments to GitHub"""
    g = Github(os.getenv('GIT_TOKEN'))

    # Load GitHub event data
    event_path = os.getenv('GITHUB_EVENT_PATH')
    with open(event_path, 'r') as f:
        event_data = json.load(f)

    # Get repository and PR details
    repo = g.get_repo(event_data['repository']['full_name'])
    pr_number = event_data['pull_request']['number']
    pull_request = repo.get_pull(pr_number)
    head_sha = event_data['pull_request']['head']['sha']

    # Parse hunks from diff
    hunks = get_valid_hunks(diff_content)
    
    # Validate comments against hunks
    valid_comments = []
    for comment in comments:
        validated = validate_comment(comment, hunks)
        if validated:
            valid_comments.append(validated)
        else:
            print(f"Skipping invalid range: {comment['path']} {comment['start_line']}-{comment['end_line']}")

    if not valid_comments:
        print("No valid comments to post")
        return

    # Post comments using GitHub's API
    try:
        pull_request.create_review(
            commit=repo.get_commit(head_sha),
            body="AI Code Review Summary",
            comments=valid_comments,
            event="COMMENT"
        )
        print(f"Posted {len(valid_comments)} comments")
    except Exception as e:
        print(f"Failed to post comments: {str(e)}")