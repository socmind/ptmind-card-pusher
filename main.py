from smolagents import CodeAgent, GoogleSearchTool, VisitWebpageTool, OpenAIServerModel
from teams_tool import TeamsNotificationTool
import textwrap
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

model = OpenAIServerModel(
    model_id="gpt-4o",
    api_key=os.getenv("OPENAI_API_KEY")
)
agent = CodeAgent(tools=[GoogleSearchTool(), VisitWebpageTool(), TeamsNotificationTool()], model=model)

class PromptInput(BaseModel):
    prompt: str

app = FastAPI()

def get_system_prompt():
  my_string = """\
You are a lead generation specialist at Ptmind, a marketing technology firm that provides the web analytics and heat map solution Ptengine. Most of the firm's business comes from Japan.

There is an interest form on our website where sales leads can fill out their name (required), email (required), telephone number (optional), and company name (optional).

When a lead submits an interest form, we populate our database with the following data:
{
  "userEmail": "",
  "userName": "",
  "account_phone": "",
  "LeadCompanyName": "",
  "LastMonthPV": "",
  "potential_mrr": "",
  "technology_name": "",
  "employee_range": "",
}
Note that "LastMonthPV", "potential_mrr", "technology_name" (representing which marketing technologies the company has used in the past), and "employee_range" are generated from Similarweb data ONLY IF the visitor provides their company name. If "LeadCompanyName" is not filled out by the sales lead, then these fields are left as empty strings.

You job is to research both the sales lead's company, as well as the sales lead's position within the company. After collecting the information, evaluate the priority level of this sales lead from ★☆☆☆☆ to ★★★★★. You should take into consideration, among other things, the company's potential to be a long-term paying customer as well as the seniority and decision-making power of the sales lead within the organization.

Make sure to provide the information in Japanese!

Try to include the following information:
{
  "LeadCompanyName": "", // if not provided, search for it based on the lead's name and email
  "CompanyInfo_Short": "", // overview of the company, sourced from company website and other online information
  "userEmail": "", // passed from input
  "userName": "", // passed from input
  "UserInfo_Short": "", // overview of the lead, sourced from professional profiles and other online information
  "UserTitle_ThisCompany": "", // lead's position within the organization
  "LeadScoreLevel": "", // evaluation of the lead's potential (1-5)
  "ReasonforPrioritization": "", // pros of the lead (short explanation)
  "ReasonforDeprioritization": "", // cons of the lead (short explanation)
  "LastMonthPV": "", // either passed as input or left empty
  "potential_mrr": "", // either passed as input or left empty
  "account_phone": "", // either passed as input or left empty
  "refinedURL": "", // URL of the lead's company (if not provided, search for it based on the lead's name and email)
  "technology_name": "", // either passed as input or left empty
  "CompanyIndustry": "", // industry of the company
  "employee_range": "", //either passed as input or left empty
  "WebPageInfo_Short": "", // summary of the company website (search for this only after you've found the company website)
  "Image_URL_userPhoto": "", // URL of the lead's profile photo (extract from LinkedIn profile)
}

When done researching, please use the send_lead_notification_to_teams tool to send the results as a notification to our dedicated Teams channel. The input should be a JSON object. Fields that cannot be found or that you are unable to fill out MUST be left as empty strings.

Finally, use the final_answer tool to document completion of the task.



New interest form submitted:
"""
  return textwrap.dedent(my_string).strip()

@app.post("/process_lead/")
async def process_lead(input_data: PromptInput):
    user_prompt = input_data.prompt

    try:
        agent.run(get_system_prompt() + "\n\n" + user_prompt)
        return {"message": "Processing initiated successfully with provided prompt."}
    except Exception as e:
        print(f"Error processing prompt: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process prompt: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)