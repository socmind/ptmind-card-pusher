from smolagents import Tool
import requests
import os
from dotenv import load_dotenv
import logging
from datetime import datetime
import json

# Configure logging (optional but recommended)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file once when the module is loaded
load_dotenv()
api_key = os.getenv('SIMILARWEB_API_KEY')

class SimilarWebLeadEnrichmentTool(Tool):
    """
    A smolagents Tool to fetch lead enrichment data from the SimilarWeb API.
    """
    name = "similarweb_lead_enrichment"
    description = """
    Calls the SimilarWeb Lead Enrichment API for a given domain and date range.
    Requires domain, start_date (YYYY-MM), and end_date (YYYY-MM) as input.
    Start and end date must be at most 11 months apart.
    Returns company enrichment data as a JSON formatted string.
    """
    inputs = {
        "domain": {
            "type": "string",
            "description": "The website domain to query (e.g., 'jp.ptmind.com').",
        },
        "start_date": {
            "type": "string",
            "description": "The start date for the data range in 'YYYY-MM' format (e.g., '2024-04').",
        },
        "end_date": {
            "type": "string",
            "description": "The end date for the data range in 'YYYY-MM' format (e.g., '2025-03'). MUST be at most 11 months after the start date!",
        },
    }
    # Outputting the result as a JSON formatted string, similar to the example tool
    output_type = "string"

    def forward(self, domain: str, start_date: str, end_date: str) -> str:
        """
        Executes the API call to SimilarWeb Lead Enrichment endpoint.

        Args:
            domain: The website domain to query.
            start_date: The start date in 'YYYY-MM' format.
            end_date: The end date in 'YYYY-MM' format.

        Returns:
            A JSON formatted string containing the API response, or an error message string.
        """
        if not api_key:
            error_msg = "Error: SIMILARWEB_API_KEY not found in environment variables or .env file."
            logging.error(error_msg)
            return error_msg # Return the error message as a string

        # Basic date format validation
        try:
            datetime.strptime(start_date, '%Y-%m')
            datetime.strptime(end_date, '%Y-%m')
        except ValueError:
            error_msg = "Error: Invalid date format. Please use 'YYYY-MM'."
            logging.error(error_msg)
            return error_msg # Return the error message as a string

        # Construct the API URL and parameters
        api_url = f"https://api.similarweb.com/v1/website/{domain}/lead-enrichment/all"
        params = {
            'api_key': api_key,
            'start_date': start_date,
            'end_date': end_date,
            'country': 'world',
            'main_domain_only': 'false',
            'format': 'json',
            'show_verified': 'false'
        }
        headers = {
            'accept': 'application/json'
        }

        logging.info(f"Tool '{self.name}': Requesting data for domain '{domain}' ({start_date} to {end_date})")

        try:
            # Make the GET request
            response = requests.get(api_url, headers=headers, params=params)

            # Check for HTTP errors (e.g., 401, 404, 429)
            response.raise_for_status()

            # Parse the JSON response
            data = response.json()
            logging.info(f"Tool '{self.name}': Successfully retrieved data for {domain}")

            # Return the data as a nicely formatted JSON string
            return json.dumps(data, indent=2)

        except requests.exceptions.RequestException as e:
            # Handle connection errors, timeouts, HTTP errors, etc.
            status_code = getattr(e.response, 'status_code', 'N/A')
            response_text = getattr(e.response, 'text', 'No response text available')
            error_msg = f"Error: API request failed for {domain}. Status: {status_code}. Details: {e}"
            logging.error(error_msg)
            logging.error(f"Response text (if available): {response_text}")
            # Return a descriptive error string
            return f"Error: API request failed for '{domain}'. Status code: {status_code}."

        except requests.exceptions.JSONDecodeError:
            # Handle cases where the response is not valid JSON
            error_msg = f"Error: Failed to decode JSON response for {domain}. Response text: {response.text}"
            logging.error(error_msg)
            # Return a descriptive error string
            return f"Error: Invalid JSON response received from API for '{domain}'."

        except Exception as e:
            # Catch any other unexpected errors
            error_msg = f"Error: An unexpected error occurred while processing request for {domain}: {e}"
            logging.error(error_msg)
            # Return a descriptive error string
            return f"Error: An unexpected error occurred for '{domain}'."

# Instantiate the tool for use
similarweb_lead_enrichment_tool = SimilarWebLeadEnrichmentTool()



