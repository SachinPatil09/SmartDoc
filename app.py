import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from youtube_transcript_api import YouTubeTranscriptApi
from langchain_community.document_loaders import CSVLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
import re
from urllib.parse import urlparse, parse_qs

# Load environment variables
load_dotenv()

# API Keys from .env
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or ""
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY") or ""
GROQ_API_KEY = os.getenv("GROQ_API_KEY") or ""

# Page configuration
st.set_page_config(
    page_title="SmartDoc",
    page_icon="🎥",
    layout="wide"
)

# Global styles
st.markdown("""
<style>
/* Page tweaks */
.block-container {
  padding-top: 2rem;
  padding-bottom: 2rem;
}

/* Fancy buttons */
.stButton > button {
  background: linear-gradient(135deg, #6b73ff 0%, #000dff 100%);
  color: white;
  border: 0;
  border-radius: 10px;
  padding: 0.6rem 1rem;
  box-shadow: 0 8px 20px rgba(0, 13, 255, 0.25);
}
.stButton > button:hover {
  filter: brightness(1.05);
  box-shadow: 0 10px 24px rgba(0, 13, 255, 0.32);
}

/* Inputs */
.stTextInput > div > div > input, .stNumberInput input {
  border-radius: 10px;
}

/* Hero card */
.hero {
  background: radial-gradient(1250px circle at 10% 20%, rgba(81, 125, 255, 0.15) 0%, rgba(81, 125, 255, 0.03) 35%, rgba(0,0,0,0) 60%),
              linear-gradient(180deg, rgba(0, 13, 255, 0.06), rgba(0,0,0,0));
  border: 1px solid rgba(81,125,255,0.2);
  border-radius: 16px;
  padding: 24px 24px 18px 24px;
  margin-bottom: 16px;
}
.badge {
  display: inline-block;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(0, 13, 255, 0.08);
  color: #0010b8;
  font-size: 12px;
  border: 1px solid rgba(0, 13, 255, 0.18);
}

/* Cards */
.card {
  background: white;
  border: 1px solid rgba(0,0,0,0.07);
  border-radius: 14px;
  padding: 16px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.04);
}

/* Expander style */
details summary {
  list-style: none;
}
.streamlit-expanderHeader {
  font-weight: 600;
}

/* Comment bubble */
.comment {
  background: #f8faff;
  border: 1px solid rgba(0, 13, 255, 0.1);
  border-radius: 12px;
  padding: 10px 12px;
  margin: 6px 0;
}
.comment .author {
  color: #0010b8;
  font-weight: 600;
  margin-right: 6px;
}
.comment .text {
  color: #1f2633;
}
</style>
""", unsafe_allow_html=True)

# Hero header - Modern Design
st.markdown(
    """
    <div class="hero">
      <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
        <div class="badge" style="background: rgba(107, 115, 255, 0.12); color: #6b73ff;">🚀 Context-Aware AI</div>
      </div>
      <h1 style="margin: 0; font-size: 2.5rem; font-weight: 700; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">
        SmartDoc
      </h1>
      <p style="margin: 8px 0 0 0; font-size: 1.1rem; color:#4a5568; font-weight: 500;">
        AI-Powered YouTube Learning Assistant
      </p>
      <p style="margin: 8px 0 0 0; color:#718096; font-size: 0.95rem;">
        📹 Analyze videos · 💬 Explore comments · 📄 Connect documents · 🤖 Ask anything
      </p>
    </div>
    """,
    unsafe_allow_html=True
)

# Sidebar (minimal)
with st.sidebar:
    st.header("Configuration")
    st.caption("Use the input in the center to load a video.")

# Centered YouTube input and Load button
center_a, center_b, center_c = st.columns([1, 2, 1])
with center_b:
    st.markdown("#### Paste a YouTube URL or ID")
    video_input = st.text_input(
        "YouTube URL or ID",
        value="https://www.youtube.com/watch?v=wzssm02u35I",
        placeholder="e.g., https://www.youtube.com/watch?v=...",
        label_visibility="collapsed",
        key="center_video_input"
    )
    load_clicked = st.button("🔄 Load Data", type="primary", use_container_width=True)
status_placeholder = st.empty()

# Initialize session state
if 'vectorstore' not in st.session_state:
    st.session_state.vectorstore = None
if 'rag_chain' not in st.session_state:
    st.session_state.rag_chain = None
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'last_loaded_data_type' not in st.session_state:
    st.session_state.last_loaded_data_type = None
if 'prompt_mode' not in st.session_state:
    st.session_state.prompt_mode = None
if 'comments_df' not in st.session_state:
    st.session_state.comments_df = None
if 'transcript_df' not in st.session_state:
    st.session_state.transcript_df = None
if 'comments_vectorstore' not in st.session_state:
    st.session_state.comments_vectorstore = None
if 'comments_chain' not in st.session_state:
    st.session_state.comments_chain = None
if 'transcript_vectorstore' not in st.session_state:
    st.session_state.transcript_vectorstore = None
if 'transcript_chain' not in st.session_state:
    st.session_state.transcript_chain = None
if 'user_comments' not in st.session_state:
    st.session_state.user_comments = []
if 'video_id' not in st.session_state:
    st.session_state.video_id = None
if 'combined_chain' not in st.session_state:
    st.session_state.combined_chain = None
if 'show_threads_count' not in st.session_state:
    st.session_state.show_threads_count = 10
if 'comment_search_query' not in st.session_state:
    st.session_state.comment_search_query = ""
if 'docs_vectorstore' not in st.session_state:
    st.session_state.docs_vectorstore = None
if 'docs_chain' not in st.session_state:
    st.session_state.docs_chain = None
if 'uploaded_docs' not in st.session_state:
    st.session_state.uploaded_docs = []
if 'doc_video_mapping' not in st.session_state:
    st.session_state.doc_video_mapping = {}  # Maps video_id to list of docs

