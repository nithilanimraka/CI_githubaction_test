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
    """Parse diff to find valid hunk positions"""
    hunks = []
    current_hunk = None
    current_file = None
    
    for line in diff_content.split('\n'):
        if line.startswith('diff --git'):
            # New file section
            current_file = line.split(' b/')[1].split()[0]
        elif line.startswith('@@'):
            # Hunk header format: @@ -old_start,old_lines +new_start,new_lines @@
            parts = line.split(' ')
            new_part = parts[2].split(',')
            new_start = int(new_part[0][1:])
            hunk_length = int(new_part[1])
            
            current_hunk = {
                'file': current_file,
                'new_start': new_start,
                'new_end': new_start + hunk_length - 1,
                'lines': []
            }
            hunks.append(current_hunk)
        elif current_hunk and line.startswith(('+', ' ')):
            # Track valid lines in hunk (additions and context)
            current_hunk['lines'].append({
                'content': line,
                'new_line': current_hunk['new_start'] + len(current_hunk['lines'])
            })
    
    return hunks


def validate_comment(comment, hunks):
    """Validate comment against actual diff hunks"""
    for hunk in hunks:
        if hunk['file'] == comment['path']:
            for line in hunk['lines']:
                if line['new_line'] == comment['line']:
                    return {
                        'path': comment['path'],
                        'position': hunk['lines'].index(line) + 1,  # GitHub's 1-based hunk position
                        'body': comment['body']
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
            print(f"Skipping invalid comment - File: {comment['path']}, Line: {comment['line']}")

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
    except Exception as e:
        print(f"Failed to post comments: {str(e)}")