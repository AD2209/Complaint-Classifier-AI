import streamlit as st
import os
import requests
import json
import tempfile
from gtts import gTTS
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from groq import Groq

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

st.set_page_config(page_title="Bank Support Chatbot", page_icon="🏦", layout="centered")

# Cleaner UI CSS
st.markdown("""
<style>
    /* Hide Streamlit top padding and main menu */
    #MainMenu {visibility: hidden;}
    .block-container {
        padding-top: 3rem;
        padding-bottom: 3rem;
        max-width: 850px;
    }
    
    /* Global background and font */
    .stApp {
        background-color: #0f0f11;
        color: #EAEAEA;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #FFFFFF;
        font-weight: 600;
    }
    
    /* Seamless Voice Bar */
    [data-testid="stAudioInput"] {
        margin: 30px auto;
        width: 100%;
        max-width: 600px;
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    
    [data-testid="stAudioInput"] > div {
        background-color: #1e1e24 !important;
        border-radius: 15px !important;
        border: 1px solid #2A2A35 !important;
        box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.4) !important;
        padding: 5px 10px !important;
        transition: all 0.2s ease;
    }
    
    [data-testid="stAudioInput"] label {
        display: none !important;
    }
    
    
    
    /* Fix Top Header Background Mismatch */
    [data-testid="stHeader"] {
        background-color: transparent !important;
    }
    
    /* Fix Bottom Input Container Background Mismatch */
    [data-testid="stBottom"] {
        background-color: #0f0f11 !important;
    }
    [data-testid="stBottom"] > div {
        background-color: #0f0f11 !important;
    }
    .stChatInputContainer {
        border-radius: 15px !important;
        background-color: #1e1e24 !important;
        border: 1px solid #2A2A35 !important;
        padding-top: 5px !important;
        z-index: 11;
    }
    
    .stChatInputContainer textarea {
        padding-left: 15px !important;
    }
    
    /* Make sure bottom padding accommodates both */
    .block-container {
        padding-bottom: 180px !important;
    }
    
    /* Force Sidebar Toggle Chevron to be Visible */
    [data-testid="collapsedControl"] {
        visibility: visible !important;
        display: flex !important;
        z-index: 9999 !important;
        color: #EAEAEA !important;
        background-color: #1e1e24 !important;
        border-radius: 50%;
    }

    /* Chat message styling */
    .stChatMessage {
        background-color: transparent !important;
    }
    .stChatMessage[data-testid="chat-message-user"] {
        background-color: #1e1e24 !important;
        border-radius: 20px;
        padding: 15px 20px;
        margin-bottom: 10px;
        border: 1px solid #2A2A35;
    }
    .stChatMessage[data-testid="chat-message-assistant"] {
        background-color: transparent !important;
        border: none;
        padding: 10px 0px;
        margin-bottom: 10px;
    }
    
    /* Clean up the audio player to be less obtrusive */
    audio {
        height: 40px;
        width: 100%;
        outline: none;
        border-radius: 8px;
        margin-top: 10px;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background-color: #1e1e24 !important;
        border-radius: 12px;
        border: 1px solid #2A2A35;
        color: #EAEAEA !important;
    }
    
    /* Empty State Styling (Gemini-like) */
    .empty-state {
        text-align: center;
        margin-top: 10vh;
        margin-bottom: 40px;
    }
    .empty-state h2 {
        font-size: 2.5rem;
        font-weight: 500;
        background: -webkit-linear-gradient(45deg, #FF6B00, #FF9D4A);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 5px;
    }
    .empty-state h1 {
        font-size: 2.8rem;
        font-weight: 600;
        color: #EAEAEA;
        margin-top: 0px;
    }
    
    /* Suggestion Chips */
    .stButton>button {
        border-radius: 25px;
        background-color: #1e1e24;
        border: 1px solid #2A2A35;
        color: #EAEAEA;
        padding: 10px 20px;
        width: 100%;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        background-color: #2b313e;
        border-color: #FF6B00;
        color: #FF6B00;
    }
    
</style>
""", unsafe_allow_html=True)

if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_api_key_here":
    st.warning("Please configure your GROQ_API_KEY in the .env file.")

# Backend API URL
API_URL = "http://localhost:8000"

