import json
import logging
import requests
from typing import Any, Dict, Optional
from dataclasses import dataclass
import time
from requests.exceptions import RequestException, Timeout
import os
from dotenv import load_dotenv

load_dotenv()

# --- Re-included code from the original script ---

# Configuration Class
@dataclass
class TeamsConfig:
    webhook_url: str = os.getenv("TEAMS_WEBHOOK_URL")
    timeout: int = 30
    max_retries: int = 3
    retry_delay: int = 10

# Logging Setup (optional within the tool, but good practice)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger("TeamsNotificationTool")

# Input Validation Helper
def validate_and_convert_to_string(value: Any, field_name: str) -> str:
    """
    Validate if the value can be converted to a string, and return the string representation.
    If None, return empty string. If conversion fails, raise ValueError.
    """
    if value is None:
        return ""
    try:
        # Ensure boolean False is converted correctly, etc.
        if isinstance(value, (int, float, bool)):
             return str(value)
        # Handle potential empty iterables if needed, though str() usually works
        if not value and not isinstance(value, (int, float, bool)):
             return ""
        return str(value)
    except Exception as e:
        raise ValueError(f"Tool input field '{field_name}' must be convertible to a string. Value: {repr(value)}. Error: {str(e)}")

# Teams Notification Class (copied directly)
class TeamsNotification:
    def __init__(self, config: TeamsConfig):
        self.config = config
        self.headers = {"Content-Type": "application/json"}

    def send_notification(self, card_data: Optional[Dict] = None) -> Dict:
        try:
            payload = self._build_payload(card_data)
            return self._send_with_retry(payload)
        except Exception as e:
            logger.error(f"Error building or sending notification: {str(e)}")
            return {"status": "Failure", "detail": f"Internal tool error: {str(e)}"}

    def _build_payload(self, card_data: Optional[Dict]) -> Dict:
        if card_data is None:
            card_data = {}

        # Base Payload - Adaptive Card Structure
        payload = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "type": "AdaptiveCard",
                        "body": [
                            {
                                "type": "TextBlock",
                                "size": "Large",
                                "weight": "Bolder",
                                "text": "New Lead - User Sign up (via Research Agent)",
                                "isSubtle": True
                            }
                        ],
                        "actions": [
                             {
                                "type": "Action.OpenUrl",
                                "title": "Source Info (if available)",
                                "url": card_data.get("source_url", "https://app.kocoro.ai/")
                            },
                             # Add more generic actions or make them dynamic if needed
                        ],
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "version": "1.2",
                        "msteams": {
                            "width": "Full",
                            "entities": [] # Initialize entities for mentions
                        }
                    }
                }
            ]
        }
        # --- Dynamically add sections based on card_data ---
        # (Keeping the logic exactly the same as the original script)

        # Company Name/Logo Section
        if card_data.get("company", {}).get("name") or card_data.get("image", {}).get("company", {}).get("url"):
            company_column_set = {"type": "ColumnSet", "columns": [], "style": "emphasis"}
            if card_data.get("company", {}).get("name"):
                company_column_set["columns"].append({
                    "type": "Column", "width": "stretch", "items": [{
                        "type": "TextBlock", "text": card_data["company"]["name"], "wrap": True, "size": "ExtraLarge"
                    }], "horizontalAlignment": "Left", "verticalContentAlignment": "Center"
                })
            if card_data.get("image", {}).get("company", {}).get("url"):
                company_column_set["columns"].append({
                    "type": "Column", "width": "stretch", "items": [{
                        "type": "Image", "url": card_data["image"]["company"]["url"], "height": "100px",
                        "horizontalAlignment": "Right", "altText": card_data["image"]["company"].get("name", "") + "_logo"
                    }]
                })
            payload["attachments"][0]["content"]["body"].append(company_column_set)

        # User Info Section
        if card_data.get("user", {}).get("name"):
            user_column_set = {
                "type": "ColumnSet", "columns": [
                    {"type": "Column", "items": [{"type": "Image", "url": card_data.get("image", {}).get("user", {}).get("url", "https://i.imgur.com/Nho5TnJb.jpg"), "altText": card_data["user"]["name"], "spacing": "None", "horizontalAlignment": "Left", "size": "Medium", "style": "Person", "width": "80px"}], "width": "80px", "verticalContentAlignment": "Top"},
                    {"type": "Column", "items": [{"type": "TextBlock", "weight": "Bolder", "size": "Large", "text": card_data["user"]["name"], "wrap": True}], "width": "stretch"}
                ], "separator": True
            }
            payload["attachments"][0]["content"]["body"].append(user_column_set)

            # User Contact Info (Phone/Email) - Appended to the second column of user info
            user_contact_info = {"type": "Container", "items": []}
            if card_data["user"].get("phone"):
                phone_column_set = {"type": "ColumnSet", "columns": [{"type": "Column", "width": "50px", "items": [{"type": "TextBlock", "text": "電話", "weight": "Bolder", "size": "Medium", "wrap": True}]}, {"type": "Column", "width": "stretch", "items": [{"type": "TextBlock", "text": card_data["user"]["phone"], "wrap": True}]}]}
                user_contact_info["items"].append(phone_column_set)
            if card_data["user"].get("email"):
                email_column_set = {"type": "ColumnSet", "columns": [{"type": "Column", "width": "50px", "items": [{"type": "TextBlock", "text": "メール", "weight": "Bolder", "size": "Medium", "wrap": True}]}, {"type": "Column", "width": "stretch", "items": [{"type": "TextBlock", "text": card_data["user"]["email"], "wrap": True}]}]}
                user_contact_info["items"].append(email_column_set)
            if user_contact_info["items"]:
                # Find the user_column_set we just added and append contact info to its second column's items
                user_column_set_index = -1 # It's the last item added to body so far
                payload["attachments"][0]["content"]["body"][user_column_set_index]["columns"][1]["items"].append(user_contact_info)

        # User Additional Info Section
        user_additional_info = {"type": "Container", "items": []}
        # Position
        if card_data.get("user", {}).get("position"):
            position_items = [{"type": "TextBlock", "text": card_data["user"]["position"], "wrap": True}]
            if card_data["user"].get("other_position"):
                position_items.append({"type": "TextBlock", "text": card_data["user"]["other_position"], "wrap": True})
            user_additional_info["items"].append({"type": "ColumnSet", "columns": [{"type": "Column", "width": "80px", "items": [{"type": "TextBlock", "text": "職位情報", "weight": "Bolder", "size": "Medium", "wrap": True}]}, {"type": "Column", "width": "stretch", "items": position_items}]})
        # Note/Tags
        if card_data.get("user", {}).get("note"):
            note_items = [{"type": "TextBlock", "text": card_data["user"]["note"], "wrap": True}]
            if card_data["user"].get("tags"):
                note_items.append({"type": "TextBlock", "text": card_data["user"]["tags"], "wrap": True})
            user_additional_info["items"].append({"type": "ColumnSet", "columns": [{"type": "Column", "width": "80px", "items": [{"type": "TextBlock", "text": "備考情報", "weight": "Bolder", "size": "Medium", "wrap": True}]}, {"type": "Column", "width": "stretch", "items": note_items}]})
        # Perspective
        if card_data.get("user", {}).get("perspective"):
             user_additional_info["items"].append({"type": "ColumnSet", "columns": [{"type": "Column", "width": "80px", "items": [{"type": "TextBlock", "text": "個人観点", "weight": "Bolder", "size": "Medium", "wrap": True}]}, {"type": "Column", "width": "stretch", "items": [{"type": "TextBlock", "text": card_data["user"]["perspective"], "wrap": True}]}]})
        if user_additional_info["items"]:
            payload["attachments"][0]["content"]["body"].append(user_additional_info)

        # Company Details Section
        company_details = {"type": "Container", "items": []}
        # Website
        if card_data.get("company", {}).get("website"):
             website_items = [{"type": "TextBlock", "text": f"[{card_data['company']['website']}]({card_data['company']['website']})", "wrap": True}]
             if card_data["company"].get("webpage_info"):
                 website_items.append({"type": "TextBlock", "text": card_data["company"]["webpage_info"], "wrap": True})
             if card_data["company"].get("webpage_tags"):
                 website_items.append({"type": "TextBlock", "text": card_data["company"]["webpage_tags"], "wrap": True})
             company_details["items"].append({"type": "ColumnSet", "columns": [{"type": "Column", "width": "80px", "items": [{"type": "TextBlock", "text": "サイト", "weight": "Bolder", "size": "Medium", "wrap": True}]}, {"type": "Column", "width": "stretch", "items": website_items}]})
        # Company Info/Industry/Size/Tech
        if card_data.get("company", {}).get("info"):
             info_items = [{"type": "TextBlock", "text": card_data["company"]["info"], "wrap": True}]
             if card_data["company"].get("employee_range"):
                 info_items.append({"type": "TextBlock", "text": f"社員規模：{card_data['company']['employee_range']}", "wrap": True})
             industry_tags = " ".join(filter(None, [card_data["company"].get("industry"), card_data["company"].get("tags")]))
             if industry_tags:
                 info_items.append({"type": "TextBlock", "text": industry_tags, "wrap": True})
             if card_data["company"].get("technology_name"):
                 info_items.append({"type": "TextBlock", "text": f"会社サイト採用技術: {card_data['company']['technology_name']}", "wrap": True})
             company_details["items"].append({"type": "ColumnSet", "columns": [{"type": "Column", "width": "80px", "items": [{"type": "TextBlock", "text": "会社情報", "weight": "Bolder", "size": "Medium", "wrap": True}]}, {"type": "Column", "width": "stretch", "items": info_items}]})
        # PTE Tags
        if card_data.get("company", {}).get("pte_tags"):
             company_details["items"].append({"type": "ColumnSet", "columns": [{"type": "Column", "width": "80px", "items": [{"type": "TextBlock", "text": "競合事例", "weight": "Bolder", "size": "Medium", "wrap": True}]}, {"type": "Column", "width": "stretch", "items": [{"type": "TextBlock", "text": card_data["company"]["pte_tags"], "wrap": True}]}]})
        # Similar Customers
        if card_data.get("company", {}).get("similar_customers"):
            company_details["items"].append({"type": "ColumnSet", "columns": [{"type": "Column", "width": "80px", "items": [{"type": "TextBlock", "text": "類似顧客", "weight": "Bolder", "size": "Medium", "wrap": True}]}, {"type": "Column", "width": "stretch", "items": [{"type": "TextBlock", "text": card_data["company"]["similar_customers"], "wrap": True}]}]})
        # Form Message
        if card_data.get("company", {}).get("form_message"):
            company_details["items"].append({"type": "ColumnSet", "columns": [{"type": "Column", "width": "80px", "items": [{"type": "TextBlock", "text": "問合せ", "weight": "Bolder", "size": "Medium", "wrap": True}]}, {"type": "Column", "width": "stretch", "items": [{"type": "TextBlock", "text": card_data["company"]["form_message"], "wrap": True}]}]})
        if company_details["items"]:
            payload["attachments"][0]["content"]["body"].append(company_details)

        # Lead Evaluation Section
        lead_evaluation = {"type": "Container", "items": [], "bleed": True}
        evaluation_data = card_data.get("evaluation", {})
        # Rating / Style
        if evaluation_data.get("lead_rating"):
             stars_count = evaluation_data["lead_rating"].count("★")
             if stars_count >= 4:
                 lead_evaluation["style"] = "warning"
             lead_evaluation["items"].append({"type": "ColumnSet", "columns": [{"type": "Column", "width": "80px", "items": [{"type": "TextBlock", "text": "リード評価", "weight": "Bolder", "size": "Medium", "wrap": True}]}, {"type": "Column", "width": "stretch", "items": [{"type": "TextBlock", "text": evaluation_data["lead_rating"], "wrap": True}]}]})
        # PV
        if evaluation_data.get("last_month_pv") and card_data.get("company", {}).get("website"):
            pv_text = f"{evaluation_data['last_month_pv']} ([{card_data['company']['website']}]({card_data['company']['website']}))"
            lead_evaluation["items"].append({"type": "ColumnSet", "columns": [{"type": "Column", "width": "80px", "items": [{"type": "TextBlock", "text": "先月PV", "weight": "Bolder", "size": "Medium", "wrap": True}]}, {"type": "Column", "width": "stretch", "items": [{"type": "TextBlock", "text": pv_text, "wrap": True}]}]})
        elif evaluation_data.get("last_month_pv"): # PV without website link
             lead_evaluation["items"].append({"type": "ColumnSet", "columns": [{"type": "Column", "width": "80px", "items": [{"type": "TextBlock", "text": "先月PV", "weight": "Bolder", "size": "Medium", "wrap": True}]}, {"type": "Column", "width": "stretch", "items": [{"type": "TextBlock", "text": str(evaluation_data['last_month_pv']), "wrap": True}]}]})
        # MRR
        if evaluation_data.get("estimated_mrr"):
             lead_evaluation["items"].append({"type": "ColumnSet", "columns": [{"type": "Column", "width": "80px", "items": [{"type": "TextBlock", "text": "推定MRR", "weight": "Bolder", "size": "Medium", "wrap": True}]}, {"type": "Column", "width": "stretch", "items": [{"type": "TextBlock", "text": evaluation_data["estimated_mrr"], "wrap": True}]}]})
        # Positive Factors
        if evaluation_data.get("positive_factors"):
             lead_evaluation["items"].append({"type": "ColumnSet", "columns": [{"type": "Column", "width": "80px", "items": [{"type": "TextBlock", "text": "加点要素", "weight": "Bolder", "size": "Medium", "wrap": True}]}, {"type": "Column", "width": "stretch", "items": [{"type": "TextBlock", "text": evaluation_data["positive_factors"], "wrap": True}]}]})
        # Negative Factors
        if evaluation_data.get("negative_factors"):
             lead_evaluation["items"].append({"type": "ColumnSet", "columns": [{"type": "Column", "width": "80px", "items": [{"type": "TextBlock", "text": "減点要素", "weight": "Bolder", "size": "Medium", "wrap": True}]}, {"type": "Column", "width": "stretch", "items": [{"type": "TextBlock", "text": evaluation_data["negative_factors"], "wrap": True}]}]})
        if lead_evaluation["items"]:
            payload["attachments"][0]["content"]["body"].append(lead_evaluation)

        # Mention Handling
        mention = card_data.get("mention", {})
        mention_email = mention.get("email")
        if mention_email:
            mention_name = mention.get("name")
            if not mention_name: # Derive name from email if missing
                mention_name = mention_email.split('@')[0].replace('.', ' ').replace('_', ' ').title()

            mention_text_block = {"type": "TextBlock", "text": f"<at>{mention_name}</at>", "wrap": True}
            mention_entity = {
                "type": "mention", "text": f"<at>{mention_name}</at>",
                "mentioned": {"id": mention_email, "name": mention_name}
            }
            # Append mention text to body and entity to msteams entities
            payload["attachments"][0]["content"]["body"].append(mention_text_block)
            payload["attachments"][0]["content"]["msteams"]["entities"].append(mention_entity)


        return payload

    def _send_with_retry(self, payload: Dict) -> Dict:
        """带重试机制的发送请求"""
        for attempt in range(self.config.max_retries):
            try:
                response = requests.post(
                    self.config.webhook_url,
                    headers=self.headers,
                    json=payload,
                    timeout=self.config.timeout
                )
                response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

                # Teams webhook usually returns '1' on success
                if response.status_code == 200 and response.text == "1":
                    logger.info("Notification sent successfully.")
                    return {"status": "Success", "detail": "Notification sent successfully."}
                else:
                    # Handle unexpected success response
                    logger.warning(f"Sent notification but received unexpected response. Status: {response.status_code}, Body: {response.text[:500]}")
                    # Still treat as success if status is 200 OK
                    if response.status_code == 200:
                         return {"status": "Success", "detail": f"Notification sent, but response was not '1' (Status: {response.status_code})."}
                    else: # Should be caught by raise_for_status, but as fallback
                         return {"status": "Failure", "detail": f"Sending failed with status: {response.status_code}, Response: {response.text[:200]}"}


            except Timeout:
                logger.warning(f"Request timed out on attempt {attempt + 1}/{self.config.max_retries}.")
                if attempt == self.config.max_retries - 1:
                    return {"status": "Failure", "detail": "Request timed out after multiple retries."}
            except RequestException as e:
                logger.error(f"Request failed on attempt {attempt + 1}/{self.config.max_retries}: {str(e)}")
                if attempt == self.config.max_retries - 1:
                    return {"status": "Failure", "detail": f"Request failed after multiple retries: {str(e)}"}

            # Wait before retrying only if it wasn't the last attempt
            if attempt < self.config.max_retries - 1:
                 logger.info(f"Waiting {self.config.retry_delay} seconds before retry...")
                 time.sleep(self.config.retry_delay)

        # Should theoretically not be reached if logic above is correct, but as safety
        return {"status": "Failure", "detail": "Reached max retries without success."}

