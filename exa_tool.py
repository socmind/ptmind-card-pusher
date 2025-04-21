from smolagents import Tool
import os
import json
from dotenv import load_dotenv

class ExaTool(Tool):
    name = "exa_search"
    description = """
    This tool lets you intelligently search the web and extract contents from the results.
    """
    inputs = {
        "query": {
            "type": "string",
            "description": "The search query."
        }
    }
    output_type = "array"

    def forward(self, query: str) -> list:
        load_dotenv()
        api_key = os.getenv("EXA_API_KEY")
        if not api_key:
            raise ValueError("EXA_API_KEY not found.")

        from exa_py import Exa

        exa = Exa(api_key=api_key)
        response = exa.search_and_contents(
            query,
            text=True
        )

        return response.results

exa_search = ExaTool()