def get_intent(user_input: str) -> str:
    """Classifies intent into: file_complaint, retrieve_complaint, unrelated"""
    if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_api_key_here":
        # simple fallback for testing
        input_lower = user_input.lower()
        if "file" in input_lower or "complaint" in input_lower or "issue" in input_lower:
            return "file_complaint"
        if "retrieve" in input_lower or "check" in input_lower or "status" in input_lower:
            return "retrieve_complaint"
        return "unrelated"

    llm = ChatGroq(temperature=0, model_name="llama-3.3-70b-versatile")
    prompt = PromptTemplate.from_template(
        """You are an intent classifier for a banking chatbot.
Classify the user's input into exactly one of four categories:
1. file_complaint (User wants to report an issue, open a ticket, file a complaint, or is describing a problem they want fixed)
2. retrieve_complaint (User wants to check the status of an existing ticket or reference a complaint ID)
3. general_query (User is asking a general banking question like "how do I secure my account", "what are your loan rates", "what is a routing number")
4. unrelated (Greeting, general chatting, or completely unrelated to banking complaints)

User Input: {user_input}

Respond ONLY with the category name (e.g. "file_complaint")."""
    )
    chain = prompt | llm | StrOutputParser()
    try:
        res = chain.invoke({"user_input": user_input}).strip().lower()
        print(f"Classification result: '{res}'")
        if "file" in res or "complaint" in res and "retrieve" not in res: return "file_complaint"
        if "retrieve" in res or "status" in res: return "retrieve_complaint"
        if "general" in res or "query" in res: return "general_query"
        return "unrelated"
    except Exception as e:
        print("Intent Error:", e)
        return "unrelated"

def generate_chat_response(user_input: str) -> str:
    """Uses LLM to answer chat queries or general banking questions."""
    if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_api_key_here":
        return "I am a banking assistant, but my AI connection is currently down. Please contact support."
        
    llm = ChatGroq(temperature=0.5, model_name="llama-3.3-70b-versatile")
    prompt = PromptTemplate.from_template(
        """You are a helpful, conversational, and professional banking assistant.
The user is talking to you. If they say hi or introduce themselves, greet them back naturally. If they ask a banking question, answer it concisely.
Do not ask them to file a complaint unless they are explicitly reporting an issue or failure.

User: {user_input}
Response:"""
    )
    chain = prompt | llm | StrOutputParser()
    try:
        return chain.invoke({"user_input": user_input}).strip()
    except Exception as e:
        print("Chat Query Error:", e)
        return "I'm sorry, I'm having trouble thinking right now. Please try again later."

def handle_conversational_extraction(user_input: str, current_data: dict, user_language: str) -> tuple:
    """Uses LLM to extract complaint details and generate the next prompt."""
    if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_api_key_here":
        return current_data, "Please configure Groq API."
        
    llm = ChatGroq(temperature=0, model_name="llama-3.3-70b-versatile")
    
    prompt = PromptTemplate.from_template(
        """You are a helpful banking assistant collecting details to file a complaint.
You need 4 pieces of information: Name, Account Number, Mobile Number, and Description of the issue.

Current collected details:
{current_data}

User's new message:
{user_input}

Task 1: Extract any new details provided in the user's message and merge them with the current details. If a piece of information is still missing, keep it as null.
Task 2: If any details are still missing, formulate a polite question asking the user for ONE of the missing details.
Task 3: If all details are collected, your next_question should be exactly: "ALL_DETAILS_COLLECTED".

IMPORTANT: The user speaks ISO-639-1 language code {user_language}. Your next_question MUST be translated into {user_language}.

Respond ONLY with a valid JSON object matching this schema:
{{
  "name": "extracted name or null",
  "account_number": "extracted account or null",
  "mobile": "extracted mobile or null",
  "description": "extracted description or null",
  "next_question": "your question in {user_language}"
}}"""
    )
    
    chain = prompt | llm | StrOutputParser()
    try:
        res = chain.invoke({
            "current_data": json.dumps(current_data), 
            "user_input": user_input,
            "user_language": user_language
        })
        import re
        match = re.search(r'\{.*\}', res.strip(), re.DOTALL)
        if match:
            parsed = json.loads(match.group(0))
        else:
            parsed = json.loads(res.strip())
            
        new_data = {
            "name": parsed.get("name"),
            "account_number": parsed.get("account_number"),
            "mobile": parsed.get("mobile"),
            "description": parsed.get("description")
        }
        return new_data, parsed.get("next_question", "Could you provide more details?")
    except Exception as e:
        print("Extraction Error:", e)
        return current_data, "I'm having trouble processing that. Could you repeat?"

