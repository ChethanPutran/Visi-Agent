from .chat import chat_prompt
from .video_desc import video_desc_extract_prompt_template
from .video_summary import video_summary_prompt_template
from .agent_prompt import agent_prompt


__all__ = [
    "chat_prompt",
    "video_desc_extract_prompt_template",
    "video_summary_prompt_template",
    "agent_prompt"

]