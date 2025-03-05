
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

    FILE: [file path]
    LINE: [exact line number from + lines]
    COMMENT: [your observation]
    SUGGESTION: [specific code replacement OR N/A]

    Formatting rules:
    1. Preserve markdown code blocks exactly
    2. Use triple backticks for suggestions
    3. Keep comments concise (1-3 sentences)
    4. Separate comment blocks with ---

    Example response:
    FILE: .github/workflows/review.yml
    LINE: 12
    COMMENT: Consider adding branch filters
    SUGGESTION: |
    on:
        pull_request:
        branches: [main, develop]

    ---

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



"""
This is the final code given by deepseek to parse the response from the LLM model. It includes errors
"""

def parse_llm_response(response: str) -> List[Dict]:
    review_comments = []
    
    # Split into comment blocks while preserving code blocks
    comment_blocks = []
    current_block = []
    in_code_block = False
    
    for line in response.split('\n'):
        if line.strip().startswith('---') and not in_code_block:
            if current_block:
                comment_blocks.append('\n'.join(current_block))
                current_block = []
        elif line.strip().startswith('```'):
            in_code_block = not in_code_block
            current_block.append(line)
        else:
            current_block.append(line)
    
    if current_block:
        comment_blocks.append('\n'.join(current_block))

    for block in comment_blocks:
        comment_data = {
            'path': None,
            'line': None,
            'body': []
        }
        
        current_section = None
        
        for line in block.split('\n'):
            line = line.rstrip()
            
            if line.startswith('FILE:'):
                comment_data['path'] = line.split('FILE:', 1)[1].strip()
            elif line.startswith('LINE:'):
                try:
                    comment_data['line'] = int(line.split('LINE:', 1)[1].strip())
                except (ValueError, IndexError):
                    continue
            elif line.startswith('COMMENT:'):
                comment_data['body'].append(line.split('COMMENT:', 1)[1].strip())
            elif line.startswith('SUGGESTION:'):
                suggestion = line.split('SUGGESTION:', 1)[1].strip()
                comment_data['body'].append(f"\n```suggestion\n{suggestion}\n```")
            elif line and any([line.startswith(s) for s in ['FILE:', 'LINE:', 'COMMENT:', 'SUGGESTION:']]):
                continue  # Skip empty lines after headers
            else:
                if comment_data['body']:
                    comment_data['body'].append(line)

        # Validate and format
        if comment_data['path'] and comment_data['line'] is not None and comment_data['body']:
            try:
                formatted_body = '\n'.join(comment_data['body'])
                # Remove empty suggestion blocks
                formatted_body = formatted_body.replace('```suggestion\n\n```', '')
                review_comments.append({
                    'path': comment_data['path'],
                    'line': comment_data['line'],
                    'body': formatted_body
                })
            except KeyError:
                continue

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