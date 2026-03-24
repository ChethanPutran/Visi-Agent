from langchain_core.prompts import PromptTemplate

video_desc_extract_prompt_template = PromptTemplate.from_template(
    """You are a video analytics agent. I'll show you several video frames with their timestamps.
        For each frame, describe what you see in 1-2 sentences. Focus on key objects, actions, 
        and any text you can read. Be concise but informative."""
        )