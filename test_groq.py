import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

def test():
    user_input = "Hello, I want to raise a complaint regarding a fraud."
    llm = ChatGroq(temperature=0, model_name="llama-3.3-70b-versatile")
    prompt = PromptTemplate.from_template(
        """You are an intent classifier for a bank chatbot.
Classify the user's input into exactly one of three categories:
1. file_complaint (User wants to report an issue, open a ticket, file a complaint, or is describing a problem they want fixed)
2. retrieve_complaint (User wants to check the status of an existing ticket or reference a complaint ID)
3. unrelated (Greeting, general chatting, or completely unrelated to banking complaints)

User Input: {user_input}

Respond ONLY with the category name (e.g. "file_complaint")."""
    )
    chain = prompt | llm | StrOutputParser()
    try:
        res = chain.invoke({"user_input": user_input}).strip().lower()
        print(f"SUCCESS! Result: '{res}'")
    except Exception as e:
        print(f"EXCEPTION! {type(e)}: {e}")

if __name__ == "__main__":
    test()
