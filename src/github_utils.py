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


def get_valid_lines(diff_content):
    """Parse diff to find valid line numbers"""
    valid_lines = {}
    current_file = None
    line_number = None
    
    for line in diff_content.split('\n'):
        if line.startswith('diff --git'):
            current_file = line.split(' b/')[-1]
            valid_lines[current_file] = set()
        elif line.startswith('@@'):
            parts = line.split('+')
            if len(parts) > 1:
                line_number = int(parts[1].split(',')[0])
        elif line.startswith('+'):
            if current_file and line_number:
                valid_lines[current_file].add(line_number)
            line_number += 1
        elif line.startswith(' ') and not line.startswith('+++'):
            line_number += 1
            
    return valid_lines


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

    # Get valid lines from diff
    valid_lines = get_valid_lines(diff_content)
    
    # Prepare filtered comments
    filtered_comments = []
    for comment in comments:
        try:
            file_path = comment['path']
            line_num = comment.get('line', 1)
            
            # Validate against actual diff
            if file_path in valid_lines and line_num in valid_lines[file_path]:
                filtered_comments.append({
                    "path": file_path,
                    "position": line_num,  # GitHub expects 'position' not 'line'
                    "body": comment['body']
                })
            else:
                print(f"Skipping invalid comment - File: {file_path}, Line: {line_num}")
                
        except KeyError as e:
            print(f"Skipping malformed comment: {comment} - Missing key: {e}")

    if not filtered_comments:
        print("No valid comments to post after filtering")
        return

    try:
        # Create review with valid comments
        pull_request.create_review(
            commit=repo.get_commit(head_sha),
            body="AI Code Review Summary",
            comments=filtered_comments,
            event="COMMENT"
        )
        print(f"Successfully posted {len(filtered_comments)} comments")
        
    except Exception as e:
        print(f"Failed to post comments: {str(e)}")
        if hasattr(e, 'data'):
            print(f"Error details: {json.dumps(e.data, indent=2)}")
        print("Problematic comments structure:", json.dumps(filtered_comments[:2], indent=2))