from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# 1. Redefine the prompt to handle a list of messages (history)
chat_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a video analytics chat assistant. Answer user questions based on the video context."),
    MessagesPlaceholder(variable_name="history"), # This handles the 'messages' list
    ("human", "{question}")
])