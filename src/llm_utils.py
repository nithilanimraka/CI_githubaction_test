
import os
import json
from google.genai import types
from google import genai
from typing import List, Dict

from github_utils import get_valid_hunks

def analyze_code_changes(diff_content: str) -> List[Dict]:
    """
    Analyze code changes using OpenAI's GPT model
    Returns a list of review comments
    """

    try:

        API_KEY = os.getenv('GEMINI_API_KEY')

        if not API_KEY:
            raise ValueError("GEMINI_API_KEY is not set. Please add it to your environment variables.")

        hunks = get_valid_hunks(diff_content)

        # Prepare the prompt for the LLM
        prompt = f"""
        Analyze these code changes and provide feedback using EXACTLY this format:

        FILE: [file-path]
        LINES: [start_line-end_line]  # MUST be within the same diff hunk
        COMMENT: [clear explanation]
        SUGGESTION: |
        [exact code replacement OR N/A]

        ---
        Example Valid Comment:
        FILE: src/utils.py
        LINES: 15-18
        COMMENT: Missing error handling for database connection
        SUGGESTION: |
        try:
            db.connect()
        except ConnectionError as e:
            logger.error(f"Connection failed: {{e}}")

        ---
        Invalid Example (will be rejected):
        FILE: src/utils.py
        LINES: fifteen-eighteen
        COMMENT: This will be skipped

        ---

        Important Rules:
        1. Never include code snippets in COMMENT
        2. Always verify line numbers exist in the diff
        3. Keep suggestions focused on changed lines
        4. Use exactly one '---' between comments

        Diff content:
        {diff_content}
        """

        client = genai.Client(api_key=API_KEY)

        #Get analysis from Gemini model
        response = client.models.generate_content(
            model="gemini-2.0-flash", contents=prompt
        )   

        #print(response.text)
        
        # Parse and format the response
        review_comments = parse_llm_response(response.text)
        print(f"Parsed {len(review_comments)} valid comments")
        return review_comments
    except Exception as e:
        print(f"LLM analysis failed: {str(e)}")
        return []



def parse_llm_response(response: str) -> List[Dict]:
    """Parse LLM response with strict validation"""
    review_comments = []
    
    for block in response.split('---'):
        lines = [line.strip() for line in block.split('\n') if line.strip()]
        if not lines:
            continue

        comment = {
            'path': None,
            'start_line': None,
            'end_line': None,
            'body': []
        }
        valid = True
        
        # Parse block
        for line in lines:
            if line.startswith('FILE:'):
                comment['path'] = line.split('FILE:', 1)[-1].strip()
            elif line.startswith('LINES:'):
                try:
                    parts = line.split('LINES:', 1)[-1].strip().split('-')
                    start = int(parts[0])
                    print(start)
                    end = int(parts[1])
                    print(end)
                    comment['start_line'], comment['end_line'] = sorted([start, end])
                except (ValueError, IndexError):
                    valid = False
            elif line.startswith('COMMENT:'):
                comment['body'].append(line.split('COMMENT:', 1)[-1].strip())
            elif line.startswith('SUGGESTION:'):
                suggestion = line.split('SUGGESTION:', 1)[-1].strip()
                if suggestion and suggestion != 'N/A':
                    comment['body'].append(f'```suggestion\n{suggestion}\n```')
            else:
                comment['body'].append(line)

        # Validate required fields
        if not all([
            comment['path'],
            isinstance(comment['start_line'], int),
            isinstance(comment['end_line'], int),
            # comment['start_line'] <= comment['end_line']
        ]):
            valid = False

        if valid:
            review_comments.append({
                'path': comment['path'],
                'start_line': comment['start_line'],
                'end_line': comment['end_line'],
                'body': '\n'.join(comment['body'])
            })
        else:
            print(f"Skipping invalid block:\n{block}")
    
    return review_comments
