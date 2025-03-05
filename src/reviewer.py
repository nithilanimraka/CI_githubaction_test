import os
from github_utils import get_pull_request_diff, post_review_comment
from llm_utils import analyze_code_changes

class AICodeReviewer:
    def __init__(self):
        self.openai_api_key = os.getenv('GEMINI_API_KEY')
        self.github_token = os.getenv('GIT_TOKEN')

    def review_pull_request(self):
        try:
            diff_content = get_pull_request_diff()
            if not diff_content:
                print("No diff content available")
                return

            review_comments = analyze_code_changes(diff_content)
            
            if not review_comments:
                print("No valid comments generated")
                return
                
            print("Valid comments to post:")
            for idx, comment in enumerate(review_comments, 1):
                print(f"Comment {idx}: {comment['path']} {comment['start_line']}-{comment['end_line']}")
                
            post_review_comment(review_comments, diff_content)
            
        except Exception as e:
            print(f"Review failed: {str(e)}")
            raise

if __name__ == '__main__':
    reviewer = AICodeReviewer()
    reviewer.review_pull_request()