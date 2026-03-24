from langchain.messages import SystemMessage

agent_prompt = SystemMessage(
            "You are a video analytics agent. Use the provided tools to answer questions about the video\
            content, summary, and visual patterns."
        )