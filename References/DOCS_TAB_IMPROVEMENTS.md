# Documents Tab - Context-Aware Processing

## Overview
Enhanced the Documents tab to provide **context-aware processing** based on the loaded YouTube video, rather than treating documents generically.

## Key Improvements

### 1. **Video Context Integration**
- Documents are now explicitly linked to the active YouTube video
- Each uploaded document includes video ID metadata
- Documents are processed with video context in mind

### 2. **Enhanced Status Display**
- **Context Status Card**: Shows active video ID, mode, and available sources
- **Visual Indicators**: Clear display of which sources (Transcript, Comments, Docs) are loaded
- **Document-Video Mapping**: Tracks which documents belong to which video

### 3. **Intelligent Document Metadata**
Every uploaded document now includes:
```python
{
    'source': 'filename.pdf',
    'video_id': 'wzssm02u35I',
    'video_context': 'Related to YouTube video: wzssm02u35I'
}
```

### 4. **Context-Aware AI Instructions**
The AI now:
- Analyzes documents specifically in relation to the video
- Finds connections between document content and video timestamps
- Identifies topics in docs that weren't covered in video (and vice versa)
- Shows what comments say about the documentation
- Provides cross-references between all sources

**System Prompt Enhancements:**
```
- [DOCS]: Uploaded documents related to the video
- [TRANSCRIPT]: Video's spoken content with timestamps
- [COMMENTS]: YouTube discussions and community feedback

Special considerations for DOCS:
- Identify which parts of docs relate to specific video timestamps
- Note if docs provide examples not shown in the video
- Highlight discrepancies between docs and video explanations
- Check if comments reference or discuss the documentation
```

### 5. **Smart Sample Questions**
Context-aware questions that change based on whether a video is loaded:

**With Video Context:**
- "What code examples in the documents relate to topics in video X?"
- "Which parts of the documentation match what's explained in the video?"
- "What timestamps in the video correspond to specific document sections?"
- "Do comments mention any documentation sections? What do they say?"

**Without Video Context:**
- Generic document-only questions

### 6. **Document-Video Insights Section**
Three new analysis buttons:

#### 🔗 Find Connections
Maps main topics in documents to video timestamps
```
Example: "Section 3.2 in the docs explains async/await, discussed at [05:30-07:15]"
```

#### 📝 Doc Gaps
Identifies what's in the video but missing from docs
```
Example: "Error handling discussed at [12:45] not documented"
```

#### 💬 Comment References
Shows what comments say about the documentation
```
Example: "Comment by @JohnDoe references the API docs section on authentication"
```

### 7. **Enhanced Citations**
Multi-source citations that show relationships:
- `[source: example.py]` - From documents
- `[timestamp]` or `[05:30]` - From video
- `[comment_id @author]` - From comments
- `[source: example.py] discusses topic at [05:30]` - Cross-reference

### 8. **User Experience Improvements**
- Documents can only be uploaded after a video is loaded (prevents orphaned docs)
- Clear visual feedback about context status
- Document tracking with timestamps and chunk counts
- Expandable document cards showing metadata

## Usage Example

### Before (Generic):
```
Q: "What are the main topics in the documents?"
A: "The documents cover topics A, B, and C."
```

### After (Context-Aware):
```
Q: "What are the main topics in the documents?"
A: "The documents cover:
   1. Async Programming [source: notes.pdf] - explained at [05:30] in video
   2. Error Handling [source: notes.pdf] - NOT covered in video but discussed in comments [@user123]
   3. Testing Strategies [source: code.py] - demonstrated at [15:20-18:00]
   
   Note: The video discusses deployment at [20:00] which is not documented."
```

## Technical Implementation

### State Management
```python
if 'doc_video_mapping' not in st.session_state:
    st.session_state.doc_video_mapping = {}
```

### Document Processing Enhancement
```python
for doc in docs:
    doc.metadata['video_id'] = st.session_state.video_id
    doc.metadata['video_context'] = f"Related to YouTube video: {st.session_state.video_id}"
    doc.page_content = f"[Document: {filename} | Video Context: {video_id}]\n\n{doc.page_content}"
```

### Combined Chain Intelligence
The combined chain now understands three-way relationships:
1. What comments say about topics
2. Where those topics appear in the video
3. How documentation covers those topics

## Benefits

1. **Contextual Understanding**: AI knows documents are related to specific video content
2. **Cross-Referencing**: Automatic linking between docs, video, and comments
3. **Gap Analysis**: Identifies missing information across sources
4. **Better Citations**: Multi-source citations with relationships
5. **User Guidance**: Clear suggestions for relevant documents to upload
6. **Quality Answers**: More comprehensive, well-connected responses

## Example Queries That Now Work Better

1. **"Does the code in the docs match what was shown in the video?"**
   - Compares code examples with video demonstrations
   - Cites specific timestamps and document sections

2. **"What do people say about the documentation in the comments?"**
   - Finds comment threads discussing docs
   - Shows sentiment and specific issues raised

3. **"What's explained in the video but not in the docs?"**
   - Identifies documentation gaps
   - Lists topics with video timestamps

4. **"Show me the code for the concept explained at [10:30]"**
   - Finds relevant code in documents
   - Cross-references with video explanation

## Future Enhancements

Potential improvements:
- Automatic document suggestions based on video topics
- Visual timeline showing doc-video alignment
- Automatic extraction of code snippets from video timestamps
- Version tracking for documents (multiple uploads over time)
- Export feature for doc-video mappings
