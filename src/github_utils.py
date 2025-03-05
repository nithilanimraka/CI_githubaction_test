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
    """Parse diff to track valid line ranges per hunk"""
    hunks = []
    current_file = None
    current_hunk = None
    new_line = None

    for line in diff_content.split('\n'):
        if line.startswith('diff --git'):
            current_file = line.split(' b/')[1].split()[0]
        elif line.startswith('@@'):
            parts = line.split('+')
            if len(parts) > 1:
                new_part = parts[1].split()[0].split(',')
                try:
                    new_start = int(new_part[0])
                    new_count = int(new_part[1]) if len(new_part) > 1 else 1
                    new_line = new_start
                    current_hunk = {
                        'file': current_file,
                        'start': new_start,
                        'end': new_start + new_count - 1,
                        'lines': set()
                    }
                    hunks.append(current_hunk)
                except ValueError:
                    current_hunk = None
        elif current_hunk and new_line is not None:
            if line.startswith('+'):
                current_hunk['lines'].add(new_line)
                new_line += 1
            elif line.startswith(' '):
                current_hunk['lines'].add(new_line)
                new_line += 1

    return hunks

def validate_comment(comment, hunks):
    """Validate comment stays within a single valid hunk"""
    for hunk in hunks:
        if hunk['file'] == comment['path']:
            # Check if both lines exist in the same hunk
            start_ok = comment['start_line'] in hunk['lines']
            end_ok = comment['end_line'] in hunk['lines']
            
            if start_ok and end_ok:
                return {
                    'path': comment['path'],
                    'start_line': comment['start_line'],
                    'line': comment['end_line'],
                    'body': comment['body'],
                    'start_side': 'RIGHT',
                    'side': 'RIGHT'
                }
    print(f"Invalid range: {comment['path']} {comment['start_line']}-{comment['end_line']}")
    return None



def post_review_comment(comments, diff_content):
    g = Github(os.getenv('GIT_TOKEN'))
    event_path = os.getenv('GITHUB_EVENT_PATH')
    
    with open(event_path, 'r') as f:
        event_data = json.load(f)
    
    repo = g.get_repo(event_data['repository']['full_name'])
    pr = repo.get_pull(event_data['pull_request']['number'])
    head_sha = event_data['pull_request']['head']['sha']
    
    hunks = get_valid_hunks(diff_content)
    valid_comments = []
    
    for comment in comments:
        validated = validate_comment(comment, hunks)
        if validated:
            valid_comments.append(validated)
        else:
            print(f"Skipping invalid: {comment['path']} {comment['start_line']}-{comment['end_line']}")
    
    if valid_comments:
        try:
            pr.create_review(
                commit=repo.get_commit(head_sha),
                body="AI Code Review Summary",
                comments=valid_comments,
                event="COMMENT"
            )
            print(f"Successfully posted {len(valid_comments)} comments")
        except Exception as e:
            print(f"Failed to post comments: {str(e)}")
            if hasattr(e, 'data'):
                print("Error details:", json.dumps(e.data, indent=2))
    else:
        print("No valid comments to post")