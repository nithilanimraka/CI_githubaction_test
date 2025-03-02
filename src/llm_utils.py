
import os
import json
from google.genai import types
from google import genai
from typing import List, Dict

def analyze_code_changes(diff_content: str) -> List[Dict]:
    """
    Analyze code changes using GEMINI model
    Returns a list of review comments
    """
    API_KEY = os.getenv('GEMINI_API_KEY')

    if not API_KEY:
        raise ValueError("GEMINI_API_KEY is not set. Please add it to your environment variables.")

    # Prepare the prompt for the LLM
    prompt = f"""
    Analyze the following code changes and provide detailed review comments in the following JSON format.

    [
    {{"body": "comment text", "path": "file_path", "position": line_number}},
    ...
    ]

    Each comment should have:
    - "body": The review comment text
    - "path": The file where the comment applies
    - "position": The line number in the diff where the comment should be placed

    Ensure the response is ONLY valid JSON. Do not include explanations or extra text.

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
    """
    Parses the LLM response and formats it into GitHub review comments.

    Args:
        response (str): The JSON response from OpenAI GPT.

    Returns:
        List[Dict]: A list of structured review comments.
    """
    try:
        # Ensure the response is JSON
        return json.loads(response)
    except json.JSONDecodeError as e:
        print("Error: LLM response is not valid JSON : {e}")
        return None