def generate_tts_audio(text: str, lang: str = 'en') -> str:
    """Generate TTS audio and return the path to the temp file."""
    try:
        tts = gTTS(text=text, lang=lang)
    except Exception as e:
        print(f"TTS language '{lang}' not supported. Error: {e}")
        try:
            tts = gTTS(text=text, lang='en')
        except Exception as e2:
            return None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            tts.save(f.name)
            return f.name
    except Exception as e:
        print("TTS Error:", e)
        return None

def transcribe_audio(audio_bytes):
    """Transcribe audio using Groq Whisper and detect language."""
    if not GROQ_API_KEY or GROQ_API_KEY == "your_groq_api_key_here":
        return "Could not transcribe audio. API key not set.", "en"
    try:
        client = Groq()
        # write bytes to temp file because groq client needs a file object
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(audio_bytes)
            temp_name = f.name
        
        with open(temp_name, "rb") as file:
            transcription = client.audio.transcriptions.create(
              file=(temp_name, file.read()),
              model="whisper-large-v3",
              prompt="The user is talking to a banking assistant in English or Hindi (नमस्ते). Use Devanagari script for Hindi.",
              response_format="verbose_json",
              temperature=0.0
            )
        os.remove(temp_name)
        lang = getattr(transcription, "language", "en")
        if not lang: lang = "en"
        return transcription.text, lang
    except Exception as e:
        print("Transcription Exception:", e)
        return f"Error transcribing audio: {str(e)}", "en"

# Session State for Conversation Management
if "messages" not in st.session_state:
    st.session_state.messages = []
if "flow_state" not in st.session_state:
    st.session_state.flow_state = "idle" # idle | awaiting_filing_choice | awaiting_complaint_form | collecting_complaint_details | awaiting_complaint_id
if "temp_user_details" not in st.session_state:
    st.session_state.temp_user_details = {"name": "", "account_number": "", "mobile": ""}
if "audio_last_played" not in st.session_state:
    st.session_state.audio_last_played = None
if "user_language" not in st.session_state:
    st.session_state.user_language = "en"
if "complaint_data" not in st.session_state:
    st.session_state.complaint_data = {"name": None, "account_number": None, "mobile": None, "description": None}

# Display chat messages
for message in st.session_state.messages:
    avatar = "🧑‍💻" if message["role"] == "user" else "🏦"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])
        if message.get("audio"):
            st.audio(message["audio"], format="audio/mp3")

# Input Handling State
if "audio_key" not in st.session_state:
    st.session_state.audio_key = 0
if "pending_audio_text" not in st.session_state:
    st.session_state.pending_audio_text = None

user_input = st.chat_input("Type your message here...", accept_file=True, file_type=["png", "jpg", "jpeg"])
raw_input = None

if st.session_state.pending_audio_text:
    raw_input = st.session_state.pending_audio_text
    st.session_state.pending_audio_text = None


def render_suggestion_chips():
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    raw_in = None
    if c1.button("🚨 Report Fraud"): raw_in = "I want to report fraud on my account."
    if c2.button("💳 Lost Card"): raw_in = "I want to file a complaint about my lost debit card."
    if c3.button("🏦 Loan Issue"): raw_in = "I want to file a complaint regarding my loan."
    if c4.button("🗣️ Use Voice"):
        st.session_state.flow_state = "collecting_complaint_details"
        msg = "I'm listening. Please tell me your name, account number, and what happened."
        audio = generate_tts_audio(msg, lang="en")
        st.session_state.messages.append({"role": "assistant", "content": msg, "audio": audio})
        st.rerun()
    return raw_in

if len(st.session_state.messages) == 0:
    st.markdown("""
    <div class="empty-state">
        <h2>Hi there</h2>
        <h1>How can I help you today?</h1>
    </div>
    """, unsafe_allow_html=True)

if st.session_state.flow_state == "idle":
    chips_input = render_suggestion_chips()
    if chips_input:
        raw_input = chips_input

if user_input:
    if getattr(user_input, "files", None):
        st.session_state.chat_attachment = user_input.files[0]
    
    if getattr(user_input, "text", None):
        raw_input = user_input.text
    elif getattr(user_input, "files", None):
        raw_input = "I've attached an image for my complaint."