# Function to fetch YouTube transcript
@st.cache_data(show_spinner=False)
def fetch_transcript(video_id):
    """Fetch transcript and return as DataFrame"""
    try:
        api_client = YouTubeTranscriptApi()
        segments_list = api_client.fetch(video_id).to_raw_data()
        df = pd.DataFrame(segments_list)
        df['video_id'] = video_id
        df = df[['video_id', 'start', 'duration', 'text']]
        csv_path = f"{video_id}_transcript.csv"
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        return df, csv_path
    except Exception as e:
        st.error(f"Error fetching transcript: {e}")
        return None, None

# Function to fetch YouTube comments
@st.cache_data(show_spinner=False)
def fetch_comments(video_id):
    """Fetch all comments (including replies) and return as DataFrame"""
    try:
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        rows = []
        
        # Fetch top-level comments
        page_token = None
        while True:
            resp = youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=100,
                pageToken=page_token,
                textFormat="html"
            ).execute()
            
            for item in resp.get("items", []):
                tlc = item["snippet"]["topLevelComment"]
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
                    "text": s.get("textDisplay")
                })
                
                # Fetch replies
                parent_id = tlc["id"]
                total_replies = item["snippet"].get("totalReplyCount", 0) or 0
                if total_replies > 0:
                    reply_page_token = None
                    while True:
                        reply_resp = youtube.comments().list(
                            part="snippet",
                            parentId=parent_id,
                            maxResults=100,
                            pageToken=reply_page_token,
                            textFormat="html"
                        ).execute()
                        
                        for reply in reply_resp.get("items", []):
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
                                "text": rs.get("textDisplay")
                            })
                        
                        reply_page_token = reply_resp.get("nextPageToken")
                        if not reply_page_token:
                            break
            
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        
        df = pd.DataFrame(rows)
        csv_path = f"{video_id}_comments_full.csv"
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        return df, csv_path
    except HttpError as e:
        st.error(f"YouTube API error: {e}")
        return None, None
    except Exception as e:
        st.error(f"Error fetching comments: {e}")
        return None, None

# Function to build threaded documents from comments
def build_threaded_docs(csv_path):
    """Build threaded documents from comments CSV"""
    raw_df = pd.read_csv(csv_path)
    raw_df["is_reply"] = raw_df["is_reply"].astype(bool)
    
    thread_id = raw_df.apply(
        lambda r: r["parent_id"] if r["is_reply"] else r["comment_id"], 
        axis=1
    )
    raw_df["thread_id"] = thread_id
    
    thread_docs = []
    for tid, g in raw_df.sort_values(["thread_id", "published_at"]).groupby("thread_id"):
        lines = []
        for _, r in g.iterrows():
            cid = r["comment_id"]
            who = r["author"]
            when = r["published_at"]
            txt = r["text"]
            lines.append(f"[{cid} @{who} {when}] {txt}")
        
        content = f"Thread: {tid}\n" + "\n".join(lines)
        top_level = g[g["is_reply"] == False].head(1)
        meta = {
            "thread_id": tid,
            "top_level_comment_id": top_level["comment_id"].iloc[0] if len(top_level) else tid,
            "source": csv_path,
        }
        thread_docs.append(Document(page_content=content, metadata=meta))
    
    return thread_docs

# Function to create RAG chain
def create_rag_chain(docs, data_type, persist_directory=None):
    """Create RAG chain with vectorstore and LLM"""
    # Split documents
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=4000, chunk_overlap=200)
    splits = text_splitter.split_documents(docs)
    
    # Create embeddings and vectorstore
    hf_emb = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectorstore = None
    try:
        if persist_directory and os.path.isdir(persist_directory) and os.listdir(persist_directory or "."):
            vectorstore = Chroma(persist_directory=persist_directory, embedding=hf_emb)
        else:
            vectorstore = Chroma.from_documents(documents=splits, embedding=hf_emb, persist_directory=persist_directory)
            if persist_directory:
                vectorstore.persist()
    except Exception:
        vectorstore = Chroma.from_documents(documents=splits, embedding=hf_emb)
    
    # Create retriever
    retriever = vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 5, "fetch_k": 20, "lambda_mult": 0.5}
    )
    
    # Normalize and create prompt based on data type
    normalized_type = (data_type or "").strip().lower()
    if normalized_type == "comments":
        system_instructions = (
            "You are an assistant that answers strictly and only using the provided YouTube comments. "
            "Do not add outside knowledge. If the comments conflict, say so and present both sides. "
            "Always cite exact comment IDs and authors for each claim using the format [comment_id @author]. "
            "If the answer is not in the comments, say 'Not found in comments.'"
        )
        human_message = (
            "Question:\n{question}\n\n"
            "Comments context (subset):\n{context}\n\n"
            "Instruction:\n"
            "- Identify the relevant thread(s) that contain the question and any replies.\n"
            "- Extract any explicit solutions, workarounds, or confirmations from replies in the same thread.\n"
            "- Respond with concise bullets under 'Causes' and 'Solutions'. If no solution is present in replies, state 'No solution found in replies.'\n"
            "- Cite each item with [comment_id @author]."
        )
    else:  # Transcript
        system_instructions = (
            "You are an assistant that answers strictly and only using the provided YouTube transcript. "
            "Do not add outside knowledge. "
            "Always cite exact timestamps for each claim using the format [timestamp]. "
            "If the answer is not in the transcript, say 'Not found in transcript.'"
        )
        human_message = (
            "Question:\n{question}\n\n"
            "Transcript context (subset):\n{context}\n\n"
            "Instruction:\n"
            "- Identify the relevant time segments that contain information about the question.\n"
            "- Extract key points, explanations, or examples from the transcript.\n"
            "- Respond with clear, concise answers.\n"
            "- Cite each point with [timestamp]."
        )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_instructions),
        ("human", human_message)
    ])
    
    # Create LLM - Using Llama 3.3 70B for better performance
    if not GROQ_API_KEY:
        st.warning("Missing GROQ_API_KEY. Set it in your .env file.")
    llm = ChatGroq(model="openai/gpt-oss-20b", api_key=GROQ_API_KEY or "")
    
    # Create RAG chain
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)
    
    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    
    prompt_mode = "Comments" if normalized_type == "comments" else "Transcript"
    return vectorstore, rag_chain, prompt_mode

