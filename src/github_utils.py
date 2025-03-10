import json
import os
from typing import List, Optional
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


def get_valid_hunks(diff_content: str) -> List[dict]:
    """Parse diff content with precise line tracking"""
    hunks = []
    current_file = None
    new_line = None
    
    for line in diff_content.split('\n'):
        if line.startswith('diff --git'):
            current_file = line.split(' b/')[1].split()[0]
            new_line = None
        elif line.startswith('@@'):
            try:
                # Extract new file range from hunk header
                new_range = line.split('+')[1].split()[0].split(',')
                new_start = int(new_range[0])
                new_line_count = int(new_range[1]) if len(new_range) > 1 else 1
                new_line = new_start
                hunks.append({
                    'file': current_file,
                    'start': new_start,
                    'end': new_start + new_line_count - 1,
                    'lines': set(range(new_start, new_start + new_line_count))
                })
            except (IndexError, ValueError):
                new_line = None
        elif new_line is not None:
            if line.startswith('+'):
                new_line += 1
            elif line.startswith(' '):
                new_line += 1

    # print(hunks)            
    return hunks

def validate_comment(comment: dict, hunks: List[dict]) -> Optional[dict]:
    """Validate comment against actual diff hunks"""
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
    filtered_comments = []
    
    for comment in comments:
        validated = validate_comment(comment, hunks)
        if validated:
            filtered_comments.append(validated)
        else:
            print(f"Skipping invalid: {comment['path']} {comment['start_line']}-{comment['end_line']}")
    
    valid_comments = []
    for comment in filtered_comments:
        if (comment['start_line'] <= comment['line'] and  # GitHub API requirement
            comment['path'] in [h['file'] for h in hunks]):
            valid_comments.append(comment)
    
    if not valid_comments:
        print("No valid comments after final validation")
        return

    # for a in valid_comments:
    #     print(a)
    try:
        # Create review with valid comments
        review = pr.create_review(
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