# --- End of Re-included code ---


# --- Smol Gents Tool Definition ---
from smolagents import Tool

class TeamsNotificationTool(Tool):
    """
    Tool to send a formatted "New Lead / Research Findings" notification
    to a specific Microsoft Teams channel using an incoming webhook.
    It structures the provided data into an Adaptive Card.
    Intended for agents to report findings.
    """
    name = "send_lead_notification_to_teams"
    description = """Sends a formatted notification about a potential lead or research findings (user and company information) to a designated Microsoft Teams channel. Use this to report the results of your research. Provide as much detail as possible, but missing fields will be handled gracefully."""

    # Define inputs based on the 'main' function's parameters
    # All inputs are treated as strings, validation happens in 'forward'
    inputs = {
        "LeadCompanyName": {"type": "string", "description": "The name of the company identified as a lead.", "nullable": True},
        "CompanyInfo_Short": {"type": "string", "description": "A short description or summary of the company.", "nullable": True},
        "userEmail": {"type": "string", "description": "The email address of the user/contact person.", "nullable": True},
        "userName": {"type": "string", "description": "The full name of the user/contact person.", "nullable": True},
        "UserInfo_Short": {"type": "string", "description": "A short description or note about the user.", "nullable": True},
        "UserTitle_ThisCompany": {"type": "string", "description": "The user's job title at the lead company.", "nullable": True},
        "PersonalOpinionPreference": {"type": "string", "description": "Any inferred personal opinions, preferences, or relevant viewpoints of the user.", "nullable": True},
        "Top5Cases_Name": {"type": "string", "description": "Names or descriptions of similar customers or relevant case studies.", "nullable": True},
        "account_phone": {"type": "string", "description": "The phone number associated with the user or company account.", "nullable": True},
        "Image_URL_companyLogo": {"type": "string", "description": "A direct URL to the company's logo image.", "nullable": True},
        "LeadScoreLevel": {"type": "string", "description": "A rating or score for the lead (e.g., '★★★★☆', 'High Priority').", "nullable": True},
        "ReasonforPrioritization": {"type": "string", "description": "Factors suggesting why this lead should be prioritized.", "nullable": True},
        "ReasonforDeprioritization": {"type": "string", "description": "Factors suggesting why this lead might be lower priority.", "nullable": True},
        "LastMonthPV": {"type": "string", "description": "Estimated website page views for the last month (numeric value preferred).", "nullable": True},
        "potential_mrr": {"type": "string", "description": "Estimated potential Monthly Recurring Revenue (MRR) from this lead.", "nullable": True},
        "refinedURL": {"type": "string", "description": "The primary website URL for the company.", "nullable": True},
        "technology_name": {"type": "string", "description": "Technologies identified as being used by the company (especially on their website).", "nullable": True},
        "formMessage": {"type": "string", "description": "Content of any message submitted via a contact form, if applicable.", "nullable": True},
        "UserTitle_OtherCompany": {"type": "string", "description": "The user's job title at a previous or different company, if relevant.", "nullable": True},
        "CompanyIndustry": {"type": "string", "description": "The industry the company operates in.", "nullable": True},
        "employee_range": {"type": "string", "description": "The estimated number of employees (e.g., '50-100', '1000+').", "nullable": True},
        "UserTags": {"type": "string", "description": "Relevant tags or keywords associated with the user.", "nullable": True},
        "CompanyTags": {"type": "string", "description": "Relevant tags or keywords associated with the company.", "nullable": True},
        "WebPageTags": {"type": "string", "description": "Tags or keywords extracted from the company's website content.", "nullable": True},
        "WebPageInfo_Short": {"type": "string", "description": "A short summary of information found on the company's webpage.", "nullable": True},
        "PTECompetitorCaseStudyTags": {"type": "string", "description": "Tags related to competitors or relevant case studies found.", "nullable": True},
        "Image_URL_userPhoto": {"type": "string", "description": "A direct URL to the user's photo (e.g., from LinkedIn).", "nullable": True},
        "mention_name": {"type": "string", "description": "The display name of a Teams user to mention in the notification (requires mention_email).", "nullable": True},
        "mention_email": {"type": "string", "description": "The email address of a Teams user to mention in the notification.", "nullable": True},
        # Added for context from agent
        "source_url": {"type": "string", "description": "Optional: The primary URL where the research information was found.", "nullable": True},
    }

    output_type = "string" # Returns a simple status message

    def forward(
        self,
        LeadCompanyName: str = "",
        CompanyInfo_Short: str = "",
        userEmail: str = "",
        userName: str = "",
        UserInfo_Short: str = "",
        UserTitle_ThisCompany: str = "",
        PersonalOpinionPreference: str = "",
        Top5Cases_Name: str = "",
        account_phone: str = "",
        Image_URL_companyLogo: str = "",
        LeadScoreLevel: str = "",
        ReasonforPrioritization: str = "",
        ReasonforDeprioritization: str = "",
        LastMonthPV: str = "",
        potential_mrr: str = "",
        refinedURL: str = "",
        technology_name: str = "",
        formMessage: str = "",
        UserTitle_OtherCompany: str = "",
        CompanyIndustry: str = "",
        employee_range: str = "",
        UserTags: str = "",
        CompanyTags: str = "",
        WebPageTags: str = "",
        WebPageInfo_Short: str = "",
        PTECompetitorCaseStudyTags: str = "",
        Image_URL_userPhoto: str = "",
        mention_name: str = "",
        mention_email: str = "",
        source_url: str = "" # Capture the new input
    ) -> str:
        """
        Executes the tool: validates inputs, builds the data structure,
        and sends the notification via TeamsNotification class.
        """
        logger.info(f"Received request to send notification for company: {LeadCompanyName or 'N/A'}")
        data = {}
        try:
            # Validate and collect all inputs
            input_params = locals() # Get all local variables including args
            # Exclude 'self' from validation
            input_params.pop('self', None)

            for key, value in input_params.items():
                 # Skip validation for parameters not in the tool's defined inputs (like logger, internal vars)
                 if key in self.inputs:
                      data[key] = validate_and_convert_to_string(value, key)

            # Specific cleanup for URLs (remove spaces) - applied *after* validation
            data["Image_URL_companyLogo"] = data.get("Image_URL_companyLogo", "").replace(" ", "")
            data["refinedURL"] = data.get("refinedURL", "").replace(" ", "")
            data["Image_URL_userPhoto"] = data.get("Image_URL_userPhoto", "").replace(" ", "")

        except ValueError as e:
            logger.error(f"Input validation failed: {str(e)}")
            return f"Input validation failed: {str(e)}" # Return error message directly

        # Structure the data for the Adaptive Card payload builder
        custom_data = {
            "user": {
                "name": data.get("userName"), "phone": data.get("account_phone"), "email": data.get("userEmail"),
                "position": data.get("UserTitle_ThisCompany"), "note": data.get("UserInfo_Short"),
                "perspective": data.get("PersonalOpinionPreference"), "other_position": data.get("UserTitle_OtherCompany"),
                "tags": data.get("UserTags")
            },
            "evaluation": {
                "lead_rating": data.get("LeadScoreLevel"), "estimated_mrr": data.get("potential_mrr"),
                "last_month_pv": data.get("LastMonthPV"), "positive_factors": data.get("ReasonforPrioritization"),
                "negative_factors": data.get("ReasonforDeprioritization")
            },
            "company": {
                "name": data.get("LeadCompanyName"), "website": data.get("refinedURL"), "info": data.get("CompanyInfo_Short"),
                "technology_name": data.get("technology_name"), "form_message": data.get("formMessage"),
                "similar_customers": data.get("Top5Cases_Name"), "industry": data.get("CompanyIndustry"),
                "employee_range": data.get("employee_range"), "tags": data.get("CompanyTags"),
                "webpage_tags": data.get("WebPageTags"), "webpage_info": data.get("WebPageInfo_Short"),
                "pte_tags": data.get("PTECompetitorCaseStudyTags")
            },
            "image": {
                "company": {"name": data.get("LeadCompanyName"), "url": data.get("Image_URL_companyLogo")},
                "user": {"name": data.get("userName"), "url": data.get("Image_URL_userPhoto") or "https://i.imgur.com/Nho5TnJb.jpg"} # Default image
            },
            # Add mention data if email is provided
            "mention": {"name": data.get("mention_name"), "email": data.get("mention_email")} if data.get("mention_email") else {},
            # Pass source_url for potential use in actions
            "source_url": data.get("source_url")
        }


        # Send the notification using the TeamsNotification class
        try:
            config = TeamsConfig() # Uses the hardcoded URL defined above
            notification_sender = TeamsNotification(config)
            result = notification_sender.send_notification(card_data=custom_data)

            logger.info(f"Notification attempt finished with status: {result.get('status')}")
            # Return the detail message regardless of precise success check ('1')
            # The agent just needs to know if it broadly succeeded or failed.
            return result.get("detail", "Notification status unknown.")

        except Exception as e:
            logger.exception("Unhandled exception during notification sending.") # Log full traceback
            return f"Tool execution failed: An unexpected error occurred ({type(e).__name__})."


# Instantiate the tool for use
teams_notification_tool = TeamsNotificationTool()