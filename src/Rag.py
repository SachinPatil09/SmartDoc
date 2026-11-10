#!/usr/bin/env python
# coding: utf-8

# In[ ]:


get_ipython().run_line_magic('pip', '-q install google-api-python-client pandas')


# In[ ]:


# --- Colab: install dependencies ---
get_ipython().system('pip -q install google-api-python-client pandas')

# --- Imports ---
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from IPython.display import FileLink, display
import os
# --- Config (edit these two) ---
VIDEO_ID = "wzssm02u35I"
DEVELOPER_KEY = "AIzaSyCeV897dvqRMJjUQo9kQcm-wJetC9YPbZQ"  # you can move this to a secret if you like

# --- Build client ---
youtube = build("youtube", "v3", developerKey=DEVELOPER_KEY)

def iter_comment_threads(video_id, part="snippet", page_size=100, text_format="html"):
    """Yield ALL commentThreads (top-level comments) with pagination."""
    page_token = None
    while True:
        resp = youtube.commentThreads().list(
            part=part,
            videoId=video_id,
            maxResults=page_size,
            pageToken=page_token,
            textFormat=text_format
        ).execute()
        for item in resp.get("items", []):
            yield item
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

def iter_replies(parent_id, part="snippet", page_size=100, text_format="html"):
    """Yield ALL replies for a given top-level comment with pagination."""
    page_token = None
    while True:
        resp = youtube.comments().list(
            part=part,
            parentId=parent_id,
            maxResults=page_size,
            pageToken=page_token,
            textFormat=text_format
        ).execute()
        for item in resp.get("items", []):
            yield item
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

def fetch_all_comments(video_id, text_format="html"):
    """Return a DataFrame with every top-level comment and reply."""
    rows = []

    # Iterate all threads (top-level comments)
    for thread in iter_comment_threads(video_id, text_format=text_format):
        tlc = thread["snippet"]["topLevelComment"]
        s = tlc["snippet"]

        rows.append({
            "comment_id": tlc["id"],
            "parent_id": None,
            "is_reply": False,
            "author": s.get("authorDisplayName"),
            "author_channel_id": (s.get("authorChannelId") or {}).get("value"),
            "published_at": s.get("publishedAt"),
            "updated_at": s.get("updatedAt"),
            "like_count": s.get("likeCount"),
            "text": s.get("textDisplay") if text_format == "html" else s.get("textOriginal")
        })

        # Iterate all replies for this thread
        parent_id = tlc["id"]
        total_replies = thread["snippet"].get("totalReplyCount", 0) or 0
        if total_replies > 0:
            for reply in iter_replies(parent_id, text_format=text_format):
                rs = reply["snippet"]
                rows.append({
                    "comment_id": reply["id"],
                    "parent_id": parent_id,
                    "is_reply": True,
                    "author": rs.get("authorDisplayName"),
                    "author_channel_id": (rs.get("authorChannelId") or {}).get("value"),
                    "published_at": rs.get("publishedAt"),
                    "updated_at": rs.get("updatedAt"),
                    "like_count": rs.get("likeCount"),
                    "text": rs.get("textDisplay") if text_format == "html" else rs.get("textOriginal")
                })

    return pd.DataFrame(rows, columns=[
        "comment_id", "parent_id", "is_reply",
        "author", "author_channel_id",
        "published_at", "updated_at", "like_count", "text"
    ])

# --- Run & download ---
try:
    # Use "html" to preserve formatting/emojis; use "plainText" to remove HTML.
    df = fetch_all_comments(VIDEO_ID, text_format="html")
    print(f"Fetched rows: {len(df)}")
    # Save CSV with UTF-8 BOM so Excel handles Unicode nicely
    out_name = f"{VIDEO_ID}_comments_full.csv"
    df.to_csv(out_name, index=False, encoding="utf-8-sig")
    # Trigger browser download in Colab
    print("Saved to:", os.path.abspath(out_name))
    display(FileLink(out_name))
except HttpError as e:
    # Helpful error messages (e.g., comments disabled, invalid key, quota)
    print("YouTube API error:")
    try:
        print(e.error_details)
    except Exception:
        print(e)
except Exception as e:
    print("Unexpected error:", e)


# In[ ]:


get_ipython().run_line_magic('pip', 'install langchain_community langchainhub chromadb langchain langchain-openai beautifulsoup4')


# In[ ]:


import os
os.environ["GROQ_API_KEY"] = "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"


# In[ ]:


from langchain_community.document_loaders import CSVLoader

loader = CSVLoader(
    file_path="wzssm02u35I_comments_full.csv",
    encoding="utf-8"  # Specify UTF-8 encoding
)
docs = loader.load()

print(f"Loaded {len(docs)} documents from CSV")
print("\nFirst document:")
print(docs[0])


# In[ ]:


# Build threaded documents so each top-level comment includes its replies
import pandas as pd
from langchain_core.documents import Document

raw_df = pd.read_csv("wzssm02u35I_comments_full.csv")

# Normalize types
raw_df["is_reply"] = raw_df["is_reply"].astype(bool)

# thread_id = parent_id for replies, else comment_id
thread_id = raw_df.apply(lambda r: r["parent_id"] if r["is_reply"] else r["comment_id"], axis=1)
raw_df["thread_id"] = thread_id

