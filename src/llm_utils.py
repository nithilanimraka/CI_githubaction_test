# llm_utils.py (updated)

import os
import re
from typing import List, Dict
from google.genai import types
from google import genai
from unidiff import PatchSet

def analyze_code_changes(diff_content: str) -> List[Dict]:
    """
    Analyze code changes using Gemini model with proper diff parsing
    Returns structured review comments with positions
    """
    API_KEY = os.getenv('GEMINI_API_KEY')
    if not API_KEY:
        raise ValueError("GEMINI_API_KEY is not set.")

    client = genai.Client(api_key=API_KEY)
    patch_set = PatchSet(diff_content)
    comments = []

    for patched_file in patch_set:
        file_path = patched_file.target_file  # File being modified
        for hunk in patched_file:
            hunk_content = str(hunk)
            added_lines = [(i+1, line) for i, line in enumerate(hunk) if line.line_type == '+']

            if not added_lines:
                continue

            prompt = f"""Analyze this code hunk from {file_path} and provide specific feedback:
            
            {hunk_content}

            For each issue found:
            1. Specify the line number within this hunk (1-based)
            2. Provide a concise comment
            3. Use format: "Line X: [comment]"
            
            Focus on:
            - Code quality & best practices
            - Security vulnerabilities
            - Performance issues
            - Style consistency
            - Potential bugs"""

            try:
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt
                )
                comments += parse_llm_response(response.text, added_lines, file_path)
            except Exception as e:
                print(f"Error processing hunk: {str(e)}")

    return comments

def parse_llm_response(response: str, valid_lines: List[tuple], file_path: str) -> List[Dict]:
    """
    Parse LLM response into GitHub comment format
    """
    comments = []
    line_pattern = re.compile(r'Line\s+(\d+):\s*(.+)')

    # Remove 'b/' prefix from path
    clean_path = file_path.lstrip('b/')

    for match in line_pattern.findall(response):
        line_num_str, comment_text = match
        try:
            line_num = int(line_num_str)
            if any(line_num == pos for pos, _ in valid_lines):
                comments.append({
                    'body': f"🤖 AI Review: {comment_text}",
                    'path': clean_path,
                    'position': line_num
                })
        except ValueError:
            continue

    return comments