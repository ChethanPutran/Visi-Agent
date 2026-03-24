from langchain_core.prompts import PromptTemplate


video_summary_prompt_template = PromptTemplate.from_template(
    """ Based on the following video transcript and visual descriptions,\
        create a comprehensive summary:

        TRANSCRIPT:
        {transcript_text}

        VISUAL DESCRIPTIONS (Key Frames):
        {visual_context}

        Please provide:
        1. A 3-4 sentence overview of the video
        2. Key topics discussed
        3. Main visual elements
        4. Any important actions or events

        Summary:""")