if raw_input:
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": raw_input})
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(raw_input)
        
    response_text = ""

    # Flow Management
    if st.session_state.flow_state == "idle":
        intent = get_intent(raw_input)
        if intent == "file_complaint":
            response_text = "I'd be happy to help you file a complaint. How would you like to provide your details?"
            st.session_state.flow_state = "awaiting_filing_choice"
        elif intent == "retrieve_complaint":
            response_text = "Sure, I can help you check the status of your complaint. Please enter your Complaint Reference ID (e.g., REF-1234ABCD)."
            st.session_state.flow_state = "awaiting_complaint_id"
        else:
            # Handle "general_query" and "unrelated" conversational chat via normal LLM
            response_text = generate_chat_response(raw_input)
            
    elif st.session_state.flow_state == "awaiting_filing_choice":
        # Form logic happens outside chat message loop
        pass
        
    elif st.session_state.flow_state == "awaiting_complaint_form":
        # Form logic happens outside chat message loop
        pass
        
    elif st.session_state.flow_state == "collecting_complaint_details":
        new_data, next_question = handle_conversational_extraction(
            raw_input, 
            st.session_state.complaint_data, 
            st.session_state.user_language
        )
        st.session_state.complaint_data = new_data
        
        if next_question == "ALL_DETAILS_COLLECTED":
            with st.spinner("Submitting your complaint..."):
                try:
                    # Upload conversational attachment if exists
                    attachment_path = None
                    if "chat_attachment" in st.session_state and st.session_state.chat_attachment:
                        upload_res = requests.post(f"{API_URL}/upload/", files={"file": (st.session_state.chat_attachment.name, st.session_state.chat_attachment, st.session_state.chat_attachment.type)})
                        if upload_res.status_code == 200:
                            attachment_path = upload_res.json().get("attachment_path")
                            
                    formatted_details = f"Name: {new_data['name']}, Account: {new_data['account_number']}, Mobile: {new_data['mobile']}"
                    payload = {
                        "user_details": formatted_details,
                        "description": new_data['description'],
                        "attachment_path": attachment_path
                    }
                    res = requests.post(f"{API_URL}/complaints/", json=payload, timeout=15)
                    if res.status_code == 200:
                        data = res.json()
                        response_text = f"Your complaint has been successfully filed under the category **{data['category']}**.\n\nYour Reference ID is: **{data['id']}**.\n\nPlease keep this ID safe."
                        urgency = data.get("urgency", "Low")
                        if urgency in ["High", "Critical"]: response_text += f"\n\n⚠️ **Urgency Level: {urgency}** - This issue has been prioritized."
                        action_taken = data.get("action_taken")
                        if action_taken and action_taken.lower() != "none": response_text += f"\n\n🚨 **Agent Action Completed:** {action_taken}"
                        advice = data.get("advice")
                        if advice: response_text += f"\n\n💡 **Next Steps / Advice:**\n{advice}"
                    elif res.status_code == 400:
                        data = res.json()
                        response_text = f"**Complaint Rejected.**\n{data.get('detail', 'Your request could not be processed.')}"
                    else:
                        response_text = "I'm sorry, there was an issue filing your complaint. Please try again later."
                except Exception as e:
                    response_text = f"Could not connect to the backend server. Error: {e}"
            st.session_state.flow_state = "idle"
            st.session_state.complaint_data = {"name": None, "account_number": None, "mobile": None, "description": None}
            st.session_state.chat_attachment = None
        else:
            response_text = next_question
        
    elif st.session_state.flow_state == "awaiting_complaint_id":
        complaint_id = raw_input.strip()
        try:
            res = requests.get(f"{API_URL}/complaints/{complaint_id}", timeout=10)
            if res.status_code == 200:
                data = res.json()
                response_text = f"Here are the details for your complaint: \n- **ID**: {data['id']}\n- **Category**: {data['category']}\n- **Status**: {data['status']}\n- **Description**: {data['description']}"
            else:
                response_text = "I couldn't find a complaint with that ID. Please check and try again."
        except Exception as e:
            response_text = f"Could not connect to the backend server. Error: {e}"
            
        st.session_state.flow_state = "idle"

    # Generate TTS audio
    audio_path = None
    if response_text:
        audio_path = generate_tts_audio(response_text, lang=st.session_state.user_language)

    # Display assistant response
    if response_text:
        st.session_state.messages.append({"role": "assistant", "content": response_text, "audio": audio_path})
        with st.chat_message("assistant", avatar="🏦"):
            st.markdown(response_text)
            if audio_path:
                st.audio(audio_path, format="audio/mp3")

# Form Rendering & Choice Rendering
if st.session_state.flow_state == "awaiting_filing_choice":
    with st.chat_message("assistant", avatar="🏦"):
        st.markdown("Please choose how you'd like to proceed:")
        col1, col2 = st.columns(2)
        if col1.button("📝 Fill out a Form"):
            st.session_state.flow_state = "awaiting_complaint_form"
            st.rerun()
        if col2.button("🗣️ Talk to Assistant"):
            st.session_state.flow_state = "collecting_complaint_details"
            msg = "Great! Please tell me your name, account number, and what happened."
            audio = generate_tts_audio(msg, lang="en")
            st.session_state.messages.append({"role": "assistant", "content": msg, "audio": audio})
            st.rerun()

