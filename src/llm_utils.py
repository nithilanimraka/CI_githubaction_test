
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
        ```suggestion
        [exact code replacement OR REMOVE_THIS_LINE_IF_NO_SUGGESTION]

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
        Invalid Example (REJECTED):
        FILE: src/app.py
        LINES: 42-40  # ERROR: start > end
        COMMENT: Magic numbers present
        SUGGESTION: MAX_RETRIES = 3

        ---

        Invalid Example (REJECTED):
        FILE: src/app.py
        LINES: invalid-numbers
        COMMENT: This will be skipped

        ---

        Rules:
        1.Never suggest changes spanning multiple hunks
        2.Keep line ranges tight around actual changes
        3.Verify line numbers exist in the diff below
        4.Use exact line numbers from the diff
        5.Seperate comments with ---

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
        review_comments = parse_llm_response(response.text,hunks)
        return review_comments
    except Exception as e:
        print(f"LLM analysis failed: {str(e)}")
        return []



def parse_llm_response(response: str, hunks: List[dict]) -> List[Dict]:
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
        valid_block = True
        
        for line in lines:
            if line.startswith('FILE:'):
                comment['path'] = line.split('FILE:', 1)[-1].strip()
            elif line.startswith('LINES:'):
                try:
                    parts = line.split('LINES:', 1)[-1].strip().split('-')
                    start = int(parts[0])
                    end = int(parts[1])
                    comment['start_line'], comment['end_line'] = sorted([start, end])
                except (ValueError, IndexError):
                    valid_block = False
            elif line.startswith('COMMENT:'):
                comment['body'].append(line.split('COMMENT:', 1)[-1].strip())
            elif line.startswith('SUGGESTION:'):
                suggestion = line.split('SUGGESTION:', 1)[-1].strip()
                if suggestion and suggestion != 'N/A':
                    comment['body'].append(f'```suggestion\n{suggestion}\n```')
            elif line:
                comment['body'].append(line)

        # Strict validation
        if not all([comment['path'],
                   isinstance(comment['start_line'], int),
                   isinstance(comment['end_line'], int),
                   comment['start_line'] <= comment['end_line']]):
            valid_block = False

        # Additional hunk validation
        valid_hunk = False
        for hunk in hunks:
            if (comment['path'] == hunk['file'] and
                comment['start_line'] >= hunk['start'] and
                comment['end_line'] <= hunk['end']):
                valid_hunk = True
                break
                
        if not valid_hunk:
            print(f"Skipping cross-hunk comment: {comment['path']} {comment['start_line']}-{comment['end_line']}")
            continue

        if valid_block:
            line_range = (f"Lines {comment['start_line']}-{comment['end_line']}" 
                         if comment['start_line'] != comment['end_line'] 
                         else f"Line {comment['start_line']}")
            
            formatted_body = f"**{line_range}**\n" + '\n'.join(comment['body'])
            review_comments.append({
                'path': comment['path'],
                'start_line': comment['start_line'],
                'end_line': comment['end_line'],
                'body': formatted_body
            })
        else:
            print(f"Skipping invalid block: {block}")
    
    return review_comments

