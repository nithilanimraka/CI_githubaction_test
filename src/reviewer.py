import os
from github_utils import get_pull_request_diff, post_review_comment
from llm_utils import analyze_code_changes

class AICodeReviewer:
    def __init__(self):
        self.github_token = os.getenv('GITHUB_TOKEN')

    def review_pull_request(self):
        diff_content, head_commit_sha, pr = get_pull_request_diff()
        review_comments = analyze_code_changes(diff_content)
        
        # Post all comments in a single review
        if review_comments:
            try:
                pr.create_review(
                    commit=pr.get_commits().reversed[0],
                    body="🤖 AI Code Review Report",
                    event="COMMENT",
                    comments=[{
                        'path': c['path'],
                        'body': c['body'],
                        'line': c['position']
                    } for c in review_comments]
                )
                print(f"Successfully posted {len(review_comments)} comments")
            except Exception as e:
                print(f"Failed to post review: {str(e)}")