# Build a combined chain that can use both comments and transcript
def create_combined_chain(comments_vs: Chroma | None, transcript_vs: Chroma | None, docs_vs: Chroma | None = None):
    if not comments_vs and not transcript_vs and not docs_vs:
        return None

    def comments_retrieve(query: str):
        if not comments_vs:
            return []
        return comments_vs.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 5, "fetch_k": 20, "lambda_mult": 0.5}
        ).invoke(query)

    def transcript_retrieve(query: str):
        if not transcript_vs:
            return []
        return transcript_vs.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 5, "fetch_k": 20, "lambda_mult": 0.5}
        ).invoke(query)

    def docs_retrieve(query: str):
        if not docs_vs:
            return []
        return docs_vs.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 5, "fetch_k": 20, "lambda_mult": 0.5}
        ).invoke(query)

    def merge_context(query: str):
        comments_docs = comments_retrieve(query)
        transcript_docs = transcript_retrieve(query)
        docs_docs = docs_retrieve(query)
        merged = []
        seen = set()
        for source_tag, docs in (("COMMENTS", comments_docs), ("TRANSCRIPT", transcript_docs), ("DOCS", docs_docs)):
            for d in docs:
                key = (source_tag, d.metadata.get("thread_id") or "", d.page_content[:160])
                if key in seen:
                    continue
                seen.add(key)
                tagged = Document(
                    page_content=f"[{source_tag}]\n{d.page_content}",
                    metadata=d.metadata
                )
                merged.append(tagged)
        # If there is no docs vectorstore available at all, make this explicit in the context
        if not docs_vs:
            merged.append(Document(page_content="[DOCS]\nNo docs Uploaded", metadata={}))
        return merged

    def format_merged(docs):
        return "\n\n-----\n\n".join(doc.page_content for doc in docs)

    if docs_vs:
        system_instructions = (
            "You are analyzing multiple sources in the context of a specific YouTube video.\n\n"
            "Available sources:\n"
            "- [COMMENTS]: YouTube discussions, questions, and community feedback\n"
            "- [TRANSCRIPT]: Video's spoken content with timestamps\n"
            "- [DOCS]: Uploaded documents related to the video (code, slides, documentation, notes)\n\n"
            "Your analysis approach:\n"
            "1. **Comments First**: Prioritize answers from comments when they directly address the query\n"
            "2. **Video Context**: Use transcript to understand what was explained and when\n"
            "3. **Document Enhancement**: Use docs to provide additional examples, details, or clarifications\n"
            "4. **Cross-Reference**: Connect information across all three sources\n\n"
            "Special considerations for DOCS:\n"
            "- Identify which parts of docs relate to specific video timestamps\n"
            "- Note if docs provide examples not shown in the video\n"
            "- Highlight discrepancies between docs and video explanations\n"
            "- Check if comments reference or discuss the documentation\n\n"
            "Citation format:\n"
            "- Comments: [comment_id @author]\n"
            "- Transcript: [timestamp] or [MM:SS]\n"
            "- Documents: [source: filename]\n"
            "- Cross-reference: [source: filename] discusses topic at [timestamp]\n\n"
            "Always provide context-aware answers that show relationships between sources."
        )
        human_message = (
            "Question:\n{question}\n\n"
            "Context (from comments, transcript, and docs):\n{context}\n\n"
            "Instructions:\n"
            "- Analyze the question considering all three sources\n"
            "- Start with what comments reveal (community discussions, issues, solutions)\n"
            "- Reference video timestamps to show where topics are explained\n"
            "- Use documents to provide additional depth, examples, or clarifications\n"
            "- Show connections: e.g., 'The code in [source: example.py] implements what was explained at [05:30]'\n"
            "- Note gaps: if docs don't cover something from the video, or vice versa\n"
            "- Keep answers structured and well-cited with all sources properly attributed"
        )
    else:
        system_instructions = (
            "You are analyzing multiple sources in the context of a specific YouTube video.\n\n"
            "Available sources:\n"
            "- [COMMENTS]: YouTube discussions, questions, and community feedback\n"
            "- [TRANSCRIPT]: Video's spoken content with timestamps\n"
            "- [DOCS]: No docs uploaded\n\n"
            "Your analysis approach:\n"
            "1. **Comments First**: Prioritize answers from comments when they directly address the query\n"
            "2. **Video Context**: Use transcript to understand what was explained and when\n"
            "3. No document enhancement: there are no docs uploaded\n"
            "4. **Cross-Reference**: Connect information across the available sources\n\n"
            "Citation format:\n"
            "- Comments: [comment_id @author]\n"
            "- Transcript: [timestamp] or [MM:SS]\n\n"
            "Always provide context-aware answers focusing on comments and transcript."
        )
        human_message = (
            "Question:\n{question}\n\n"
            "Context (from comments and transcript):\n{context}\n\n"
            "Instructions:\n"
            "- Analyze the question considering the available sources\n"
            "- Start with what comments reveal (community discussions, issues, solutions)\n"
            "- Reference video timestamps to show where topics are explained\n"
            "- No docs uploaded; ignore document enhancement and document citations\n"
            "- Show connections between comments and transcript\n"
            "- Note gaps: if transcript doesn't cover something from comments, or vice versa\n"
            "- Keep answers structured and well-cited for the available sources"
        )
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_instructions),
        ("human", human_message)
    ])
    llm = ChatGroq(model="openai/gpt-oss-20b", api_key=GROQ_API_KEY or "")
    rag_chain = (
        {"context": RunnablePassthrough() | merge_context | format_merged, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    return rag_chain

# Utility to strip simple HTML tags from YouTube comment text
def strip_html_tags(raw_text):
    if raw_text is None:
        return ""
    try:
        return re.sub(r"<.*?>", "", str(raw_text))
    except Exception:
        return str(raw_text or "")

# Utility: extract video_id from URL or return as-is if it already looks like an ID
def extract_video_id(youtube_input):
    if not youtube_input:
        return ""
    text = youtube_input.strip()
    # If it's already a typical 11-char ID (heuristic)
    if re.fullmatch(r"[A-Za-z0-9_-]{8,20}", text):
        return text
    try:
        parsed = urlparse(text)
        # https://www.youtube.com/watch?v=VIDEOID
        if parsed.netloc.lower().endswith("youtube.com"):
            qs = parse_qs(parsed.query or "")
            if "v" in qs and len(qs["v"]) > 0:
                return qs["v"][0]
            # Shorts or embed formats
            parts = (parsed.path or "").strip("/").split("/")
            if len(parts) >= 2 and parts[0] in ("shorts", "embed"):
                return parts[1]
        # https://youtu.be/VIDEOID
        if parsed.netloc.lower().endswith("youtu.be"):
            vid = (parsed.path or "").strip("/")
            if vid:
                return vid
    except Exception:
        pass
    # Last fallback: try to capture after v= in raw text
    m = re.search(r"[?&]v=([A-Za-z0-9_-]{8,20})", text)
    if m:
        return m.group(1)
    return text

# Main UI
col1, col2 = st.columns([2, 1])

with col1:
    if load_clicked:
        with st.spinner("Loading data..."):
            try:
                derived_video_id = extract_video_id(video_input)
                if not derived_video_id:
                    status_placeholder.error("❌ Could not detect a valid YouTube video ID from the input.")
                    st.stop()
                st.session_state.video_id = derived_video_id
                any_docs_loaded = False
                docs_transcript = []
                docs_comments = []

                # Always fetch both transcript and comments
                status_placeholder.info("Fetching transcript...")
                df_transcript, transcript_csv_path = fetch_transcript(derived_video_id)
                if df_transcript is not None:
                    st.success(f"✅ Fetched {len(df_transcript)} transcript segments")
                    st.session_state.transcript_df = df_transcript
                    loader = CSVLoader(file_path=transcript_csv_path, encoding="utf-8")
                    docs_transcript = loader.load()
                    any_docs_loaded = True

                status_placeholder.info("Fetching comments...")
                df_comments, comments_csv_path = fetch_comments(derived_video_id)
                if df_comments is not None:
                    st.success(f"✅ Fetched {len(df_comments)} comments")
                    st.session_state.comments_df = df_comments
                    docs_comments = build_threaded_docs(comments_csv_path)
                    any_docs_loaded = True

                # Build separate chains if available
                st.session_state.comments_vectorstore = None
                st.session_state.comments_chain = None
                st.session_state.transcript_vectorstore = None
                st.session_state.transcript_chain = None
                st.session_state.combined_chain = None

                if docs_comments:
                    status_placeholder.info("Creating RAG chain for comments...")
                    persist_dir_comments = os.path.join(".chroma", f"{derived_video_id}", "comments")
                    c_vs, c_chain, _ = create_rag_chain(docs_comments, "comments", persist_directory=persist_dir_comments)
                    st.session_state.comments_vectorstore = c_vs
                    st.session_state.comments_chain = c_chain

                if docs_transcript:
                    status_placeholder.info("Creating RAG chain for transcript...")
                    persist_dir_transcript = os.path.join(".chroma", f"{derived_video_id}", "transcript")
                    t_vs, t_chain, _ = create_rag_chain(docs_transcript, "transcript", persist_directory=persist_dir_transcript)
                    st.session_state.transcript_vectorstore = t_vs
                    st.session_state.transcript_chain = t_chain
                
                # Combined chain if either exists
                if st.session_state.comments_vectorstore or st.session_state.transcript_vectorstore or st.session_state.docs_vectorstore:
                    st.session_state.combined_chain = create_combined_chain(
                        st.session_state.comments_vectorstore,
                        st.session_state.transcript_vectorstore,
                        st.session_state.docs_vectorstore
                    )

                # Back-compat: set a default rag_chain mainly for the Ask Questions area
                st.session_state.rag_chain = (
                    st.session_state.combined_chain
                    or st.session_state.transcript_chain
                    or st.session_state.comments_chain
                )

                if any_docs_loaded and (st.session_state.rag_chain is not None):
                    st.session_state.data_loaded = True
                    st.session_state.last_loaded_data_type = "Both"
                    st.session_state.prompt_mode = (
                        "Combined" if st.session_state.combined_chain else
                        ("Transcript" if st.session_state.transcript_chain else "Comments")
                    )
                    status_placeholder.success("✅ Data loaded and RAG chains created!")
                else:
                    status_placeholder.error("❌ Failed to load data")
                    
            except Exception as e:
                status_placeholder.error(f"❌ Error: {e}")
                st.error(f"Detailed error: {str(e)}")

with col2:
    st.header("Data Status")
    if st.session_state.data_loaded:
        st.success("✅ Data loaded")
        st.info(f"📊 Prompt mode: {st.session_state.prompt_mode or '—'}")
        if st.session_state.video_id:
            st.caption(f"Video: {st.session_state.video_id}")
    else:
        st.warning("⚠️ No data loaded")

tab_overview, tab_ask, tab_course, tab_summaries, tab_docs = st.tabs(["Overview", "Ask", "Course", "Summaries", "Docs"])

with tab_overview:
    st.markdown("### 📊 Overview")
    col_a, col_b, col_c = st.columns(3)
    t_count = int(len(st.session_state.transcript_df)) if st.session_state.transcript_df is not None else 0
    c_count = int(len(st.session_state.comments_df)) if st.session_state.comments_df is not None else 0
    mode = st.session_state.prompt_mode or "—"
    with col_a:
        st.metric("Transcript segments", f"{t_count}")
    with col_b:
        st.metric("Comments", f"{c_count}")
    with col_c:
        st.metric("Prompt mode", mode)
    if st.session_state.video_id:
        st.caption(f"Video: {st.session_state.video_id}")
    st.markdown("---")
    st.markdown("Use the Ask tab to query, and Course tab to browse and discuss.")

with tab_ask:
    st.markdown("### 🔍 Ask Questions")
    if st.session_state.data_loaded and st.session_state.rag_chain:
        question = st.text_area(
            "Your question", 
            placeholder="e.g., What are the main topics discussed?",
            height=100
        )
        
        ask_button = st.button("Ask", type="primary")
        
        if ask_button and question:
            with st.spinner("Generating answer..."):
                try:
                    answer = st.session_state.rag_chain.invoke(question)
                    st.markdown("#### Answer")
                    st.markdown(answer)
                except Exception as e:
                    st.error(f"Error generating answer: {e}")
        
        st.markdown("#### 💡 Sample Questions")
        samples = [
            "Give me a summary of the video",
            "What are the main topics discussed?",
            "What problems or issues are mentioned?",
            "What solutions or recommendations are provided?"
        ]
        cols = st.columns(2)
        for idx, sample in enumerate(samples):
            with cols[idx % 2]:
                if st.button(sample, key=f"sample_{idx}"):
                    with st.spinner("Generating answer..."):
                        try:
                            answer = st.session_state.rag_chain.invoke(sample)
                            st.markdown("#### Answer")
                            st.markdown(answer)
                        except Exception as e:
                            st.error(f"Error generating answer: {e}")
    else:
        st.info("👆 Please load data first to start asking questions")

with tab_course:
    st.markdown("### 🎓 Course View")
    if st.session_state.video_id:
        video_url = f"https://www.youtube.com/watch?v={st.session_state.video_id}"
        st.video(video_url)
    else:
        st.info("Provide a YouTube URL/ID and load data to preview the video here.")

    st.markdown("#### Comments")
    ctrl_col1, ctrl_col2 = st.columns([2, 1])
    with ctrl_col1:
        st.session_state.comment_search_query = st.text_input(
            "Search comments",
            value=st.session_state.comment_search_query or "",
            placeholder="Filter by keyword..."
        )
    with ctrl_col2:
        st.session_state.show_threads_count = st.number_input(
            "Show threads",
            min_value=5,
            max_value=100,
            value=int(st.session_state.show_threads_count or 10),
            step=5
        )

    comments_container = st.container()
    with comments_container:
        if st.session_state.comments_df is not None and len(st.session_state.comments_df) > 0:
            try:
                dfc = st.session_state.comments_df.copy()
                dfc["is_reply"] = dfc["is_reply"].astype(bool)
                dfc["thread_id"] = dfc.apply(
                    lambda r: r["parent_id"] if r["is_reply"] else r["comment_id"], axis=1
                )
                query = (st.session_state.comment_search_query or "").strip().lower()
                if query:
                    dfc = dfc[dfc["text"].str.lower().str.contains(query, na=False)]
                latest_by_thread = dfc.groupby("thread_id")["published_at"].max().reset_index()
                top_threads = latest_by_thread.sort_values("published_at", ascending=False)["thread_id"].tolist()
                show_count = min(int(st.session_state.show_threads_count or 10), len(top_threads))
                st.caption(f"Showing {show_count} of {len(top_threads)} threads")
                for thread_id in top_threads[:show_count]:
                    g = dfc[dfc["thread_id"] == thread_id].sort_values("published_at")
                    if g.empty:
                        continue
                    head = g[g["is_reply"] == False].head(1)
                    title_text = strip_html_tags(head["text"].iloc[0] if len(head) else g["text"].iloc[0])
                    with st.expander(title_text[:140] + ("..." if len(title_text) > 140 else ""), expanded=False):
                        for _, r in g.iterrows():
                            who = r.get("author") or "Unknown"
                            safe_text = strip_html_tags(r.get("text"))
                            st.markdown(f"<div class='comment'><span class='author'>{who}</span><span class='text'>{safe_text}</span></div>", unsafe_allow_html=True)
            except Exception as display_err:
                st.warning(f"Could not render YouTube comments: {display_err}")
        else:
            st.info("No YouTube comments loaded yet. Load comments from the sidebar.")

    st.markdown("#### Start a discussion")
    user_comment_text = st.text_area(
        "Add your comment:",
        placeholder="Type your question or comment about the video...",
        height=100,
        key="user_comment_input"
    )
    post_col1, post_col2 = st.columns([1, 8])
    with post_col1:
        post_clicked = st.button("Post", type="primary", use_container_width=True)

    if post_clicked:
        if not (user_comment_text or "").strip():
            st.warning("Please type a comment before posting.")
        else:
            st.session_state.user_comments.append({
                "author": "You",
                "text": user_comment_text.strip()
            })

            ai_reply = None
            try:
                if st.session_state.combined_chain is not None:
                    ai_reply = st.session_state.combined_chain.invoke(user_comment_text)
                else:
                    if st.session_state.comments_chain is not None:
                        comments_answer = st.session_state.comments_chain.invoke(user_comment_text)
                        if comments_answer and ("not found in comments" not in comments_answer.lower()):
                            ai_reply = comments_answer
                    if ai_reply is None and st.session_state.transcript_chain is not None:
                        ai_reply = st.session_state.transcript_chain.invoke(user_comment_text)
            except Exception as gen_err:
                st.error(f"Error generating reply: {gen_err}")

            if ai_reply:
                st.success("Assistant replied to your comment.")
            else:
                ai_reply = "I couldn't find this in the loaded comments or transcript."

            with st.container():
                st.markdown("**You**:")
                st.write(user_comment_text.strip())
                st.markdown("**Assistant**:")
                st.write(ai_reply)

            try:
                if st.session_state.comments_vectorstore is not None:
                    thread_num = len(st.session_state.user_comments)
                    live_doc_content = (
                        f"Thread: user_live_{thread_num}\n"
                        f"[user @You] {user_comment_text.strip()}\n"
                        f"[assistant @AI] {ai_reply}"
                    )
                    st.session_state.comments_vectorstore.add_documents([
                        Document(page_content=live_doc_content, metadata={
                            "thread_id": f"user_live_{thread_num}",
                            "source": "live_session"
                        })
                    ])
                    try:
                        st.session_state.comments_vectorstore.persist()
                    except Exception:
                        pass
            except Exception as up_err:
                st.warning(f"Could not add live discussion to retriever: {up_err}")

with tab_summaries:
    st.markdown("### 🧠 Quick Summaries")
    sum_col1, sum_col2, sum_col3 = st.columns(3)

    def generate_summary(style: str):
        chain = st.session_state.combined_chain or st.session_state.transcript_chain or st.session_state.comments_chain
        if not chain:
            st.warning("Load data first to generate a summary.")
            return
        prompt_map = {
            "one_liner": "Provide a one-line executive summary.",
            "short": "Provide a concise 5-bullet summary of the key points.",
            "detailed": "Provide a detailed summary with sections and key takeaways."
        }
        ask = prompt_map.get(style, "Provide a concise summary.")
        with st.spinner("Summarizing..."):
            try:
                ans = chain.invoke(ask)
                st.write(ans)
            except Exception as e:
                st.error(f"Error generating summary: {e}")

    with sum_col1:
        if st.button("📝 1‑liner"):
            generate_summary("one_liner")
    with sum_col2:
        if st.button("📌 Short"):
            generate_summary("short")
    with sum_col3:
        if st.button("📚 Detailed"):
            generate_summary("detailed")

with tab_docs:
    st.markdown("### 📄 Documents")
    
    # Context status card
    if st.session_state.data_loaded and st.session_state.video_id:
        context_status = f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    border-radius: 10px; padding: 15px; margin-bottom: 20px; color: white;">
            <h4 style="margin: 0; color: white;">📹 Active Context</h4>
            <p style="margin: 5px 0; color: white;">
                <strong>Video ID:</strong> {st.session_state.video_id}<br>
                <strong>Mode:</strong> Context-Aware Document Analysis<br>
                <strong>Sources:</strong> {'✓ Transcript' if st.session_state.transcript_df is not None else '✗ Transcript'} | 
                              {'✓ Comments' if st.session_state.comments_df is not None else '✗ Comments'} | 
                              {'✓ Docs' if st.session_state.uploaded_docs else '✗ Docs'}
            </p>
        </div>
        """
        st.markdown(context_status, unsafe_allow_html=True)
    
    # Context-aware description based on loaded video
    if st.session_state.video_id and st.session_state.data_loaded:
        st.markdown("""
        **Upload documents related to this video:**
        - 📘 Course notes, slides, or lecture materials
        - 💻 Code examples, scripts, or repositories mentioned
        - 📖 Official documentation or API references
        - 📚 Supplementary reading materials or articles
        - 🔬 Related research papers or technical documents
        
        **The AI will:**
        - Connect document content with video timestamps
        - Find where code examples relate to video explanations
        - Identify topics covered in docs but not in video (and vice versa)
        - Show what the community discusses about the documentation
        """)
    else:
        st.warning("⚠️ Please load a YouTube video first to enable context-aware document processing.")
        st.markdown("Documents will be analyzed in the context of the video's transcript and comments.")
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Upload documents (PDF, TXT, CSV, MD)",
        type=["pdf", "txt", "csv", "md"],
        accept_multiple_files=True,
        key="doc_uploader",
        disabled=not st.session_state.data_loaded
    )
    
    process_docs_button = st.button("Process Documents", type="primary")
    
    if process_docs_button and uploaded_files:
        with st.spinner("Processing documents..."):
            try:
                from langchain_community.document_loaders import TextLoader
                import tempfile
                import io
                
                # Try to import PyPDFLoader
                try:
                    from langchain_community.document_loaders import PyPDFLoader
                    pdf_loader_available = True
                except ImportError:
                    pdf_loader_available = False
                    st.warning("PDF support limited. Install pypdf for better PDF processing: pip install pypdf")
                
                # Alternative: use pypdf directly if available
                try:
                    import pypdf
                    pypdf_available = True
                except ImportError:
                    pypdf_available = False
                
                all_docs = []
                
                for uploaded_file in uploaded_files:
                    # Save uploaded file to temp location
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{uploaded_file.name}") as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        tmp_path = tmp_file.name
                    
                    try:
                        # Load based on file type
                        if uploaded_file.name.endswith('.pdf'):
                            if pdf_loader_available:
                                loader = PyPDFLoader(tmp_path)
                                docs = loader.load()
                            elif pypdf_available:
                                # Manual PDF extraction using pypdf
                                pdf_reader = pypdf.PdfReader(tmp_path)
                                text_content = ""
                                for page_num, page in enumerate(pdf_reader.pages):
                                    text_content += f"\n--- Page {page_num + 1} ---\n"
                                    text_content += page.extract_text()
                                docs = [Document(page_content=text_content, metadata={"source": uploaded_file.name, "page_count": len(pdf_reader.pages)})]
                            else:
                                st.error(f"Cannot process PDF. Please install pypdf: pip install pypdf")
                                continue
                        elif uploaded_file.name.endswith('.txt'):
                            loader = TextLoader(tmp_path, encoding='utf-8')
                            docs = loader.load()
                        elif uploaded_file.name.endswith('.csv'):
                            loader = CSVLoader(file_path=tmp_path, encoding='utf-8')
                            docs = loader.load()
                        elif uploaded_file.name.endswith('.md'):
                            # Use TextLoader for markdown files (simpler and more reliable)
                            loader = TextLoader(tmp_path, encoding='utf-8')
                            docs = loader.load()
                        else:
                            st.warning(f"Unsupported file type: {uploaded_file.name}")
                            continue
                        
                        # Add source metadata with video context
                        for doc in docs:
                            doc.metadata['source'] = uploaded_file.name
                            doc.metadata['video_id'] = st.session_state.video_id
                            doc.metadata['video_context'] = f"Related to YouTube video: {st.session_state.video_id}"
                            # Enhance content with video reference
                            if st.session_state.video_id:
                                doc.page_content = f"[Document: {uploaded_file.name} | Video Context: {st.session_state.video_id}]\n\n{doc.page_content}"
                        
                        all_docs.extend(docs)
                        
                        # Track doc-video mapping
                        if st.session_state.video_id:
                            if st.session_state.video_id not in st.session_state.doc_video_mapping:
                                st.session_state.doc_video_mapping[st.session_state.video_id] = []
                            st.session_state.doc_video_mapping[st.session_state.video_id].append({
                                'filename': uploaded_file.name,
                                'chunk_count': len(docs),
                                'timestamp': pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                            })
                        
                        st.session_state.uploaded_docs.append(uploaded_file.name)
                        
                    except Exception as e:
                        st.error(f"Error processing {uploaded_file.name}: {e}")
                        import traceback
                        st.error(f"Details: {traceback.format_exc()}")
                    finally:
                        # Clean up temp file
                        try:
                            os.unlink(tmp_path)
                        except:
                            pass
                
                if all_docs:
                    # Create vectorstore for docs
                    st.info("Creating vector store for documents...")
                    text_splitter = RecursiveCharacterTextSplitter(chunk_size=4000, chunk_overlap=200)
                    splits = text_splitter.split_documents(all_docs)
                    
                    hf_emb = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
                    
                    # Create or update docs vectorstore
                    if st.session_state.docs_vectorstore is None:
                        persist_dir_docs = os.path.join(".chroma", "docs")
                        st.session_state.docs_vectorstore = Chroma.from_documents(
                            documents=splits, 
                            embedding=hf_emb, 
                            persist_directory=persist_dir_docs
                        )
                    else:
                        # Add to existing vectorstore
                        st.session_state.docs_vectorstore.add_documents(splits)
                    
                    try:
                        st.session_state.docs_vectorstore.persist()
                    except:
                        pass
                    
                    # Create docs chain
                    retriever = st.session_state.docs_vectorstore.as_retriever(
                        search_type="mmr",
                        search_kwargs={"k": 5, "fetch_k": 20, "lambda_mult": 0.5}
                    )
                    
                    system_instructions = (
                        f"You are an assistant analyzing documents in the context of YouTube video: {st.session_state.video_id}.\n"
                        "You have access to three sources:\n"
                        "- [DOCS]: Uploaded documents related to the video\n"
                        "- [TRANSCRIPT]: The video's spoken content with timestamps\n"
                        "- [COMMENTS]: YouTube comments and discussions\n\n"
                        "Your task:\n"
                        "1. Analyze how the documents relate to what's discussed in the video\n"
                        "2. Find connections between document content and video timestamps\n"
                        "3. Identify if documents provide additional context, examples, or clarifications\n"
                        "4. Note any discrepancies or complementary information\n\n"
                        "Citation rules:\n"
                        "- Documents: [source: filename]\n"
                        "- Video content: [timestamp] or [comment_id @author]\n"
                        "- Always show the relationship between sources\n\n"
                        "If information is only in documents without video context, state: 'From documents only (not mentioned in video)'.\n"
                        "If video discusses something not in documents, state: 'Discussed in video at [timestamp] but not documented'."
                    )
                    human_message = (
                        "Question:\n{question}\n\n"
                        "Documents context:\n{context}\n\n"
                        "Instructions:\n"
                        f"- Consider this question in the context of YouTube video: {st.session_state.video_id}\n"
                        "- Extract relevant information from documents\n"
                        "- Explain how it relates to or expands on video content\n"
                        "- Provide specific citations from both documents and video when applicable\n"
                        "- Highlight key connections or gaps between sources"
                    )
                    
                    prompt = ChatPromptTemplate.from_messages([
                        ("system", system_instructions),
                        ("human", human_message)
                    ])
                    
                    llm = ChatGroq(model="openai/gpt-oss-20b", api_key=GROQ_API_KEY or "")
                    
                    def format_docs_content(docs):
                        return "\n\n".join(doc.page_content for doc in docs)
                    
                    st.session_state.docs_chain = (
                        {"context": retriever | format_docs_content, "question": RunnablePassthrough()}
                        | prompt
                        | llm
                        | StrOutputParser()
                    )
                    
                    # Update combined chain to include docs
                    if st.session_state.comments_vectorstore or st.session_state.transcript_vectorstore or st.session_state.docs_vectorstore:
                        st.session_state.combined_chain = create_combined_chain(
                            st.session_state.comments_vectorstore,
                            st.session_state.transcript_vectorstore,
                            st.session_state.docs_vectorstore
                        )
                        st.session_state.rag_chain = st.session_state.combined_chain
                    
                    st.success(f"✅ Processed {len(all_docs)} document chunks from {len(uploaded_files)} files!")
                else:
                    st.warning("No documents were successfully processed.")
                    
            except Exception as e:
                st.error(f"Error processing documents: {e}")
    
    # Display uploaded documents with video context
    if st.session_state.uploaded_docs:
        st.markdown("#### 📚 Uploaded Documents")
        if st.session_state.video_id:
            st.caption(f"All documents analyzed in context of video: `{st.session_state.video_id}`")
            
            # Show documents for current video
            if st.session_state.video_id in st.session_state.doc_video_mapping:
                current_docs = st.session_state.doc_video_mapping[st.session_state.video_id]
                for idx, doc_info in enumerate(current_docs):
                    with st.expander(f"📄 {doc_info['filename']}", expanded=False):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.caption(f"✓ Indexed: {doc_info['chunk_count']} chunks")
                        with col2:
                            st.caption(f"🕒 {doc_info['timestamp']}")
                        st.caption(f"🎥 Linked to: {st.session_state.video_id}")
            else:
                # Show all docs (legacy support)
                for idx, doc_name in enumerate(st.session_state.uploaded_docs):
                    st.markdown(f"{idx + 1}. 📄 **{doc_name}** ✓")
        else:
            for idx, doc_name in enumerate(st.session_state.uploaded_docs):
                st.markdown(f"{idx + 1}. 📄 **{doc_name}**")
    
    # Query interface for docs
    st.markdown("---")
    st.markdown("#### 🔍 Query: Docs + Video + Comments")
    
    if st.session_state.data_loaded:
        st.info("💡 Ask questions that connect the uploaded documents with the video content and discussions")
    
    if st.session_state.docs_vectorstore or st.session_state.combined_chain:
        docs_question = st.text_area(
            "Ask a question combining all sources",
            placeholder="e.g., Does the documentation cover what was explained at [timestamp]? Are there code examples for the concepts discussed?",
            height=100,
            key="docs_question_input"
        )
        
        docs_ask_button = st.button("Ask Question", type="primary", key="docs_ask_btn")
        
        if docs_ask_button and docs_question:
            with st.spinner("Generating answer from all sources..."):
                try:
                    # Use combined chain if available, otherwise use docs chain
                    if st.session_state.combined_chain:
                        answer = st.session_state.combined_chain.invoke(docs_question)
                    elif st.session_state.docs_chain:
                        answer = st.session_state.docs_chain.invoke(docs_question)
                    else:
                        answer = "No data sources available."
                    
                    st.markdown("#### Answer")
                    st.markdown(answer)
                except Exception as e:
                    st.error(f"Error generating answer: {e}")
        
        # Sample questions for docs - context-aware based on video
        st.markdown("#### 💡 Context-Aware Sample Questions")
        if st.session_state.video_id:
            docs_samples = [
                f"What code examples in the documents relate to topics in video {st.session_state.video_id}?",
                "Which parts of the documentation match what's explained in the video?",
                "Are there any examples or diagrams in docs that weren't shown in the video?",
                "Do comments mention any documentation sections? What do they say?",
                "What timestamps in the video correspond to specific document sections?",
                "Are there discrepancies between the documentation and video explanation?"
            ]
        else:
            docs_samples = [
                "What topics are covered in the uploaded documents?",
                "How do the documents relate to the video content?",
                "Are there any discrepancies between docs and video?",
                "What additional information do the documents provide?"
            ]
        
        docs_cols = st.columns(2)
        for idx, sample in enumerate(docs_samples):
            with docs_cols[idx % 2]:
                if st.button(sample, key=f"docs_sample_{idx}"):
                    with st.spinner("Analyzing across all sources..."):
                        try:
                            if st.session_state.combined_chain:
                                answer = st.session_state.combined_chain.invoke(sample)
                            elif st.session_state.docs_chain:
                                answer = st.session_state.docs_chain.invoke(sample)
                            else:
                                answer = "No data sources available."
                            st.markdown("#### Answer")
                            st.markdown(answer)
                        except Exception as e:
                            st.error(f"Error generating answer: {e}")
    else:
        st.info("👆 Load a YouTube video first, then upload and process documents to enable context-aware analysis")
    
    # Additional insights section
    if st.session_state.uploaded_docs and st.session_state.data_loaded:
        st.markdown("---")
        st.markdown("#### 📊 Document-Video Insights")
        
        insight_cols = st.columns(3)
        
        with insight_cols[0]:
            if st.button("🔗 Find Connections", use_container_width=True):
                with st.spinner("Analyzing connections..."):
                    try:
                        query = f"List the main topics in the documents and identify which timestamps in the video discuss these topics. Provide a mapping."
                        if st.session_state.combined_chain:
                            answer = st.session_state.combined_chain.invoke(query)
                            st.markdown("**Topic-Timestamp Mapping:**")
                            st.markdown(answer)
                    except Exception as e:
                        st.error(f"Error: {e}")
        
        with insight_cols[1]:
            if st.button("📝 Doc Gaps", use_container_width=True):
                with st.spinner("Finding gaps..."):
                    try:
                        query = f"What important topics are discussed in the video but not covered in the uploaded documents? List them with timestamps."
                        if st.session_state.combined_chain:
                            answer = st.session_state.combined_chain.invoke(query)
                            st.markdown("**Topics Missing from Docs:**")
                            st.markdown(answer)
                    except Exception as e:
                        st.error(f"Error: {e}")
        
        with insight_cols[2]:
            if st.button("💬 Comment References", use_container_width=True):
                with st.spinner("Analyzing comments..."):
                    try:
                        query = f"Which comments reference or discuss content from the uploaded documents? What are they saying?"
                        if st.session_state.combined_chain:
                            answer = st.session_state.combined_chain.invoke(query)
                            st.markdown("**Comments About Docs:**")
                            st.markdown(answer)
                    except Exception as e:
                        st.error(f"Error: {e}")

# Footer
st.markdown("---")
st.markdown("Developed by Sachin Aman Sagar Kausthubha")
