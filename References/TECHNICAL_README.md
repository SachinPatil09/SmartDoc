# SmartDoc: Technical Documentation

## 🎯 Project Overview

**SmartDoc** is an AI-powered contextual knowledge assistant that leverages Retrieval-Augmented Generation (RAG) to provide intelligent question-answering capabilities across multiple data sources. The application seamlessly integrates YouTube video content (transcripts and comments) with user-uploaded documents to create a unified knowledge base.

---

## 🏗️ Architecture & Conceptual Design

### Core Concept
SmartDoc implements a **multi-source RAG pipeline** that:
1. Ingests data from YouTube videos (transcripts + comments) and local documents (PDF, TXT, CSV, MD)
2. Processes and chunks the content into semantically meaningful segments
3. Creates vector embeddings for semantic search
4. Stores embeddings in a vector database (ChromaDB)
5. Retrieves relevant context based on user queries
6. Generates accurate, context-aware answers using LLMs

### Technology Stack

**Frontend:**
- **Streamlit**: Interactive web interface with real-time updates

**Data Extraction:**
- **YouTube Transcript API**: Fetches video transcripts
- **YouTube Data API v3**: Retrieves video comments and metadata
- **LangChain Document Loaders**: PDF, CSV, TXT, Markdown parsing

**AI/ML Components:**
- **HuggingFace Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` for semantic embeddings
- **ChromaDB**: Vector database for similarity search
- **Groq API**: Fast LLM inference (llama-3.3-70b-versatile)
- **LangChain**: Orchestrates RAG pipeline components

**Processing:**
- **RecursiveCharacterTextSplitter**: Intelligent document chunking
- **MMR (Maximal Marginal Relevance)**: Diverse retrieval results

---

## 🔄 Application Flow

### 1. Data Ingestion Phase

#### YouTube Video Processing
```
User Input (YouTube URL/ID)
    ↓
Extract Video ID
    ↓
Parallel Fetching:
    ├─→ Fetch Transcript (via YouTubeTranscriptApi)
    │   ├─→ Retrieve timestamped segments
    │   └─→ Convert to DataFrame
    │
    └─→ Fetch Comments (via YouTube Data API)
        ├─→ Get top-level comments with engagement metrics
        ├─→ Fetch nested reply threads
        └─→ Build threaded comment structure
    ↓
Store as CSV files (transcript.csv, comments.csv)
```

#### Document Upload Processing
```
User Uploads Documents (PDF/TXT/CSV/MD)
    ↓
Detect File Type
    ↓
Route to Appropriate Loader:
    ├─→ PDF: PyPDFLoader
    ├─→ TXT: TextLoader
    ├─→ CSV: CSVLoader
    └─→ MD: TextLoader
    ↓
Extract Text Content
    ↓
Create Document Objects with Metadata
```

### 2. Embedding & Indexing Phase

```
Raw Documents (Transcript/Comments/Docs)
    ↓
Text Splitting (RecursiveCharacterTextSplitter)
    ├─→ Chunk Size: 4000 characters
    └─→ Overlap: 200 characters
    ↓
Generate Embeddings (HuggingFace all-MiniLM-L6-v2)
    ├─→ 384-dimensional vectors
    └─→ Captures semantic meaning
    ↓
Store in ChromaDB Vector Stores
    ├─→ Comments VectorStore (persist: .chroma/comments/)
    ├─→ Transcript VectorStore (persist: .chroma/transcript/)
    └─→ Documents VectorStore (persist: .chroma/docs/)
```

### 3. Query Processing Phase

```
User Query
    ↓
Query Embedding (same model: all-MiniLM-L6-v2)
    ↓
Multi-Source Retrieval (Parallel):
    ├─→ Search Comments VectorStore (MMR, k=5)
    ├─→ Search Transcript VectorStore (MMR, k=5)
    └─→ Search Documents VectorStore (MMR, k=5)
    ↓
Context Merging
    ├─→ Combine retrieved chunks from all sources
    ├─→ Deduplicate similar content
    └─→ Prioritize by relevance score
    ↓
Prompt Construction
    ├─→ System instructions
    ├─→ Retrieved context (formatted)
    └─→ User question
    ↓
LLM Generation (Groq - llama-3.3-70b-versatile)
    ├─→ Temperature: 0.3 (balanced creativity/accuracy)
    └─→ Max tokens: 1024
    ↓