if st.session_state.flow_state == "awaiting_complaint_form":
    with st.chat_message("assistant", avatar="🏦"):
        st.markdown("Please fill out this form to file your complaint.")
        with st.form("complaint_form", clear_on_submit=True):
            f_name = st.text_input("Full Name")
            f_account = st.text_input("Bank Account Number")
            f_mobile = st.text_input("Registered Mobile Number")
            f_desc = st.text_area("Complaint Description")
            f_image = st.file_uploader("Attach Image (Optional)", type=["png", "jpg", "jpeg"])
            submit_btn = st.form_submit_button("Submit Complaint")
            
            if submit_btn:
                if not f_name or not f_account or not f_mobile or not f_desc:
                    st.error("Please fill in all the fields before submitting.")
                else:
                    try:
                        attachment_path = None
                        if f_image:
                            upload_res = requests.post(f"{API_URL}/upload/", files={"file": (f_image.name, f_image, f_image.type)})
                            if upload_res.status_code == 200:
                                attachment_path = upload_res.json().get("attachment_path")
                                
                        formatted_details = f"Name: {f_name}, Account: {f_account}, Mobile: {f_mobile}"
                        payload = {
                            "user_details": formatted_details,
                            "description": f_desc,
                            "attachment_path": attachment_path
                        }
                        res = requests.post(f"{API_URL}/complaints/", json=payload, timeout=15)
                        if res.status_code == 200:
                            data = res.json()
                            success_msg = f"Your complaint has been successfully filed under the category **{data['category']}**.\n\nYour Reference ID is: **{data['id']}**.\n\nPlease keep this ID safe to check your status later."
                            st.session_state.messages.append({"role": "assistant", "content": success_msg})
                            
                            urgency = data.get("urgency", "Low")
                            if urgency in ["High", "Critical"]:
                                urgency_msg = f"⚠️ **Urgency Level: {urgency}** - This issue has been prioritized."
                                st.session_state.messages.append({"role": "assistant", "content": urgency_msg})

                            action_taken = data.get("action_taken")
                            if action_taken and action_taken.lower() != "none":
                                action_msg = f"🚨 **Agent Action Completed:** {action_taken}"
                                st.session_state.messages.append({"role": "assistant", "content": action_msg})

                            # Display advice if present
                            if advice:
                                st.session_state.messages.append({"role": "assistant", "content": f"💡 **Next Steps / Advice:**\n{advice}"})
                                
                            # Display uploaded image confirmation
                            if attachment_path:
                                st.session_state.messages.append({"role": "assistant", "content": f"📎 **Image Attached:** Successfully uploaded."})
                                
                            st.session_state.flow_state = "idle"
                            st.rerun()
                        elif res.status_code == 400:
                            data = res.json()
                            fail_msg = f"**Complaint Rejected.**\n{data.get('detail', 'Your request could not be processed.')}"
                            st.session_state.messages.append({"role": "assistant", "content": fail_msg})
                            st.session_state.flow_state = "idle"
                            st.rerun()
                        else:
                            st.error("I'm sorry, there was an issue filing your complaint. Please try again later.")
                            st.session_state.flow_state = "idle"
                    except Exception as e:
                        st.error(f"Could not connect to the backend server. Error: {e}")
                        st.session_state.flow_state = "idle"

# Always render the voice bar at the very bottom of the page content
if st.session_state.flow_state == "collecting_complaint_details":
    audio_input = st.audio_input("🎙️ Speak your details", key=f"mic_{st.session_state.audio_key}")
else:
    # Floating mic button
    audio_input = st.audio_input("🎙️ Voice Message", key=f"mic_{st.session_state.audio_key}")

if audio_input is not None:
    # audio_input behaves like a file uploader in streamlit.
    audio_bytes = audio_input.getvalue()
    audio_hash = hash(audio_bytes)
    if "last_audio_hash" not in st.session_state or st.session_state.last_audio_hash != audio_hash:
        st.session_state.last_audio_hash = audio_hash
        with st.spinner("Transcribing audio..."):
            transcribed_text, user_lang = transcribe_audio(audio_bytes)
            st.session_state.user_language = user_lang
            st.session_state.pending_audio_text = transcribed_text
            st.session_state.audio_key += 1
            st.rerun()
