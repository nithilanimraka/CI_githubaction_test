
import os
import json
from google.genai import types
from google import genai
from typing import List, Dict

def analyze_code_changes(diff_content: str) -> List[Dict]:
    """
    Analyze code changes using OpenAI's GPT model
    Returns a list of review comments
    """

    try:

        API_KEY = os.getenv('GEMINI_API_KEY')

        if not API_KEY:
            raise ValueError("GEMINI_API_KEY is not set. Please add it to your environment variables.")

        # Prepare the prompt for the LLM
        prompt = f"""
        Analyze these code changes and provide feedback using EXACTLY this format:

        FILE: [file-path]
        LINES: [start_line-end_line]  # MUST have start <= end and MUST be valid numbers
        COMMENT: [clear explanation]
        SUGGESTION: |
        ```suggestion
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
        Invalid Example (REJECTED):
        FILE: src/app.py
        LINES: 42-40  # ERROR: start > end
        COMMENT: Magic numbers present
        SUGGESTION: MAX_RETRIES = 3

        ---

        Rules:
        1. Always use LINES: [start-end] format
        2. Start <= End
        3. Separate comments with ---
        4. Use "N/A" for no suggestion
        5. Suggestions must be properly indented

    Diff content:
    {diff_content}
    """

        client = genai.Client(api_key=API_KEY)

        #Get analysis from Gemini model
        response = client.models.generate_content(
            model="gemini-2.0-flash", contents=prompt
        )   

        print(response.text)
        
        # Parse and format the response
        review_comments = parse_llm_response(response.text)
        return review_comments
    except Exception as e:
        print(f"LLM analysis failed: {str(e)}")
        return []



def parse_llm_response(response: str) -> List[Dict]:
    review_comments = []
    
    for block in response.split('---'):
        lines = [line.rstrip() for line in block.split('\n') if line.strip()]
        if not lines:
            continue

        comment = {'path': None, 'start_line': None, 'end_line': None, 'body': []}
        in_suggestion = False
        suggestion_lines = []
        
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
                    continue
            elif line.startswith('COMMENT:'):
                comment['body'].append(line.split('COMMENT:', 1)[-1].strip())
            elif line.startswith('SUGGESTION:'):
                in_suggestion = True
                suggestion_lines = []
            elif in_suggestion:
                if line == '```':
                    in_suggestion = False
                    if suggestion_lines:
                        comment['body'].append('```suggestion\n' + '\n'.join(suggestion_lines) + '\n```')
                else:
                    suggestion_lines.append(line)
            else:
                comment['body'].append(line)

        # Validation
        if all([comment['path'],
              isinstance(comment['start_line'], int),
              isinstance(comment['end_line'], int),
              comment['start_line'] <= comment['end_line']]):
            
            # Format body
            line_range = (f"**Lines {comment['start_line']}-{comment['end_line']}:**\n" 
                         if comment['start_line'] != comment['end_line'] 
                         else f"**Line {comment['start_line']}:**\n")
            
            formatted_body = line_range + '\n'.join(comment['body'])
            review_comments.append({
                'path': comment['path'],
                'start_line': comment['start_line'],
                'end_line': comment['end_line'],
                'body': formatted_body
            })
    
    return review_comments