Stream Response to User
```

### 4. RAG Chain Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Combined RAG Chain                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  Comments    │  │ Transcript   │  │  Documents   │ │
│  │  Retriever   │  │  Retriever   │  │  Retriever   │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │
│         │                  │                  │          │
│         └──────────────────┴──────────────────┘          │
│                         │                                │
│                  ┌──────▼──────┐                        │
│                  │   Context   │                        │
│                  │   Merger    │                        │
│                  └──────┬──────┘                        │
│                         │                                │
│                  ┌──────▼──────┐                        │
│                  │   Prompt    │                        │
│                  │  Template   │                        │
│                  └──────┬──────┘                        │
│                         │                                │
│                  ┌──────▼──────┐                        │
│                  │     LLM     │                        │
│                  │   (Groq)    │                        │
│                  └──────┬──────┘                        │
│                         │                                │
│                  ┌──────▼──────┐                        │
│                  │   Output    │                        │
│                  │   Parser    │                        │
│                  └─────────────┘                        │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 📋 Key Features & Implementation

### 1. **Multi-Source RAG**
- **Problem**: Traditional RAG systems work with single data sources
- **Solution**: Parallel retrieval from 3 independent vector stores
- **Benefit**: Comprehensive answers drawing from videos, comments, and documents

### 2. **Comment Threading**
- **Problem**: YouTube comments are hierarchical (replies to comments)
- **Solution**: Recursive fetching of reply threads with parent-child relationships
- **Benefit**: Preserves conversation context and discussion flow

### 3. **Persistent Vector Storage**
- **Problem**: Re-embedding large datasets on every session is slow
- **Solution**: ChromaDB persistence to `.chroma/` directory
- **Benefit**: Instant loading of previously indexed data

### 4. **MMR Retrieval**
- **Problem**: Similar chunks can be redundant
- **Solution**: Maximal Marginal Relevance algorithm
- **Benefit**: Diverse, non-redundant retrieval results

### 5. **Adaptive Prompting**
- **Problem**: Different data types need different question-answering strategies
- **Solution**: Dynamic prompt templates based on data source (comments/transcript/docs)
- **Benefit**: Contextually appropriate responses

### 6. **Streaming Responses**
- **Problem**: Waiting for full LLM generation creates poor UX
- **Solution**: Token-by-token streaming via LangChain
- **Benefit**: Real-time response display

---

## 🎨 User Interface Tabs

### 1. **Overview Tab**
- Video metadata display
- Engagement statistics
- Data loading controls

### 2. **Ask Tab**
- Main question-answering interface
- Multi-source querying
- Response streaming with source attribution

### 3. **Course Tab**
- Browse and search through video transcript
- Timestamp navigation
- Full transcript viewing

### 4. **Summaries Tab**
- AI-generated content summaries
- Multiple summary styles (concise, detailed, bullet points, key insights)
- Dedicated summaries for comments and transcript

### 5. **Docs Tab**
- Document upload interface (drag-and-drop)
- Supported formats: PDF, TXT, CSV, MD
- Document-specific Q&A
- File management (upload/delete)

---

## 🔧 Core Functions Breakdown

### `fetch_transcript(video_id)`
- Calls YouTube Transcript API
- Returns DataFrame with columns: `video_id`, `start`, `duration`, `text`
- Cached to avoid redundant API calls

### `fetch_comments(video_id)`
- Uses YouTube Data API v3
- Retrieves comments with pagination
- Includes metrics: `likeCount`, `replyCount`, `authorDisplayName`
- Stores both top-level and reply comments

### `build_threaded_docs(csv_path)`
- Reads comments CSV
- Constructs threaded conversation structure
- Creates LangChain Document objects with metadata
- Preserves parent-child relationships

### `create_rag_chain(docs, data_type, persist_directory)`
- Chunks documents using RecursiveCharacterTextSplitter
- Generates embeddings with HuggingFace model
- Creates/loads ChromaDB vector store
- Configures MMR retriever
- Returns RAG chain (retriever → prompt → LLM → parser)

### `create_combined_chain(comments_vs, transcript_vs, docs_vs)`
- Merges retrievers from all three sources
- Implements context aggregation logic
- Creates unified prompt with multi-source context
- Returns combined RAG chain

### `extract_video_id(youtube_input)`
- Parses various YouTube URL formats
- Extracts video ID from:
  - Full URLs (`youtube.com/watch?v=...`)
  - Short URLs (`youtu.be/...`)
  - Embed URLs
  - Raw video IDs

---

## 🗄️ Data Persistence Structure

```
Smart_Doc/
├── .chroma/
│   ├── comments/          # Comment embeddings vector store
│   ├── transcript/        # Transcript embeddings vector store
│   └── docs/              # Document embeddings vector store
├── {video_id}_transcript.csv    # Cached transcript data
├── {video_id}_comments_full.csv # Cached comments data
└── uploaded_docs/         # Temporary storage for uploaded files
```

---

## 🧠 LLM Configuration

### Model Selection
- **Primary**: Groq - `llama-3.3-70b-versatile`
- **Reasoning**: Fast inference, high-quality responses, cost-effective

### Prompt Engineering
Each data type has a specialized prompt:

**Comments Prompt:**
```
You are a friendly assistant helping users understand YouTube comments.
Context: {context}
Question: {question}
```

**Transcript Prompt:**
```
You are an expert at analyzing video transcripts.
Context: {context}
Question: {question}
```

**Combined Prompt:**
```
You have access to video transcripts, comments, and uploaded documents.
Synthesize information from all sources to answer questions.
Context: {context}
Question: {question}
```

---

## 🚀 Performance Optimizations

1. **Caching**: `@st.cache_data` for API calls and data loading
2. **Session State**: Maintains vector stores across interactions
3. **Persistent Storage**: ChromaDB persistence avoids re-embedding
4. **Parallel Retrieval**: Concurrent searches across vector stores
5. **Streaming**: Progressive response rendering
6. **Lazy Loading**: Vector stores loaded only when needed

---

## 🔒 Security & Configuration

### Environment Variables (.env)
```
YOUTUBE_API_KEY=your_youtube_api_key
GROQ_API_KEY=your_groq_api_key
OPENAI_API_KEY=your_openai_api_key  # optional
```

### API Rate Limits
- YouTube Data API: 10,000 quota units/day
- Groq: Tier-based rate limits
- Implemented error handling for quota exhaustion

---

## 📊 Data Flow Example

**User Query: "What are the main criticisms in the comments?"**

1. **Input Processing**: Query converted to embedding vector
2. **Retrieval**: 
   - Comments DB returns 5 critical comment chunks
   - Transcript DB returns 2 relevant segments
   - Docs DB returns 0 (no uploaded docs)
3. **Context Building**: 7 chunks formatted into prompt
4. **LLM Generation**: Groq processes prompt with context
5. **Response Streaming**: Answer displayed token-by-token
6. **Source Attribution**: Shows which chunks influenced answer

---

## 🛠️ Error Handling

- **Missing API Keys**: Graceful degradation with user notifications
- **Invalid YouTube URLs**: Input validation and error messages
- **Transcript Unavailable**: Fallback to comments-only mode
- **Rate Limiting**: Retry logic with exponential backoff
- **File Upload Errors**: Type validation and size limits
- **Embedding Failures**: Fallback to basic search

---

## 🔮 Future Enhancements

1. **Multi-Language Support**: Automatic translation of transcripts/comments
2. **Video Summarization**: Timestamped chapter generation
3. **Citation Tracking**: Precise source attribution with timestamps
4. **Collaborative Features**: Share and collaborate on video analyses
5. **Advanced Analytics**: Sentiment analysis, topic modeling
6. **Export Options**: PDF reports, markdown summaries
7. **Custom Embeddings**: Fine-tuned models for domain-specific content

---

## 📝 Development Notes

### Adding New Document Types
1. Create loader in `load_documents()` function
2. Add file extension to upload filter
3. Update UI to display new type

### Modifying Retrieval Parameters
- **`k`**: Number of chunks to retrieve (default: 5)
- **`fetch_k`**: Pool size for MMR (default: 20)
- **`lambda_mult`**: Diversity vs. relevance (0-1, default: 0.5)

### Changing Chunk Settings
- **`chunk_size`**: Maximum characters per chunk (default: 4000)
- **`chunk_overlap`**: Overlap between chunks (default: 200)

---

## 🏁 Conclusion

SmartDoc demonstrates a production-ready implementation of multi-source RAG, combining video content analysis with document intelligence. The architecture is modular, scalable, and designed for extensibility, making it suitable for various knowledge management and educational use cases.

**Key Takeaway**: By separating concerns (data ingestion, embedding, retrieval, generation) and maintaining persistent storage, SmartDoc achieves both performance and user experience excellence.
