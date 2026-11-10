#!/usr/bin/env python
# coding: utf-8

# In[1]:


get_ipython().run_line_magic('pip', '-q install youtube-transcript-api pandas')


# In[2]:


from youtube_transcript_api import YouTubeTranscriptApi
import pandas as pd
from IPython.display import FileLink, display
import os


# In[3]:


VIDEO_ID = "wzssm02u35I"


# In[4]:


def fetch_transcript_to_csv(video_id):
    """Fetch transcript and save to CSV"""
    try:
        # Fetch transcript using current API (v1.2+)
        api_client = YouTubeTranscriptApi()
        segments_list = api_client.fetch(video_id).to_raw_data()

        # Convert to DataFrame
        df = pd.DataFrame(segments_list)
        df['video_id'] = video_id

        # Reorder columns
        df = df[['video_id', 'start', 'duration', 'text']]

        # Save to CSV
        csv_path = f"{video_id}_transcript.csv"
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")

        print(f"Fetched segments: {len(df)}")
        print(f"Saved to: {os.path.abspath(csv_path)}")
        display(FileLink(csv_path))

        return df

    except Exception as e:
        print(f"Error: {e}")
        return None

# Fetch and save transcript
transcript_df = fetch_transcript_to_csv(VIDEO_ID)
if transcript_df is not None:
    print("\nFirst 5 segments:")
    print(transcript_df.head())


# In[5]:


import os
os.environ["GROQ_API_KEY"] = "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"


# In[6]:


get_ipython().run_line_magic('pip', 'install langchain_community langchainhub chromadb langchain langchain-openai beautifulsoup4')


# In[7]:


from langchain_community.document_loaders import CSVLoader

loader = CSVLoader(
    file_path="wzssm02u35I_transcript.csv",
    encoding="utf-8"  # Specify UTF-8 encoding
)
docs = loader.load()

print(f"Loaded {len(docs)} documents from CSV")
print("\nFirst document:")
print(docs[0])


# In[9]:


from langchain_text_splitters import RecursiveCharacterTextSplitter

# Use larger chunks so a whole thread (question + replies) stays together
text_splitter = RecursiveCharacterTextSplitter(chunk_size = 4000, chunk_overlap = 200)
splits = text_splitter.split_documents(docs)


# In[10]:


print(splits[0])
print(splits[1])
print(splits[2])


# In[11]:


pip install langchain-groq


# In[12]:


from langchain_groq import ChatGroq


# In[13]:


get_ipython().run_line_magic('pip', 'install sentence-transformers')


# In[14]:


from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# Fast, small embedding model
hf_emb = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
# Rebuild store from threaded, larger chunks
vectorstore = Chroma.from_documents(documents=splits, embedding=hf_emb)


# In[15]:


print(vectorstore._collection.get())


# In[16]:


print("\nCollection 1 - ", vectorstore._collection.get(ids=['28651d9a-ab51-41f8-ab83-e68285623c4e'], include=["embeddings", "documents"]))
print("\nCollection 2 - ", vectorstore._collection.get(ids=['054dee19-19ed-4574-bc51-511060fd707a'], include=["embeddings", "documents"]))
print("\nCollection 3 - ", vectorstore._collection.get(ids=['2fd71cb4-835a-43c5-b920-b7e1be51c450'], include=["embeddings", "documents"]))


# In[17]:


from langchain_core.runnables import RunnableLambda

def simple_retrieve(query: str):
    """Simple MMR-based retrieval for transcript chunks"""
    # Use MMR (Maximal Marginal Relevance) for diverse, relevant results
    docs = vectorstore.max_marginal_relevance_search(
        query,
        k=5,           # Return top 5 chunks
        fetch_k=20,    # Consider top 20 for diversity
        lambda_mult=0.5  # Balance relevance vs diversity
    )
    return docs

retriever = vectorstore.as_retriever(
    search_type="mmr",
    search_kwargs={"k": 5, "fetch_k": 20, "lambda_mult": 0.5}
)


# In[18]:


from langchain_core.prompts import ChatPromptTemplate

system_instructions = (
    "You are an assistant that answers strictly and only using the provided YouTube transcript. "
    "Do not add outside knowledge. "
    "Always cite exact timestamps for each claim using the format [timestamp]. "
    "If the answer is not in the transcript, say 'Not found in transcript.'"
)

prompt = ChatPromptTemplate.from_messages([
    ("system", system_instructions),
    ("human", (
        "Question:\\n{question}\\n\\n"
        "Transcript context (subset):\\n{context}\\n\\n"
        "Instruction:\\n"
        "- Identify the relevant time segments that contain information about the question.\\n"
        "- Extract key points, explanations, or examples from the transcript.\\n"
        "- Respond with clear, concise answers.\\n"
        "- Cite each point with [timestamp]."
    ))
])


# In[19]:


from langchain_groq import ChatGroq
llm = ChatGroq(model="openai/gpt-oss-20b", api_key="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")


# In[20]:


from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate


# In[21]:


def format_docs(docs):
    """Format retrieved documents for context"""
    return "\\n\\n".join(doc.page_content for doc in docs)


# In[22]:


dag = ({"context" : retriever | format_docs, "question" : RunnablePassthrough()}
       | prompt
       | llm
       | StrOutputParser())

rag_chain = dag


# In[24]:


print(rag_chain.invoke("what is rag model"))


# In[26]:


get_ipython().run_line_magic('cd', '/content/drive/MyDrive/Colab Notebooks/')
get_ipython().system('ls')


# In[27]:


from google.colab import drive
drive.mount('/content/drive')


# In[ ]:




