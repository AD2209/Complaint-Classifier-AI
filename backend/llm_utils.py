import os
import json
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

class ComplaintAnalysis(BaseModel):
    category: str = Field(description="One of: 'Fraud Investigation Portal', 'Account Services Portal', 'Loan Support Portal', 'General Support Portal', or 'Rejected'")
    urgency: str = Field(description="One of: 'Low', 'Medium', 'High', 'Critical'")
    advice: str = Field(description="2-3 sentences of immediate, actionable advice for the user.")
    action_to_take: str = Field(description="A simulated system action, e.g., 'Freeze Account', 'Escalate to Live Agent', 'Waive Late Fee', or 'None' if standard processing is fine.")
    translated_description: str = Field(description="The user's complaint description translated into English. If already in English, just return the original text.")

def analyze_complaint(description: str) -> dict:
    """
    Analyzes the complaint to extract category, urgency, advice, and a mock automated action.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        # Fallback for testing without an API key
        return {
            "category": "General Support Portal",
            "urgency": "Low",
            "advice": "Thank you for reaching out. We will look into this.",
            "action_to_take": "None",
            "translated_description": description
        }

    llm = ChatGroq(temperature=0, model_name="llama-3.3-70b-versatile")
    parser = JsonOutputParser(pydantic_object=ComplaintAnalysis)
    
    prompt = PromptTemplate(
        template="""You are an intelligent, decision-making agent for a bank.
Analyze the user's complaint strictly and provide your response as a JSON object matching the formatting instructions below.

Categories strictly allowed:
1. Fraud Investigation Portal (unauthorized transactions, stolen cards, scams)
2. Account Services Portal (balance, login, debit cards)
3. Loan Support Portal (home/auto loans, EMIs, interest)
4. General Support Portal (general inquiries)
5. Rejected (non-banking, non-financial support issues)

Determine the urgency level (Low, Medium, High, Critical) based on financial loss or security risk.
Provide 2-3 sentences of actionable advice.
Suggest an automated 'action_to_take' if applicable. Examples: 'Freeze Account', 'Generate New Card', 'Escalate to Fraud Team', 'Flag for Review', or 'None'.

{format_instructions}

User Complaint:
{description}
""",
        input_variables=["description"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    
    chain = prompt | llm | parser
    
    try:
        response = chain.invoke({"description": description})
        
        # Ensure category is exact fallback
        valid_categories = [
            "Fraud Investigation Portal",
            "Account Services Portal",
            "Loan Support Portal",
            "General Support Portal",
            "Rejected"
        ]
        
        cat = response.get("category", "General Support Portal")
        found = False
        for valid in valid_categories:
            if valid.lower() in cat.lower():
                response["category"] = valid
                found = True
                break
        if not found:
            response["category"] = "General Support Portal"
            
        return response
    except Exception as e:
        print(f"Error during analysis: {e}")
        return {
            "category": "General Support Portal",
            "urgency": "Low",
            "advice": "Our team has received your request and will contact you shortly.",
            "action_to_take": "None",
            "translated_description": description
        }
