import os
from github_utils import get_pull_request_diff, post_review_comment
from llm_utils import analyze_code_changes

class AICodeReviewer:
    def __init__(self):
        self.github_token = os.getenv('GITHUB_TOKEN')

    def review_pull_request(self):
        diff_content, head_commit_sha, pr = get_pull_request_diff()
        review_comments = analyze_code_changes(diff_content, head_commit_sha)
        
        for comment in review_comments:
            post_review_comment(comment, pr)
            print(f"Posted comment for {comment['path']} line {comment['position']}")

if __name__ == '__main__':
    reviewer = AICodeReviewer()
    reviewer.review_pull_request()