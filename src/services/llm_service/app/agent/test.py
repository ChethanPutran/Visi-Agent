from langchain_community.document_loaders import TextLoader
from langchain_core.vectorstores import VectorStore
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
# from langchain_community.vectorstores import FAISS,Chroma
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from langchain_text_splitters import RecursiveCharacterTextSplitter
# from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.runnables import RunnableParallel,RunnablePassthrough, RunnableLambda
import os
import markdown


def generate_transcript(video_id: str, language: str = "en"):
    """Generate transcript for a YouTube video given its ID."""
    try:
        fetcher = YouTubeTranscriptApi()
        transcript = fetcher.list(video_id).find_transcript([language]).fetch()
        if transcript.is_generated:
             return transcript.snippets
    except TranscriptsDisabled:
        return None

def get_chunks(docs):
    # Split the transcript into chunks
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.create_documents([docs])

    print(f"Total chunks created: {len(chunks)}")
    return chunks

def create_vector_store(docs, embeddings, PERSIST_DIR="data/vectors", COLLECTION_NAME="default_collection"):
    # Create and persist Chroma vector store
    vectordb = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=PERSIST_DIR,
        collection_name=COLLECTION_NAME
    )
    
    print(f"Vector database stored successfully in {PERSIST_DIR}")

def load_vector_store(embedding_model,persist_directory: str = "data/vectors", collection_name: str = "default_collection",) -> VectorStore:
    vectordb = Chroma(embedding_function=embedding_model,persist_directory=persist_directory, collection_name=collection_name)
    return vectordb


def get_response_from_model(model: ChatGoogleGenerativeAI, prompt: str):
    res = model.invoke(prompt).content

    print("Response from the model:")
    
    if isinstance(res, str):
        print(res)
        exit(0)
    if isinstance(res, list):
        for r in res:
            if isinstance(r, dict) and 'text' in r:
                print(r['text'])

if __name__ == "__main__":
    # Get the video transcript
    transcripts = generate_transcript("qrsNX1Rwle0")
    entire_transcript = ""
    if transcripts:
        # print(transcripts[:4])  # Example video ID
        entire_transcript = " ".join([segment.text for segment in transcripts])
    else:
        print("Transcripts are disabled for this video.")

    chunks = get_chunks(entire_transcript)
    # print(chunks[:2])  # Print first two chunks as a sample

    # embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")
    embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    create_vector_store(
        docs = chunks,
        embeddings = embedding_model,
        PERSIST_DIR = "data/vectors/youtube_qrsNX1Rwle0",
        COLLECTION_NAME = "youtube_qrsNX1Rwle0_collection"
    )

    # vector_store = FAISS.from_documents(chunks, embedding_model)
    # # Create a retriever from the vector store
    retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 3})


    db = load_vector_store(
        persist_directory="data/vectors/youtube_qrsNX1Rwle0",
        collection_name="youtube_qrsNX1Rwle0_collection",
        embedding_model=embedding_model
    )
    retriever = db.as_retriever(search_type="similarity", search_kwargs={"k": 3})

    prompt_template = PromptTemplate(
        template="""
        You are an AI assistant helping with video content. Use the following
        context to answer the question.

        Context: {context}

        Question: {question}
        Answer in detail.
        """,
        input_variables=["question", "context"]
    )

    # prompt_template.save("data/prompts/video_qa_prompt_template.json")

    # prompt_template = PromptTemplate.from_file("data/prompts/video_qa_prompt_template.json")
    # Example query to test the retriever

    question = "What is the main topic discussed in the video?"
    # retried_docs = retriever.invoke(question)

    # print(f"Retrieved {len(retried_docs)} documents:")
    # # print(retried_docs)

    def format_doc(retried_docs):
        return  "\n".join([doc.page_content for doc in retried_docs])

    # prompt = prompt_template.invoke(input={
    #     "question": question, "context": context})


    # print("Final Prompt to the model:")
    # print(prompt)
    

    llm = ChatGoogleGenerativeAI(
        model="gemini-3-flash-preview",
        temperature=1.0,  # Gemini 3.0+ defaults to 1.0
        max_tokens=None,
        timeout=None,
        max_retries=2,
        # other params...
    )

    input_chain = RunnableParallel(
        {
            "context": retriever | RunnableLambda(format_doc),
            "question": RunnablePassthrough()
        }
    )

    parser = StrOutputParser()

    main_chain = input_chain | prompt_template | llm | parser

    md_text = main_chain.invoke(question)

    # # Convert to HTML
    html_content = markdown.markdown(md_text)

    print(html_content)

    # # Create Chain

    # prompt_template | model | parser


    

    # import base64
    # from langchain.messages import HumanMessage
    # from langchain_google_genai import ChatGoogleGenerativeAI

    # model = ChatGoogleGenerativeAI(model="gemini-3-pro-preview")

    # video_bytes = open("path/to/your/video.mp4", "rb").read()
    # video_base64 = base64.b64encode(video_bytes).decode("utf-8")
    # mime_type = "video/mp4"

    # message = HumanMessage(
    #     content=[
    #         {"type": "text", "text": "Describe what's in this video in a sentence."},
    #         {
    #             "type": "video",
    #             "base64": video_base64,
    #             "mime_type": mime_type,
    #         },
    #     ]
    # )
    # response = model.invoke([message])

