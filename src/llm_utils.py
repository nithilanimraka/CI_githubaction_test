
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
    Analyze the following code changes and provide review comments using EXACTLY this format:

    FILE: [file-path]
    LINE: [line-number]
    COMMENT: [your comment]
    SUGGESTION: [optional suggested code]

    ---
    Example:
    FILE: src/app.py
    LINE: 42
    COMMENT: Avoid magic numbers, consider using a constant
    SUGGESTION: MAX_RETRIES = 3

    ---

    Make sure to insert '---' in between two review comments. IT IS A MUST!!!

    Focus on:
    - Code quality issues
    - Security vulnerabilities
    - Performance optimizations
    - Style inconsistencies
    - Possible bugs
    - Missing documentation

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
    return review_comments



"""
This is the final code given by deepseek to parse the response from the LLM model. It includes errors
"""

def parse_llm_response(response: str) -> List[Dict]:
    review_comments = []
    
    # Split response into valid comment blocks
    comment_blocks = response.split('---')
    
    for block in comment_blocks:
        block = block.strip()
        if not block:
            continue
            
        comment_data = {
            'path': None,
            'line': None,
            'body': ''
        }
        
        # Validate required fields
        has_file = False
        has_line = False
        has_comment = False
        
        for line in block.split('\n'):

            line = line.strip()

            if line.startswith('FILE:'):
                comment_data['path'] = line.split('FILE:', 1)[-1].strip()
                has_file = True

            elif line.startswith('LINE:'):
                try:
                    comment_data['line'] = int(line.split('LINE:', 1)[-1].strip())
                    has_line = True
                except (ValueError, IndexError):
                    continue

            elif line.startswith('COMMENT:'):
                comment_data['body'] += line.split('COMMENT:', 1)[-1].strip() + '\n'
                has_comment = True

            elif line.startswith('SUGGESTION:'):
                suggestion = line.split('SUGGESTION:', 1)[-1].strip()
                if suggestion and suggestion != 'N/A':
                    comment_data['body'] += f"\n```suggestion\n{suggestion}\n```"

            elif line:
                comment_data['body'] += line + '\n'
        
        # Only add properly formatted comments
        if has_file and has_line and has_comment:
            comment_data['body'] = comment_data['body'].strip()
            review_comments.append(comment_data)
        else:
            print(f"Skipping invalid comment block:\n{block}")
            
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