class SimilarWebTechnographicsTool(Tool):
    """
    A smolagents Tool to fetch technographics data from the SimilarWeb API (v4).
    """
    name = "similarweb_technographics"
    description = """
    Calls the SimilarWeb Technographics API (v4) for a given domain.
    Retrieves a list of technologies detected on the website.
    Returns the list as a JSON formatted string. Requires the domain name as input.
    """
    inputs = {
        "domain": {
            "type": "string",
            "description": "The website domain to query for technographics (e.g., 'jp.ptmind.com').",
        },
        # Note: 'limit' is hardcoded to 1000 as per the provided URL example.
        # It could be added as an input if variable limits are needed.
    }
    # Outputting the result as a JSON formatted string
    output_type = "string"

    def forward(self, domain: str) -> str:
        """
        Executes the API call to the SimilarWeb Technographics v4 endpoint.

        Args:
            domain: The website domain to query.

        Returns:
            A JSON formatted string containing the API response (list of technologies),
            or an error message string.
        """
        if not api_key:
            error_msg = "Error: SIMILARWEB_API_KEY not found in environment variables or .env file."
            logging.error(error_msg)
            return error_msg # Return the error message as a string

        # Construct the API URL and parameters
        # Using the v4 endpoint as specified
        api_url = f"https://api.similarweb.com/v4/website/{domain}/technographics/all"
        params = {
            'api_key': api_key,
            'format': 'json',
            'limit': 1000 # Hardcoded limit based on the example URL
        }
        headers = {
            'accept': 'application/json'
        }

        logging.info(f"Tool '{self.name}': Requesting technographics data for domain '{domain}'")

        try:
            # Make the GET request
            response = requests.get(api_url, headers=headers, params=params)

            # Check for HTTP errors (e.g., 401, 403, 404, 429)
            response.raise_for_status()

            # Parse the JSON response
            data = response.json()
            logging.info(f"Tool '{self.name}': Successfully retrieved technographics for {domain}")

            # Return the data as a nicely formatted JSON string
            return json.dumps(data, indent=2)

        except requests.exceptions.RequestException as e:
            # Handle connection errors, timeouts, HTTP errors, etc.
            status_code = getattr(e.response, 'status_code', 'N/A')
            response_text = getattr(e.response, 'text', 'No response text available')
            error_msg = f"Error: API request failed for {domain}. Status: {status_code}. Details: {e}"
            logging.error(error_msg)
            logging.error(f"Response text (if available): {response_text}")
            # Return a descriptive error string
            return f"Error: API request failed for '{domain}'. Status code: {status_code}."

        except requests.exceptions.JSONDecodeError:
            # Handle cases where the response is not valid JSON
            error_msg = f"Error: Failed to decode JSON response for {domain}. Response text: {response.text}"
            logging.error(error_msg)
            # Return a descriptive error string
            return f"Error: Invalid JSON response received from API for '{domain}'."

        except Exception as e:
            # Catch any other unexpected errors
            error_msg = f"Error: An unexpected error occurred while processing request for {domain}: {e}"
            logging.error(error_msg)
            # Return a descriptive error string
            return f"Error: An unexpected error occurred for '{domain}'."

# Instantiate the tool for use
similarweb_technographics_tool = SimilarWebTechnographicsTool()



class SimilarWebGeneralDataTool(Tool):
    """
    A smolagents Tool to fetch general data from the SimilarWeb API (v1).
    """
    name = "similarweb_general_data"
    description = """
    Calls the SimilarWeb General Data API (v1) for a given domain.
    Retrieves general information like category, description, location, estimated revenue,
    employee count, and basic traffic overview data.
    Returns the data as a JSON formatted string. Requires the domain name as input.
    """
    inputs = {
        "domain": {
            "type": "string",
            "description": "The website domain to query for general data (e.g., 'jp.ptmind.com').",
        },
    }
    # Outputting the result as a JSON formatted string
    output_type = "string"

    def forward(self, domain: str) -> str:
        """
        Executes the API call to the SimilarWeb General Data v1 endpoint.

        Args:
            domain: The website domain to query.

        Returns:
            A JSON formatted string containing the API response (general website data),
            or an error message string.
        """
        if not api_key:
            error_msg = "Error: SIMILARWEB_API_KEY not found in environment variables or .env file."
            logging.error(error_msg)
            return error_msg # Return the error message as a string

        # Construct the API URL and parameters
        # Using the v1 endpoint as specified
        api_url = f"https://api.similarweb.com/v1/website/{domain}/general-data/all"
        params = {
            'api_key': api_key,
            'format': 'json',
        }
        headers = {
            'accept': 'application/json'
        }

        logging.info(f"Tool '{self.name}': Requesting general data for domain '{domain}'")

        try:
            # Make the GET request
            response = requests.get(api_url, headers=headers, params=params)

            # Check for HTTP errors (e.g., 401, 403, 404, 429)
            response.raise_for_status()

            # Parse the JSON response
            data = response.json()
            logging.info(f"Tool '{self.name}': Successfully retrieved general data for {domain}")

            # Return the data as a nicely formatted JSON string
            return json.dumps(data, indent=2)

        except requests.exceptions.RequestException as e:
            # Handle connection errors, timeouts, HTTP errors, etc.
            status_code = getattr(e.response, 'status_code', 'N/A')
            response_text = getattr(e.response, 'text', 'No response text available')
            error_msg = f"Error: API request failed for {domain}. Status: {status_code}. Details: {e}"
            logging.error(error_msg)
            logging.error(f"Response text (if available): {response_text}")
            # Return a descriptive error string
            return f"Error: API request failed for '{domain}'. Status code: {status_code}."

        except requests.exceptions.JSONDecodeError:
            # Handle cases where the response is not valid JSON
            error_msg = f"Error: Failed to decode JSON response for {domain}. Response text: {response.text}"
            logging.error(error_msg)
            # Return a descriptive error string
            return f"Error: Invalid JSON response received from API for '{domain}'."

        except Exception as e:
            # Catch any other unexpected errors
            error_msg = f"Error: An unexpected error occurred while processing request for {domain}: {e}"
            logging.error(error_msg)
            # Return a descriptive error string
            return f"Error: An unexpected error occurred for '{domain}'."

# Instantiate the tool for use
similarweb_general_data_tool = SimilarWebGeneralDataTool()