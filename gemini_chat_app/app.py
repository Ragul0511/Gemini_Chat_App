import streamlit as st
import requests
import base64 # Required to encode image to base64
import json   # For pretty printing JSON in error messages

st.set_page_config(layout="centered") # Set a centered layout for better aesthetics

st.title("🔮 Gemini AI Chat App (Model: 2.5 Flash)")
st.markdown("Ask Gemini questions and optionally include an image!")

# Initialize chat history in session state if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = [] 

# Input for the Gemini API Key - this stays outside the form as it's not cleared on every submission
api_key = st.text_input("🔑 Enter your Gemini API Key", type="password", help="Get your API key from Google AI Studio: https://aistudio.google.com/app/apikey")

# Display previous messages from history
# This section remains above the input form to show the conversation flow
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        for part in message["parts"]:
            if "text" in part:
                st.markdown(part["text"])
            if "inlineData" in part:
                # Decode base64 image and display it
                img_data = base64.b64decode(part["inlineData"]["data"])
                st.image(img_data, caption="User Image", use_column_width=True)

# --- START OF CHANGES: Using st.form for input widgets ---
# Place input widgets inside a Streamlit form for automatic clearing on submit
with st.form("chat_form", clear_on_submit=True):
    # Input for the text prompt
    current_text_prompt = st.text_area(
        "💬 Type your message here...",
        height=68,
        placeholder="e.g., 'Describe this image' or 'What do you see here?'",
        key="user_text_input" # Unique key for this widget
    )

    # Input for image upload
    uploaded_file = st.file_uploader(
        "🖼️ Upload an image (optional)",
        type=["jpg", "jpeg", "png", "webp"],
        key="user_image_input" # Unique key for this widget
    )

    # Submit button for the form
    submit_button = st.form_submit_button("Ask Gemini", use_container_width=True)

# Logic for when the form is submitted
if submit_button:
    # Validate inputs
    if not api_key:
        st.error("Please enter your Gemini API Key to proceed.")
        st.stop() # Stop execution if API key is missing
    
    if not current_text_prompt and not uploaded_file:
        st.warning("Please enter a message or upload an image to ask Gemini.")
        st.stop() # Stop execution if both are empty

    # Define the model to use. Gemini 2.5 Flash supports multimodal input.
    model_name = "gemini-2.5-flash-preview-05-20" # This model is suitable for multimodal inputs
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"

    headers = {"Content-Type": "application/json"}
    
    # Construct the 'parts' for the current user's input
    current_user_parts = []

    if current_text_prompt:
        current_user_parts.append({"text": current_text_prompt})
    
    if uploaded_file:
        image_bytes = uploaded_file.getvalue()
        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        mime_type = uploaded_file.type
        
        supported_mime_types = ["image/jpeg", "image/png", "image/webp"]
        if mime_type not in supported_mime_types:
            st.error(f"Unsupported image format: {mime_type}. Please upload JPG, JPEG, PNG, or WEBP.")
            st.stop()

        current_user_parts.append({
            "inlineData": {
                "mimeType": mime_type,
                "data": base64_image
            }
        })

    # Add the current user message to the session state history FIRST
    st.session_state.messages.append({"role": "user", "parts": current_user_parts})

    # Display the user's message immediately (optional, as the loop above will also display it on rerun)
    # This immediate display is useful for visual feedback before the full page reloads for the API response.
    with st.chat_message("user"):
        for part in current_user_parts:
            if "text" in part:
                st.markdown(part["text"])
            if "inlineData" in part:
                img_data = base64.b64decode(part["inlineData"]["data"])
                st.image(img_data, caption="User Image", use_column_width=True)

    # The payload for the API call will include the entire chat history
    # The Gemini API expects 'contents' to be an array of chat turns.
    payload = {
        "contents": st.session_state.messages # Send the entire conversation history
    }

    # Display a spinner while waiting for the API response
    with st.spinner("Gemini is thinking and processing your request..."):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=120)
            response.raise_for_status() 
            result = response.json()

            if "candidates" in result and result["candidates"]:
                reply_parts = result["candidates"][0]["content"]["parts"]
                reply_text = "".join([part["text"] for part in reply_parts if "text" in part])
                
                # Add Gemini's response to the session state history
                st.session_state.messages.append({"role": "model", "parts": [{"text": reply_text}]})

                # Display Gemini's response
                with st.chat_message("model"):
                    st.markdown(reply_text)
                
                # Inputs are cleared automatically by clear_on_submit=True in st.form
                # No need to call clear_inputs() explicitly here anymore
            else:
                st.error("❌ Error: Gemini API did not return a valid response.")
                st.json(result)
                # If there's an error, remove the last user message to avoid a broken state
                st.session_state.messages.pop() 
        
        except requests.exceptions.Timeout:
            st.error("❌ Request timed out. Gemini took too long to respond. Please try again.")
            st.session_state.messages.pop() # Remove user message on error
        except requests.exceptions.ConnectionError:
            st.error("❌ Network connection error. Please check your internet connection.")
            st.session_state.messages.pop() # Remove user message on error
        except requests.exceptions.HTTPError as e:
            st.error(f"❌ HTTP Error from Gemini API: {e.response.status_code}")
            st.json(e.response.json())
            st.session_state.messages.pop() # Remove user message on error
        except Exception as e:
            st.error(f"❌ An unexpected error occurred: {e}")
            st.session_state.messages.pop() # Remove user message on error