thread_docs = []
for tid, g in raw_df.sort_values(["thread_id", "published_at"]).groupby("thread_id"):
    lines = []
    for _, r in g.iterrows():
        cid = r["comment_id"]
        who = r["author"]
        when = r["published_at"]
        txt = r["text"]
        lines.append(f"[{cid} {who} {when}] {txt}")
    content = (
        f"Thread: {tid}\n" + "\n".join(lines)
    )
    # Use the top-level author as metadata if present
    top_level = g[g["is_reply"] == False].head(1)
    meta = {
        "thread_id": tid,
        "top_level_comment_id": top_level["comment_id"].iloc[0] if len(top_level) else tid,
        "source": "DBMPXJJfQEA_comments_full.csv",
    }
    thread_docs.append(Document(page_content=content, metadata=meta))

# Replace docs with threaded docs
docs = thread_docs
print(f"Built {len(docs)} threaded documents.")


# In[ ]:


from langchain_text_splitters import RecursiveCharacterTextSplitter

# Use larger chunks so a whole thread (question + replies) stays together
text_splitter = RecursiveCharacterTextSplitter(chunk_size = 4000, chunk_overlap = 200)
splits = text_splitter.split_documents(docs)


# In[ ]:


print(splits[0])
print(splits[1])
print(splits[2])


# In[ ]:


print(len(splits))


# In[ ]:


pip install langchain-groq


# In[ ]:


from langchain_groq import ChatGroq


# In[ ]:


get_ipython().run_line_magic('pip', 'install sentence-transformers')


# In[ ]:


from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# Fast, small embedding model
hf_emb = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
# Rebuild store from threaded, larger chunks
vectorstore = Chroma.from_documents(documents=splits, embedding=hf_emb)


# In[ ]:


print(vectorstore._collection.get())


# In[ ]:


print("\nCollection 1 - ", vectorstore._collection.get(ids=['28651d9a-ab51-41f8-ab83-e68285623c4e'], include=["embeddings", "documents"]))
print("\nCollection 2 - ", vectorstore._collection.get(ids=['054dee19-19ed-4574-bc51-511060fd707a'], include=["embeddings", "documents"]))
print("\nCollection 3 - ", vectorstore._collection.get(ids=['2fd71cb4-835a-43c5-b920-b7e1be51c450'], include=["embeddings", "documents"]))


# In[ ]:


# Hybrid retriever: MMR vector search + keyword fallback for error codes
import re
from langchain_core.runnables import RunnableLambda

KEYWORD_PATTERN = re.compile(r"\b(?:403|429|quota|access|error(?:s)?|ada\s*002)\b", re.IGNORECASE)

def hybrid_retrieve(query: str):
    # Vector search (MMR)
    vec_docs = vectorstore.max_marginal_relevance_search(query, k=12, fetch_k=50, lambda_mult=0.5)
    # Keyword fallback over chunks
    keyword_hits = []
    if KEYWORD_PATTERN.search(query or ""):
        q_terms = set(t.lower() for t in KEYWORD_PATTERN.findall(query))
        for d in splits:
            text = d.page_content.lower()
            if any(t in text for t in q_terms):
                keyword_hits.append(d)
    # Merge & dedupe
    merged = []
    seen = set()
    for d in (vec_docs + keyword_hits):
        key = (d.metadata.get("thread_id"), d.page_content[:120])
        if key in seen:
            continue
        seen.add(key)
        merged.append(d)
    return merged[:15]

retriever = RunnableLambda(lambda q: hybrid_retrieve(q))


# In[ ]:


from langchain_core.prompts import ChatPromptTemplate

system_instructions = (
    "You are an assistant that answers strictly and only using the provided YouTube comments. "
    "Do not add outside knowledge. If the comments conflict, say so and present both sides. "
    "Always cite exact comment IDs and authors for each claim using the format [comment_id @author]. "
    "If the answer is not in the comments, say 'Not found in comments.'"
)

prompt = ChatPromptTemplate.from_messages([
    ("system", system_instructions),
    ("human", (
        "Question:\n{question}\n\n"
        "Comments context (subset):\n{context}\n\n"
        "Instruction:\n"
        "- Identify the relevant thread(s) that contain the question and any replies.\n"
        "- Extract any explicit solutions, workarounds, or confirmations from replies in the same thread.\n"
        "- Respond with concise bullets under 'Causes' and 'Solutions'. If no solution is present in replies, state 'No solution found in replies.'\n"
        "- Cite each item with [comment_id @author]."
    ))
])


# In[ ]:


from langchain_groq import ChatGroq
llm = ChatGroq(model="openai/gpt-oss-20b", api_key="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")


# In[ ]:


from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate


# In[ ]:


def format_docs(docs):
  # Keep only the essential fields in each chunk to help retrieval grounding
  cleaned = []
  for doc in docs:
    cleaned.append(doc.page_content)
  return "\n---\n".join(cleaned)


# In[ ]:


dag = ({"context" : retriever | format_docs, "question" : RunnablePassthrough()}
       | prompt
       | llm
       | StrOutputParser())

rag_chain = dag


# In[ ]:


print(rag_chain.invoke("please give me a summary"))


# In[25]:


get_ipython().system('jupyter nbconvert --to script Rag.ipynb')


# In[26]:


get_ipython().system('pwd')
get_ipython().system('ls')


# In[28]:


from google.colab import drive
drive.mount('/content/drive')


# In[32]:


get_ipython().run_line_magic('cd', '/content/drive/folders/1R247lyfBPa-pjhxOyeB-xRl7h--1x4x8')
get_ipython().system('ls')


# In[33]:


get_ipython().system('jupyter nbconvert --to script Rag.ipynb')

