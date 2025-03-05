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


def get_valid_lines(diff_content):
    """Parse diff to find valid line numbers in the new file version"""
    valid_lines = {}
    current_file = None
    new_file_line = None  # Tracks line numbers in the new file
    hunk_lines = 0  # Tracks number of lines processed in current hunk

    for line in diff_content.split('\n'):
        # Start of new file diff
        if line.startswith('diff --git'):
            current_file = line.split(' b/')[-1].split()[0]
            valid_lines[current_file] = set()
            new_file_line = None
            hunk_lines = 0
            continue

        # Hunk header - format: @@ -old_start,old_lines +new_start,new_lines @@
        if line.startswith('@@'):
            try:
                # Extract new file line information
                new_part = line.split('+')[1].split(' ', 1)[0]
                new_start = int(new_part.split(',')[0])
                new_file_line = new_start
                hunk_lines = 0
                valid_lines[current_file].add(new_file_line)
            except (IndexError, ValueError):
                new_file_line = None
            continue

        if new_file_line is None:
            continue  # Skip lines before valid hunk header

        # Track line types
        if line.startswith('+'):
            # Added line - valid for commenting
            valid_lines[current_file].add(new_file_line)
            new_file_line += 1
            hunk_lines += 1
        elif line.startswith(' '):
            # Context line - valid for commenting
            valid_lines[current_file].add(new_file_line)
            new_file_line += 1
            hunk_lines += 1
        elif line.startswith('-'):
            # Deleted line - only exists in old file, don't increment new line
            hunk_lines += 1
        else:
            # Other diff control lines
            continue

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

        # Ensure we're dealing with a dictionary
        if not isinstance(comment, dict):
            print(f"Skipping invalid comment type: {type(comment)}")
            continue

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