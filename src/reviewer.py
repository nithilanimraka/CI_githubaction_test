import os
from github_utils import get_pull_request_diff, post_review_comment
from llm_utils import analyze_code_changes

class AICodeReviewer:
    def __init__(self):
        self.openai_api_key = os.getenv('GEMINI_API_KEY')
        self.github_token = os.getenv('GIT_TOKEN')

    def review_pull_request(self):
        try:
            # Get the PR diff
            diff_content = get_pull_request_diff()

            # Analyze changes using LLM
            review_comments = analyze_code_changes(diff_content)

            # Post all comments in a single batch
            if review_comments:
                post_review_comment(review_comments, diff_content)
            else:
                print("No valid review comments generated")

        except Exception as e:
            print(f"Review failed: {str(e)}")
            raise

if __name__ == '__main__':
    reviewer = AICodeReviewer()
    reviewer.review_pull_request()