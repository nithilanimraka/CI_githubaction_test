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
    """Parse diff to find valid line numbers with proper initialization"""
    valid_lines = {}
    current_file = None
    line_number = None
    
    for line in diff_content.split('\n'):
        # Reset tracking for new files
        if line.startswith('diff --git'):
            current_file = line.split(' b/')[-1].strip()
            valid_lines[current_file] = set()
            line_number = None  # Reset for new file
            continue
            
        # Parse hunk header
        if line.startswith('@@'):
            try:
                # Extract new file line number (after +)
                hunk_header = line.split('+', 1)[1].split(' ', 1)[0]
                line_number = int(hunk_header.split(',')[0])
                valid_lines[current_file].add(line_number)
            except (IndexError, ValueError):
                line_number = None  # Invalid hunk format
            continue
            
        # Only process lines if we have valid line_number
        if line_number is None:
            continue
            
        # Track added lines
        if line.startswith('+'):
            valid_lines[current_file].add(line_number)
            line_number += 1
        # Track context lines (non-diff lines)
        elif line.startswith(' '):
            line_number += 1
            
    return valid_lines


"""
Posting can be done later when logs are correct and accurate. The line numbers are faulty and need to be fixed.
"""


def post_review_comment(comments, diff_content):
    """Post validated review comments to GitHub"""
    g = Github(os.getenv('GIT_TOKEN'))
    
    # Load GitHub event data
    event_path = os.getenv('GITHUB_EVENT_PATH')
    with open(event_path, 'r') as f:
        event_data = json.load(f)

    # Get repository details
    repo = g.get_repo(event_data['repository']['full_name'])
    pr_number = event_data['pull_request']['number']
    pull_request = repo.get_pull(pr_number)
    head_sha = event_data['pull_request']['head']['sha']

    # Get valid lines from diff
    valid_lines = get_valid_lines(diff_content)
    
    # Prepare GitHub-compatible comments
    github_comments = []
    for comment in comments:
        try:
            file_path = comment['path']
            line_num = comment['line']
            body = comment['body']
            
            # Validate against actual diff
            if (file_path in valid_lines and 
                line_num in valid_lines[file_path] and 
                len(body) > 0):
                
                github_comments.append({
                    "path": file_path,
                    "position": line_num,
                    "body": body
                })
                
        except KeyError as e:
            print(f"Skipping invalid comment structure: {e}")
            continue

    if not github_comments:
        print("No valid comments to post after validation")
        return

    try:
        # Create review with valid comments
        review = pull_request.create_review(
            commit=repo.get_commit(head_sha),
            body="AI Code Review Summary",
            comments=github_comments,
            event="COMMENT"
        )
        print(f"Successfully posted {len(github_comments)} comments")
        print(f"Review URL: {review.html_url}")
        
    except Exception as e:
        print(f"Failed to post comments: {str(e)}")
        if hasattr(e, 'data'):
            print(f"GitHub API error details: {json.dumps(e.data, indent=2)}")