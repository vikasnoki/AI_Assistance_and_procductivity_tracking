import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langchain_core.prompts import load_prompt
# Load env variables
load_dotenv()

# Page title
st.title("AI Assistance")

Temp =st.slider("Creativity:",min_value=0.0,value=0.0,max_value=2.0)


# Initialize model
llm = HuggingFaceEndpoint(
    repo_id="openai/gpt-oss-20b",
    temperature=Temp,
    task="text-generation"
)
model = ChatHuggingFace(llm=llm)
#temp = load_prompt('template.json')
# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = [
        SystemMessage(content="Explain as an expert in all fields with requiered analogy and example if needed.")
    ]

# User input
user_input = st.text_input("You:")
token_size = st.number_input("token-size")
if st.button('click'):
    # Process input
    if user_input:
        # Append human message
        st.session_state.messages.append(HumanMessage(content=f"{user_input}.and give the output in range 1 to {token_size} tokens.add recommended wbesites and youtube links related to topic"))

        # Generate AI response
        ai_message = model.invoke(st.session_state.messages)

        # Append AI message
        st.session_state.messages.append(AIMessage(content=ai_message.content))

# Display chat history
for msg in st.session_state.messages:
    if isinstance(msg, HumanMessage):
        st.markdown(f"*You:* {msg.content}")
    elif isinstance(msg, AIMessage):
        st.markdown(f"*AI:* {msg.content}")