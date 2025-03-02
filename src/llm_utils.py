
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
    Analyze the following code changes and provide detailed review comments.
    Focus on:
    - Code quality and best practices
    - Potential security vulnerabilities
    - Performance implications
    - Code style consistency

    Diff content:
    {diff_content}
    """

    client = genai.Client(api_key=API_KEY)

    #Get analysis from Gemini model
    response = client.models.generate_content(
        model="gemini-2.0-flash", contents=prompt
    )   

    # Parse and format the response
    review_comments = parse_llm_response(response)
    return review_comments

def parse_llm_response(response: str) -> List[Dict]:
    """
    Parse the LLM response and format it into review comments
    Returns a list of structured comment objects
    """
    review_comments = []
    
    try:
        # Attempt to parse JSON if the model returns structured data
        parsed_response = json.loads(response)
        if isinstance(parsed_response, list):
            return parsed_response  # Assuming the LLM gives a structured JSON list
    except json.JSONDecodeError:
        # If not JSON, process the text response
        pass

    # Fallback: Extracting comments from plain text response
    sections = response.split("\n\n")  # Assuming comments are separated by double newlines

    for section in sections:
        lines = section.split("\n")
        if len(lines) >= 3:
            # Extracting comment components
            file_line_info = lines[0].strip()  # Expected format: "File: filename.py, Line: 10"
            comment_body = "\n".join(lines[1:]).strip()

            # Extract filename and line number
            file_path = None
            position = None

            if "File:" in file_line_info and "Line:" in file_line_info:
                try:
                    parts = file_line_info.replace("File:", "").replace("Line:", "").split(",")
                    file_path = parts[0].strip()
                    position = int(parts[1].strip())
                except ValueError:
                    continue  # Skip if parsing fails

            # Create structured comment
            if file_path and position:
                review_comments.append({
                    "body": comment_body,
                    "commit_id": "LATEST_COMMIT_ID",  # Needs to be dynamically set
                    "path": file_path,
                    "position": position
                })

    return review_comments
