import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(layout="centered")

st.markdown("""
<style>
/* Seamless Voice Input styling */
[data-testid="stAudioInput"] {
    border-radius: 15px 15px 0 0;
    background-color: #1e1e24 !important;
    border: 1px solid #2A2A35 !important;
    border-bottom: none !important;
    padding: 10px 15px !important;
    margin-bottom: -15px;
    z-index: 10;
}
.stChatInputContainer {
    border-radius: 0 0 15px 15px !important;
    background-color: #1e1e24 !important;
    border: 1px solid #2A2A35 !important;
    border-top: 1px solid #333 !important;
    z-index: 11;
}
[data-testid="stBottom"] {
    background-color: transparent !important;
}
</style>
""", unsafe_allow_html=True)

st.title("Test App")
st.write("Hello")

audio_input = st.audio_input("Voice Input")
chat_input = st.chat_input("Chat Input")

components.html("""
<script>
    const parentDoc = window.parent.document;
    const audioInput = parentDoc.querySelector('[data-testid="stAudioInput"]');
    const bottomContainer = parentDoc.querySelector('[data-testid="stBottom"] > div');
    
    // Check if we need to move it
    if (audioInput && bottomContainer) {
        // Move audio block up to bottom container
        const audioBlock = audioInput.parentElement; // might need to move the wrapper
        if (audioBlock.parentElement !== bottomContainer) {
            bottomContainer.insertBefore(audioBlock, bottomContainer.firstChild);
        }
    }
</script>
""", height=0, width=0)

