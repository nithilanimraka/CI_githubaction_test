
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
    API_KEY = os.getenv('GEMINI_API_KEY')

    if not API_KEY:
        raise ValueError("GEMINI_API_KEY is not set. Please add it to your environment variables.")

    # Prepare the prompt for the LLM
    prompt = f"""
    Analyze these code changes and provide feedback using EXACTLY this format:

    FILE: [file-path]
    LINE_START: [starting-line-number]
    LINE_END: [ending-line-number]
    COMMENT: [your comment]
    SUGGESTION: [optional suggested code]

    ---
    Example 1 (single line):
    FILE: src/app.py
    LINE_START: 42
    LINE_END: 42
    COMMENT: Avoid magic numbers
    SUGGESTION: MAX_RETRIES = 3

    ---

    Example 2 (multi-line):
    FILE: src/utils.py
    LINE_START: 15
    LINE_END: 18
    COMMENT: Missing error handling
    SUGGESTION: 
        try:
            database.connect()
        except ConnectionError as e:
            logger.error(f"Connection failed: {{e}}")

    ---
    Key rules:
    1. LINE_END >= LINE_START
    2. Both lines must be in the same diff hunk
    3. Use LINE_END=LINE_START for single-line issues
    4. Separate comments with ---

    Focus on:
    - Code quality
    - Security
    - Performance
    - Style consistency
    - Documentation

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


def parse_llm_response(response: str) -> List[Dict]:
    review_comments = []
    comment_blocks = response.split('---')
    
    for block in comment_blocks:
        lines = [line.strip() for line in block.split('\n') if line.strip()]
        comment_data = {
            'path': None,
            'start_line': None,
            'end_line': None,
            'body': []
        }
        
        for line in lines:
            if line.startswith('FILE:'):
                comment_data['path'] = line.split('FILE:', 1)[-1].strip()
            elif line.startswith('LINE_START:'):
                try:
                    comment_data['start_line'] = int(line.split('LINE_START:', 1)[-1].strip())
                except ValueError:
                    continue
            elif line.startswith('LINE_END:'):
                try:
                    comment_data['end_line'] = int(line.split('LINE_END:', 1)[-1].strip())
                except ValueError:
                    continue
            elif line.startswith('COMMENT:'):
                comment_data['body'].append(line.split('COMMENT:', 1)[-1].strip())
            elif line.startswith('SUGGESTION:'):
                suggestion = line.split('SUGGESTION:', 1)[-1].strip()
                if suggestion:
                    comment_data['body'].append(f"\n```suggestion\n{suggestion}\n```")
            elif line:
                comment_data['body'].append(line)
        
        # Validation
        if (comment_data['path'] and 
            comment_data['start_line'] is not None and
            comment_data['end_line'] is not None and
            comment_data['end_line'] >= comment_data['start_line'] and
            comment_data['body']):
            
            # Format body with line range header
            line_range = f"Lines {comment_data['start_line']}-{comment_data['end_line']}:" if \
                        comment_data['start_line'] != comment_data['end_line'] else \
                        f"Line {comment_data['start_line']}:"
            
            comment_data['body'] = f"**{line_range}**\n" + '\n'.join(comment_data['body'])
            review_comments.append({
                'path': comment_data['path'],
                'start_line': comment_data['start_line'],
                'end_line': comment_data['end_line'],
                'body': comment_data['body']
            })
    
    return review_comments


# def parse_llm_response(response: str) -> List[Dict]:
#     """
#     Parse the LLM response and format it into review comments
#     Returns a list of structured comment objects
#     """
#     review_comments = []
    
#     # Split response into individual comments
#     comment_blocks = response.split('---')
    
#     for block in comment_blocks:
#         lines = [line.strip() for line in block.split('\n') if line.strip()]
#         if not lines:
#             continue
            
#         comment_data = {
#             'body': '',
#             'path': None,
#             'position': 1,  # Default to first line if not specified
#             'suggestion': None
#         }
        
#         current_section = None
        
#         for line in lines:
#             if line.startswith('FILE:'):
#                 comment_data['path'] = line.split('FILE:')[1].strip()
#             elif line.startswith('LINE:'):
#                 try:
#                     comment_data['position'] = int(line.split('LINE:')[1].strip())
#                 except ValueError:
#                     pass  # Keep default position if invalid line number
#             elif line.startswith('COMMENT:'):
#                 comment_data['body'] = line.split('COMMENT:')[1].strip()
#             elif line.startswith('SUGGESTION:'):
#                 comment_data['suggestion'] = line.split('SUGGESTION:')[1].strip()
#             else:
#                 # Handle multi-line comments
#                 if comment_data['body']:
#                     comment_data['body'] += '\n' + line
#                 else:
#                     comment_data['body'] = line
        
#         # Add code suggestion as markdown if provided
#         if comment_data['suggestion']:
#             comment_data['body'] += f"\n\n```suggestion\n{comment_data['suggestion']}\n```"
        
#         if comment_data['path'] and comment_data['body']:
#             review_comments.append({
#                 'body': comment_data['body'],
#                 'path': comment_data['path'],
#                 'position': comment_data['position']
#             })
    
#     return review_comments