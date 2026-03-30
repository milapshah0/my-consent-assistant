# Consent Dashboard - Technical Specification

## 1. Project Overview

### 1.1 Purpose
A single-page dashboard application designed to streamline day-to-day consent management work by:
- Automatically aggregating Confluence pages related to consent
- Automatically extracting and displaying user stories from Aha
- Automatically performing background analysis of consent-related documentation
- Providing quick access to relevant information with an intuitive UI

### 1.2 Target Users
- Consent team members
- Engineers implementing consent functionality

## 2. Technical Stack

### 2.1 Backend
- **Language**: Python 3.13+
- **Package Manager**: Poetry
- **Framework**: FastAPI (for REST API)
- **Database**: PostgreSQL 15+ with pgvector extension
- **ORM**: SQLAlchemy 2.0+ (async)
- **Migrations**: Alembic
- **Background Jobs**: APScheduler (in-process scheduler)
- **Vector Store**: pgvector for semantic search
- **Caching**: Simple in-memory cache or file-based cache
- **Key Libraries**:
  - `httpx` - HTTP client for API calls
  - `pydantic` - Data validation
  - `python-dotenv` - Environment configuration
  - `uvicorn` - ASGI server
  - `sqlalchemy[asyncio]` - Async ORM
  - `asyncpg` - PostgreSQL async driver
  - `apscheduler` - Background job scheduler
  - `aiosqlite` or `cachetools` - Simple caching (optional)
  - `pgvector` - Vector similarity search
  - `sentence-transformers` - Text embeddings
  - `langchain` - LLM orchestration (optional)
  - `openai` - AI/chatbot integration (optional)

### 2.2 Frontend
- **Framework**: React 18+
- **Build Tool**: Vite
- **Language**: TypeScript
- **UI Framework**: TailwindCSS
- **Component Library**: shadcn/ui
- **Icons**: Lucide React
- **State Management**: React Query (TanStack Query)
- **Routing**: React Router v6
- **Additional Libraries**:
  - `axios` - HTTP client
  - `recharts` - Charts and visualizations
  - `date-fns` - Date formatting
  - `react-markdown` - Markdown rendering
  - `zustand` - Lightweight state management

### 2.3 Development Tools
- **Code Quality**: ESLint, Prettier (FE), Black, isort (BE)
- **Type Checking**: TypeScript (FE), MyPy (BE)
- **Testing**: Vitest (FE), Pytest (BE)

## 3. Architecture

### 3.1 System Architecture
```
┌─────────────────────────────────────────────────────────┐
│                    React SPA (Frontend)                 │
│  - Dashboard  - Chat Interface  - User Story Context   │
└───────────────────────────┬─────────────────────────────┘
                            │ REST API
                            │
┌───────────────────────────▼─────────────────────────────┐
│                   FastAPI (Backend)                     │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │
│  │  API Routes  │  │   Chatbot    │  │ APScheduler │  │
│  │              │  │   Q&A Engine │  │ (Background)│  │
│  └──────────────┘  └──────────────┘  └─────────────┘  │
└────────┬────────────────┬────────────────┬─────────────┘
         │                │                │
         │                │                │
┌────────▼────────────────▼────────────────▼─────────────┐
│              PostgreSQL + pgvector                      │
│         (All data + vector embeddings)                  │
└────────┬────────────────────────────────────────────────┘
         │
         │ Background sync
         │
┌────────▼────────────────────────────────────────────────┐
│                  External APIs                          │
│  - Confluence API                                       │
│  - Aha API                                              │
│  - OpenAI API (optional)                                │
└─────────────────────────────────────────────────────────┘
```

### 3.2 Backend Architecture
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI app entry point
│   ├── config.py                   # Configuration settings
│   ├── database.py                 # Database connection & session
│   ├── models/                     # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── confluence_page.py      # Confluence page model
│   │   ├── aha_feature.py          # Aha feature/story model
│   │   ├── keyword.py              # Extracted keywords
│   │   ├── relationship.py         # Page-Story relationships
│   │   ├── chat_session.py         # Chat conversation history
│   │   └── embedding.py            # Vector embeddings
│   ├── schemas/                    # Pydantic schemas (API models)
│   │   ├── __init__.py
│   │   ├── confluence.py
│   │   ├── aha.py
│   │   ├── chat.py
│   │   └── analysis.py
│   ├── services/                   # Business logic
│   │   ├── __init__.py
│   │   ├── confluence_service.py   # Confluence API integration
│   │   ├── aha_service.py          # Aha API integration
│   │   ├── analysis_service.py     # Data analysis & insights
│   │   ├── embedding_service.py    # Text embedding generation
│   │   ├── chatbot_service.py      # Q&A and chatbot logic
│   │   └── context_service.py      # Cross-story context awareness
│   ├── api/                        # API routes
│   │   ├── __init__.py
│   │   ├── confluence.py
│   │   ├── aha.py
│   │   ├── chat.py                 # Chat/Q&A endpoints
│   │   └── analysis.py
│   ├── tasks/                      # Background tasks (APScheduler)
│   │   ├── __init__.py
│   │   ├── scheduler.py            # APScheduler setup
│   │   ├── sync_confluence.py      # Sync Confluence pages
│   │   ├── sync_aha.py             # Sync Aha features
│   │   ├── extract_keywords.py     # Extract keywords
│   │   ├── generate_embeddings.py  # Generate vector embeddings
│   │   └── analyze_relationships.py # Analyze relationships
│   └── utils/                      # Utility functions
│       ├── __init__.py
│       ├── cache.py
│       ├── embeddings.py           # Embedding utilities
│       └── helpers.py
├── alembic/                        # Database migrations
│   ├── versions/
│   └── env.py
├── tests/
├── pyproject.toml
└── .env.example
```

### 3.3 Frontend Architecture
```
frontend/
├── src/
│   ├── main.tsx                    # Entry point
│   ├── App.tsx                     # Root component
│   ├── components/                 # Reusable components
│   │   ├── ui/                    # shadcn/ui components
│   │   ├── Dashboard.tsx          # Main dashboard view
│   │   ├── ConfluenceCard.tsx     # Confluence page card
│   │   ├── AhaStoryCard.tsx       # Aha user story card
│   │   ├── AnalysisPanel.tsx      # Analysis summary panel
│   │   ├── ChatInterface.tsx      # Q&A chatbot interface
│   │   ├── ChatMessage.tsx        # Individual chat message
│   │   ├── StoryContext.tsx       # Story context sidebar
│   │   ├── RelatedContent.tsx     # Related pages/stories
│   │   ├── IdeaFormulator.tsx     # Help formulate ideas
│   │   └── Sidebar.tsx            # Navigation sidebar
│   ├── hooks/                     # Custom React hooks
│   │   ├── useConfluence.ts
│   │   ├── useAha.ts
│   │   ├── useAnalysis.ts
│   │   ├── useChat.ts             # Chat/Q&A hook
│   │   └── useStoryContext.ts     # Story context hook
│   ├── services/                  # API service layer
│   │   └── api.ts
│   ├── types/                     # TypeScript types
│   │   ├── confluence.ts
│   │   ├── aha.ts
│   │   ├── chat.ts
│   │   └── analysis.ts
│   ├── utils/                     # Utility functions
│   │   └── helpers.ts
│   └── styles/                    # Global styles
├── package.json
└── vite.config.ts
```

## 4. Feature Requirements

### 4.1 Core Features

#### 4.1.1 Confluence Integration
- **Search & Filter**: Search consent-related pages by keywords, labels, spaces
- **Page Display**: Show page title, excerpt, last updated, author
- **Quick Access**: Direct links to Confluence pages
- **Content Preview**: Inline preview of page content with formatted rendering
- **Filters**:
  - By space
  - By date range
  - By author
  - By labels/tags

#### 4.1.2 Aha Integration
- **User Stories**: Display active user stories related to consent
- **Story Details**:
  - Story name and description
  - Status (Not started, In progress, Done)
  - Priority
  - Assignees
  - Tags
  - Due dates
- **Filters**:
  - By status
  - By priority
  - By assignee
  - By product/initiative

#### 4.1.3 Background Analysis (Background Jobs)
- **Content Extraction**: Automatically extract key information from Confluence pages
- **Keyword Analysis**: Identify frequently mentioned terms across all content
- **Relationship Mapping**: Automatically link related pages and stories using embeddings
- **Trend Analysis**: Track changes over time with historical data
- **Summary Generation**: Generate AI-powered summaries of content
- **Embedding Generation**: Create vector embeddings for semantic search
- **Scheduled Sync**: Auto-sync data every 15 minutes

#### 4.1.4 Chatbot & Q&A System
**Purpose**: Help developers design applications by providing intelligent assistance and context

**Core Capabilities**:
- **Contextual Q&A**: Answer questions about consent implementation, user stories, and documentation
- **Idea Formulation**: Help developers articulate and refine their implementation ideas
- **Solution Guidance**: Suggest approaches based on existing stories and documentation
- **Cross-Story Context**: Leverage knowledge from all user stories, even when focused on one
- **Smart Suggestions**: Recommend related stories, pages, and patterns

**Features**:
- **Natural Language Interface**: Conversational chat interface
- **Context-Aware Responses**: Understands current user story focus
- **Related Content Discovery**: "You might also want to look at..."
- **Code Examples**: Extract and suggest relevant code snippets from Confluence
- **Design Pattern Suggestions**: Identify similar implementations
- **Requirement Clarification**: Help refine vague requirements
- **Gist Summaries**: Provide quick summaries of pages/stories
- **What Am I Solving**: Help developer articulate the problem statement

**Conversation Flow**:
1. Developer selects a user story to focus on
2. Dashboard shows gist/summary of the story
3. Related confluence pages and other stories appear
4. Developer asks questions via chat:
   - "What's the best way to implement this?"
   - "Are there similar features already built?"
   - "What are the key requirements here?"
   - "Help me understand what I'm solving"
5. Chatbot provides contextual answers using:
   - Current story details
   - Related stories
   - Confluence documentation
   - Historical patterns

#### 4.1.5 Dashboard Features
- **Widgets**:
  - Recent Confluence updates
  - Active user stories count
  - Priority distribution chart
  - Recent activity timeline
  - Quick links section
  - Search across all sources
- **Customization**: User can show/hide widgets
- **Refresh**: Manual and auto-refresh options
- **Notifications**: Highlight new or updated content

### 4.2 UI/UX Requirements

#### 4.2.1 Design Principles
- **Modern & Clean**: Minimal clutter, focus on content
- **Responsive**: Works on desktop and tablet
- **Accessible**: WCAG 2.1 AA compliant
- **Fast**: Optimized loading with skeleton screens
- **Intuitive**: Clear navigation and tooltips

#### 4.2.2 Color Scheme
- **Primary**: Blue (#3B82F6) - Trust, professional
- **Secondary**: Purple (#8B5CF6) - Creative, innovative
- **Accent**: Green (#10B981) - Success, active states
- **Warning**: Amber (#F59E0B)
- **Error**: Red (#EF4444)
- **Background**: Gradient or subtle pattern
- **Dark Mode**: Support for dark theme

#### 4.2.3 Components
- **Cards**: Rounded corners, subtle shadows, hover effects
- **Tooltips**: Context-sensitive help on all interactive elements
- **Loading States**: Skeleton screens and progress indicators
- **Empty States**: Helpful messages when no data
- **Error States**: Clear error messages with retry options

## 5. API Specifications

### 5.1 Backend API Endpoints

#### 5.1.1 Confluence Endpoints
```
GET /api/confluence/pages
  Query params:
    - search: string (optional)
    - space: string (optional)
    - limit: int (default: 20)
    - offset: int (default: 0)
  Response: List of Confluence pages

GET /api/confluence/pages/{page_id}
  Response: Full page details with content

GET /api/confluence/spaces
  Response: List of available spaces
```

#### 5.1.2 Aha Endpoints
```
GET /api/aha/ideas
  Query params:
    - status: string (optional)
    - priority: string (optional)
    - limit: int (default: 20)
  Response: List of features/user stories

GET /api/aha/ideas/{feature_id}
  Response: Full feature details
```

#### 5.1.3 Analysis Endpoints
```
GET /api/analysis/summary
  Query params:
    - days: int (default: 7)
  Response: Summary statistics

GET /api/analysis/keywords
  Response: Top keywords from recent content

GET /api/analysis/trends
  Response: Trend data over time
```

#### 5.1.4 Chat & Q&A Endpoints
```
POST /api/chat/message
  Body:
    - message: string (user question)
    - session_id: string (optional, for conversation continuity)
    - story_id: string (optional, current focused story)
  Response: AI-generated answer with sources

GET /api/chat/sessions
  Response: List of chat sessions

GET /api/chat/sessions/{session_id}
  Response: Chat history for session

POST /api/chat/context
  Body:
    - story_id: string
  Response: Related stories, pages, and context summary

POST /api/chat/formulate-idea
  Body:
    - rough_idea: string
    - story_id: string (optional)
  Response: Structured idea with suggestions

GET /api/chat/related/{story_id}
  Query params:
    - limit: int (default: 10)
  Response: Related stories and confluence pages
```

#### 5.1.5 Utility Endpoints
```
GET /api/health
  Response: Service health status

GET /api/refresh
  Response: Trigger background data refresh
```

### 5.2 External API Integration

#### 5.2.1 Confluence API
- **Base URL**: `https://zentrust.atlassian.net/wiki/rest/api`
- **Authentication**: Bearer token (API key)
- **Key Endpoints**:
  - `/content/search` - Search content
  - `/content/{id}` - Get page by ID
  - `/space` - List spaces

#### 5.2.2 Aha API
- **Base URL**: `https://onetrust.aha.io/api/v1`
- **Authentication**: Bearer token (API key)
- **Key Endpoints**:
  - `/features` - List features
  - `/features/{id}` - Get feature details

## 6. Database Schema (PostgreSQL)

### 6.1 Overview
The database uses PostgreSQL 15+ with the pgvector extension for semantic search capabilities. All tables use UUIDs for primary keys and include standard timestamp fields.

### 6.2 Database Tables

#### 6.2.1 confluence_pages
Stores Confluence page data extracted via background jobs.

```sql
CREATE TABLE confluence_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    confluence_id VARCHAR(255) UNIQUE NOT NULL,  -- Original Confluence page ID
    space_key VARCHAR(100) NOT NULL,
    space_name VARCHAR(255),
    title TEXT NOT NULL,
    excerpt TEXT,
    content TEXT,  -- Full page content (markdown or storage format)
    content_html TEXT,  -- Rendered HTML content
    url TEXT NOT NULL,
    author_name VARCHAR(255),
    author_email VARCHAR(255),
    author_account_id VARCHAR(255),
    labels TEXT[],  -- Array of label names
    version INTEGER,
    status VARCHAR(50) DEFAULT 'current',  -- current, archived, deleted
    last_modified_at TIMESTAMP WITH TIME ZONE,
    confluence_created_at TIMESTAMP WITH TIME ZONE,
    confluence_updated_at TIMESTAMP WITH TIME ZONE,
    synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_confluence_id (confluence_id),
    INDEX idx_space_key (space_key),
    INDEX idx_labels (labels),
    INDEX idx_updated_at (confluence_updated_at DESC),
    INDEX idx_status (status)
);
```

#### 6.2.2 aha_features
Stores Aha feature/user story data extracted via background jobs.

```sql
CREATE TABLE aha_features (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aha_id VARCHAR(255) UNIQUE NOT NULL,  -- Original Aha feature ID
    reference_num VARCHAR(50) NOT NULL,  -- e.g., CONSENT-123
    name TEXT NOT NULL,
    description TEXT,
    status VARCHAR(50),  -- Not started, In progress, Done, etc.
    workflow_status JSONB,  -- Full workflow status object
    priority VARCHAR(50),  -- High, Medium, Low
    score DECIMAL,  -- Priority score
    assignees JSONB,  -- Array of assignee objects {id, name, email}
    tags TEXT[],
    product_name VARCHAR(255),
    release_name VARCHAR(255),
    initiative_name VARCHAR(255),
    due_date DATE,
    start_date DATE,
    url TEXT NOT NULL,
    custom_fields JSONB,  -- Additional custom fields
    requirements_count INTEGER DEFAULT 0,
    tasks_count INTEGER DEFAULT 0,
    progress_percentage DECIMAL(5,2),
    aha_created_at TIMESTAMP WITH TIME ZONE,
    aha_updated_at TIMESTAMP WITH TIME ZONE,
    synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_aha_id (aha_id),
    INDEX idx_reference_num (reference_num),
    INDEX idx_status (status),
    INDEX idx_priority (priority),
    INDEX idx_tags (tags),
    INDEX idx_updated_at (aha_updated_at DESC)
);
```

#### 6.2.3 embeddings
Stores vector embeddings for semantic search (generated via background jobs).

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_type VARCHAR(50) NOT NULL,  -- 'confluence_page' or 'aha_feature'
    content_id UUID NOT NULL,  -- FK to confluence_pages.id or aha_features.id
    embedding_model VARCHAR(100) DEFAULT 'all-MiniLM-L6-v2',
    embedding vector(384),  -- Adjust dimension based on model
    text_chunk TEXT,  -- The text that was embedded
    chunk_index INTEGER DEFAULT 0,  -- For large documents split into chunks
    metadata JSONB,  -- Additional metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_content_type_id (content_type, content_id),
    INDEX idx_embedding_vector USING ivfflat (embedding vector_cosine_ops)
);
```

#### 6.2.4 keywords
Stores extracted keywords and their frequencies (extracted via background jobs).

```sql
CREATE TABLE keywords (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    keyword VARCHAR(255) NOT NULL,
    normalized_keyword VARCHAR(255) NOT NULL,  -- Lowercase, stemmed
    frequency INTEGER DEFAULT 1,
    context_type VARCHAR(50),  -- 'confluence', 'aha', 'both'
    first_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Indexes
    UNIQUE INDEX idx_normalized_keyword_context (normalized_keyword, context_type),
    INDEX idx_frequency (frequency DESC),
    INDEX idx_keyword (keyword)
);
```

#### 6.2.5 keyword_occurrences
Tracks where keywords appear (many-to-many).

```sql
CREATE TABLE keyword_occurrences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    keyword_id UUID REFERENCES keywords(id) ON DELETE CASCADE,
    content_type VARCHAR(50) NOT NULL,  -- 'confluence_page' or 'aha_feature'
    content_id UUID NOT NULL,
    occurrence_count INTEGER DEFAULT 1,
    context_snippet TEXT,  -- Surrounding text
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_keyword_id (keyword_id),
    INDEX idx_content (content_type, content_id),
    UNIQUE INDEX idx_keyword_content (keyword_id, content_type, content_id)
);
```

#### 6.2.6 relationships
Stores relationships between Confluence pages and Aha features (discovered via background analysis).

```sql
CREATE TABLE relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type VARCHAR(50) NOT NULL,  -- 'confluence_page' or 'aha_feature'
    source_id UUID NOT NULL,
    target_type VARCHAR(50) NOT NULL,  -- 'confluence_page' or 'aha_feature'
    target_id UUID NOT NULL,
    relationship_type VARCHAR(50) NOT NULL,  -- 'references', 'related_to', 'implements', 'documents'
    confidence_score DECIMAL(5,4),  -- 0.0 to 1.0
    evidence JSONB,  -- What led to this relationship (shared keywords, embeddings, etc.)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_source (source_type, source_id),
    INDEX idx_target (target_type, target_id),
    INDEX idx_relationship_type (relationship_type),
    INDEX idx_confidence (confidence_score DESC),
    UNIQUE INDEX idx_unique_relationship (source_type, source_id, target_type, target_id, relationship_type)
);
```

#### 6.2.7 chat_sessions
Stores chat conversation sessions for the Q&A system.

```sql
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_name VARCHAR(255),
    user_id VARCHAR(255),  -- Future: for multi-user support
    focused_story_id UUID,  -- REFERENCES aha_features(id), optional
    context_metadata JSONB,  -- Additional context
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_message_at TIMESTAMP WITH TIME ZONE,
    
    -- Indexes
    INDEX idx_user_id (user_id),
    INDEX idx_focused_story (focused_story_id),
    INDEX idx_last_message (last_message_at DESC)
);
```

#### 6.2.8 chat_messages
Stores individual messages in chat conversations.

```sql
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,  -- 'user' or 'assistant'
    content TEXT NOT NULL,
    sources JSONB,  -- Referenced confluence pages, aha features, etc.
    metadata JSONB,  -- Model used, tokens, etc.
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_session_id_created (session_id, created_at),
    INDEX idx_role (role)
);
```

#### 6.2.9 analysis_summaries
Stores pre-computed analysis summaries (generated via background jobs).

```sql
CREATE TABLE analysis_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    summary_type VARCHAR(50) NOT NULL,  -- 'daily', 'weekly', 'monthly', 'story'
    reference_id UUID,  -- Optional: specific story ID for story-level summaries
    summary_data JSONB NOT NULL,  -- Flexible JSON structure for different summary types
    metadata JSONB,
    valid_from TIMESTAMP WITH TIME ZONE NOT NULL,
    valid_until TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_summary_type (summary_type),
    INDEX idx_reference_id (reference_id),
    INDEX idx_valid_from (valid_from DESC)
);
```

#### 6.2.10 sync_logs
Tracks background job execution and sync status.

```sql
CREATE TABLE sync_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sync_type VARCHAR(50) NOT NULL,  -- 'confluence', 'aha', 'embeddings', 'keywords', 'relationships'
    status VARCHAR(20) NOT NULL,  -- 'running', 'success', 'failed'
    items_processed INTEGER DEFAULT 0,
    items_created INTEGER DEFAULT 0,
    items_updated INTEGER DEFAULT 0,
    items_deleted INTEGER DEFAULT 0,
    error_message TEXT,
    error_details JSONB,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds DECIMAL(10,2),
    
    -- Indexes
    INDEX idx_sync_type_status (sync_type, status),
    INDEX idx_started_at (started_at DESC)
);
```

### 6.3 Database Views

#### 6.3.1 v_story_context
Provides enriched story context for the chatbot.

```sql
CREATE VIEW v_story_context AS
SELECT 
    af.id,
    af.reference_num,
    af.name,
    af.description,
    af.status,
    af.priority,
    af.url,
    -- Related confluence pages
    COALESCE(
        json_agg(
            DISTINCT jsonb_build_object(
                'id', cp.id,
                'title', cp.title,
                'url', cp.url,
                'confidence', r1.confidence_score
            )
        ) FILTER (WHERE cp.id IS NOT NULL), 
        '[]'
    ) AS related_pages,
    -- Related stories
    COALESCE(
        json_agg(
            DISTINCT jsonb_build_object(
                'id', af2.id,
                'reference_num', af2.reference_num,
                'name', af2.name,
                'url', af2.url,
                'confidence', r2.confidence_score
            )
        ) FILTER (WHERE af2.id IS NOT NULL),
        '[]'
    ) AS related_stories,
    -- Top keywords
    COALESCE(
        json_agg(
            DISTINCT jsonb_build_object(
                'keyword', k.keyword,
                'frequency', ko.occurrence_count
            )
        ) FILTER (WHERE k.id IS NOT NULL),
        '[]'
    ) AS top_keywords
FROM aha_features af
LEFT JOIN relationships r1 ON r1.source_type = 'aha_feature' 
    AND r1.source_id = af.id 
    AND r1.target_type = 'confluence_page'
LEFT JOIN confluence_pages cp ON cp.id = r1.target_id
LEFT JOIN relationships r2 ON r2.source_type = 'aha_feature' 
    AND r2.source_id = af.id 
    AND r2.target_type = 'aha_feature'
LEFT JOIN aha_features af2 ON af2.id = r2.target_id AND af2.id != af.id
LEFT JOIN keyword_occurrences ko ON ko.content_type = 'aha_feature' AND ko.content_id = af.id
LEFT JOIN keywords k ON k.id = ko.keyword_id
GROUP BY af.id;
```

### 6.4 Pydantic Schemas (API Models)

These are the Pydantic models used for API requests/responses:

#### 6.4.1 Confluence Schemas
```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class ConfluencePageBase(BaseModel):
    title: str
    space_key: str
    excerpt: Optional[str] = None
    url: str

class ConfluencePageResponse(ConfluencePageBase):
    id: UUID
    confluence_id: str
    space_name: Optional[str]
    author_name: Optional[str]
    labels: List[str] = []
    status: str
    confluence_updated_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

class ConfluencePageDetail(ConfluencePageResponse):
    content: Optional[str]
    content_html: Optional[str]
    version: Optional[int]
```

#### 6.4.2 Aha Schemas
```python
class AhaFeatureBase(BaseModel):
    name: str
    reference_num: str
    description: Optional[str] = None
    status: str
    priority: Optional[str] = None
    url: str

class AhaFeatureResponse(AhaFeatureBase):
    id: UUID
    aha_id: str
    assignees: Optional[List[dict]] = []
    tags: List[str] = []
    due_date: Optional[datetime]
    progress_percentage: Optional[float]
    aha_updated_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

class AhaFeatureDetail(AhaFeatureResponse):
    workflow_status: Optional[dict]
    custom_fields: Optional[dict]
    requirements_count: int = 0
    tasks_count: int = 0
```

#### 6.4.3 Chat Schemas
```python
class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[UUID] = None
    story_id: Optional[UUID] = None

class ChatMessageResponse(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    sources: Optional[List[dict]] = []
    created_at: datetime
    
    class Config:
        from_attributes = True

class ChatContextResponse(BaseModel):
    story: AhaFeatureDetail
    related_pages: List[ConfluencePageResponse]
    related_stories: List[AhaFeatureResponse]
    summary: str
    top_keywords: List[dict]

class IdeaFormulationRequest(BaseModel):
    rough_idea: str = Field(..., min_length=10, max_length=5000)
    story_id: Optional[UUID] = None

class IdeaFormulationResponse(BaseModel):
    structured_idea: str
    problem_statement: str
    suggested_approach: str
    related_patterns: List[dict]
    questions_to_consider: List[str]
```

#### 6.4.4 Analysis Schemas
```python
class AnalysisSummary(BaseModel):
    total_pages: int
    total_features: int
    recent_updates: int
    active_stories: int
    top_keywords: List[dict]
    activity_trend: List[dict]
    priority_distribution: dict
    
class RelationshipResponse(BaseModel):
    id: UUID
    source_type: str
    source_id: UUID
    target_type: str
    target_id: UUID
    relationship_type: str
    confidence_score: float
    evidence: Optional[dict]
    
    class Config:
        from_attributes = True
```

## 7. Background Jobs Architecture

### 7.1 APScheduler Tasks

All data extraction and analysis happens in the background using APScheduler, running in-process with the FastAPI application. No separate worker processes or message brokers required.

#### 7.1.1 Sync Tasks

**Task: sync_confluence_pages**
- **Schedule**: Every 15 minutes
- **Function**: Fetch new/updated Confluence pages from API
- **Process**:
  1. Query Confluence API for pages in consent-related spaces
  2. Compare with existing pages in database
  3. Insert new pages or update existing ones
  4. Mark deleted pages as archived
  5. Trigger embedding generation for new content

**Task: sync_aha_features**
- **Schedule**: Every 15 minutes
- **Function**: Fetch new/updated Aha features
- **Process**:
  1. Query Aha API for consent-related features
  2. Compare with existing features in database
  3. Insert new features or update existing ones
  4. Update assignees, tags, and status
  5. Trigger embedding generation for new content

#### 7.1.2 Analysis Tasks

**Task: generate_embeddings**
- **Trigger**: After content sync or on-demand
- **Function**: Generate vector embeddings for semantic search
- **Process**:
  1. Find content without embeddings or with outdated embeddings
  2. Split large documents into chunks
  3. Generate embeddings using sentence-transformers
  4. Store in embeddings table

**Task: extract_keywords**
- **Schedule**: Every 30 minutes
- **Function**: Extract and update keywords from content
- **Process**:
  1. Process new/updated pages and features
  2. Extract keywords using NLP techniques
  3. Update keywords and keyword_occurrences tables
  4. Calculate frequency statistics

**Task: analyze_relationships**
- **Schedule**: Every hour
- **Function**: Discover relationships between content
- **Process**:
  1. Use vector similarity to find related content
  2. Analyze keyword overlap
  3. Detect explicit references (e.g., story numbers in pages)
  4. Calculate confidence scores
  5. Store in relationships table

**Task: generate_summaries**
- **Schedule**: Daily at 2 AM
- **Function**: Pre-compute analysis summaries
- **Process**:
  1. Calculate aggregate statistics
  2. Generate trend data
  3. Create story-level context summaries
  4. Store in analysis_summaries table

### 7.2 Task Dependencies

```
sync_confluence_pages ──┐
                         ├──> generate_embeddings ──> analyze_relationships ──> generate_summaries
sync_aha_features ──────┤
                         └──> extract_keywords ──────┘
```

### 7.3 APScheduler Configuration

```python
# app/tasks/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import logging

logger = logging.getLogger(__name__)

# Initialize scheduler
scheduler = AsyncIOScheduler()

def setup_scheduler():
    """Configure and start the background job scheduler."""
    from app.tasks.sync_confluence import sync_confluence_pages
    from app.tasks.sync_aha import sync_aha_features
    from app.tasks.extract_keywords import extract_keywords
    from app.tasks.analyze_relationships import analyze_relationships
    from app.tasks.generate_embeddings import generate_embeddings
    
    # Sync tasks - every 15 minutes
    scheduler.add_job(
        sync_confluence_pages,
        trigger=IntervalTrigger(minutes=15),
        id='sync_confluence',
        name='Sync Confluence Pages',
        replace_existing=True,
        max_instances=1  # Prevent concurrent runs
    )
    
    # Embedding generation - every 20 minutes (after sync)
    scheduler.add_job(
        generate_embeddings,
        trigger=IntervalTrigger(minutes=20),
        id='generate_embeddings',
        name='Generate Embeddings',
        replace_existing=True,
        max_instances=1
    )
    
    # Keyword extraction - every 30 minutes
    scheduler.add_job(
        extract_keywords,
        trigger=IntervalTrigger(minutes=30),
        id='extract_keywords',
        name='Extract Keywords',
        replace_existing=True,
        max_instances=1
    )
    
    # Relationship analysis - every hour
    scheduler.add_job(
        analyze_relationships,
        trigger=IntervalTrigger(hours=1),
        id='analyze_relationships',
        name='Analyze Relationships',
        replace_existing=True,
        max_instances=1
    )
    
    # Daily summaries - 2 AM every day
    scheduler.add_job(
        generate_summaries,
        trigger=CronTrigger(hour=2, minute=0),
        id='generate_summaries',
        name='Generate Daily Summaries',
        replace_existing=True
    )
    
    # Start the scheduler
    scheduler.start()
    logger.info("Background job scheduler started")
    
    return scheduler

def shutdown_scheduler():
    """Gracefully shutdown the scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Background job scheduler stopped")

# In app/main.py, add:
# @app.on_event("startup")
# async def startup_event():
#     setup_scheduler()
#
# @app.on_event("shutdown")
# async def shutdown_event():
#     shutdown_scheduler()
```

## 8. Configuration & Security

### 8.1 Environment Variables
```bash
# Backend (.env)

# Database
DATABASE_URL=postgresql+psycopg://postgres:password@localhost:5432/consent_dashboard
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# External APIs
CONFLUENCE_EMAIL=your-email@company.com
CONFLUENCE_API_TOKEN=your_confluence_api_token
CONFLUENCE_BASE_URL=https://zentrust.atlassian.net/wiki
CONFLUENCE_SPACE_KEYS=CONSENT,PRIVACY  # Comma-separated list of spaces to sync

AHA_API_KEY=TX1RnViXL4F43lNRzNWowglZl9snmWcUazHOswEJb34
AHA_BASE_URL=https://onetrust.aha.io/api/v1
AHA_PRODUCT_KEY=CONSENT  # Product key to filter features

# AI/Chatbot (Optional - for enhanced Q&A)
OPENAI_API_KEY=<optional_openai_key>
OPENAI_MODEL=gpt-4
EMBEDDING_MODEL=all-MiniLM-L6-v2  # sentence-transformers model

# Application Settings
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
SECRET_KEY=<generate_random_secret_key>

# Background Jobs (APScheduler)
BACKGROUND_JOBS_ENABLED=true
SYNC_INTERVAL_MINUTES=15

# Performance
CACHE_TTL=300
MAX_EMBEDDING_BATCH_SIZE=100

# Frontend (.env)
VITE_API_BASE_URL=http://localhost:8000
```

### 8.2 Security Considerations
- **API Keys**: All API keys stored in environment variables only, never in code
- **Database**: PostgreSQL with strong password, connection pooling
- **CORS**: Configured for specific origins only
- **Rate Limiting**: Applied on all public API endpoints
- **Input Validation**: Pydantic models validate all API requests
- **SQL Injection**: Protected via SQLAlchemy ORM parameterized queries
- **HTTPS**: Required in production
- **Secrets Management**: Use proper secrets management in production (e.g., AWS Secrets Manager, HashiCorp Vault)
- **Database Migrations**: Track all schema changes via Alembic
- **Access Control**: Future: Add authentication/authorization for multi-user support

## 9. Performance Requirements

### 9.1 Backend
- API response time < 500ms for cached data
- API response time < 2s for fresh data
- Support concurrent requests (min 50)
- Background refresh every 5 minutes

### 9.2 Frontend
- Initial page load < 2s
- Time to interactive < 3s
- Smooth animations (60fps)
- Lazy loading for images and heavy components

## 10. Development Phases

### Phase 1: Foundation & Database (Week 1)
- [ ] Set up project structure (backend, frontend)
- [ ] Configure Poetry and npm/pnpm
- [ ] Set up PostgreSQL database with pgvector extension
- [ ] Create Alembic migrations for all tables
- [ ] Create basic FastAPI server
- [ ] Create React app with Vite and TailwindCSS
- [ ] Set up ESLint, Prettier, Black, isort
- [ ] Create .env.example files

### Phase 2: Backend Core & External APIs (Week 1-2)
- [ ] Implement database models (SQLAlchemy)
- [ ] Implement Pydantic schemas
- [ ] Implement Confluence API service
- [ ] Implement Aha API service
- [ ] Create basic API endpoints (Confluence, Aha)
- [ ] Set up APScheduler
- [ ] Write unit tests for services

### Phase 3: Background Jobs (Week 2)
- [ ] Implement sync_confluence_pages task
- [ ] Implement sync_aha_features task
- [ ] Implement generate_embeddings task
- [ ] Implement extract_keywords task
- [ ] Implement analyze_relationships task
- [ ] Implement generate_summaries task
- [ ] Configure APScheduler with intervals
- [ ] Add sync logging and monitoring
- [ ] Implement manual trigger endpoints

### Phase 4: Frontend Dashboard (Week 2-3)
- [ ] Set up shadcn/ui components
- [ ] Implement Dashboard layout with sidebar
- [ ] Create ConfluenceCard component
- [ ] Create AhaStoryCard component
- [ ] Create AnalysisPanel component
- [ ] Implement filters and search
- [ ] Add React Query for data fetching
- [ ] Create loading and error states

### Phase 5: Chatbot & Q&A System (Week 3)
- [ ] Implement embedding service
- [ ] Implement semantic search using pgvector
- [ ] Implement chatbot service (context-aware)
- [ ] Create chat API endpoints
- [ ] Implement ChatInterface component
- [ ] Implement StoryContext component
- [ ] Implement RelatedContent component
- [ ] Implement IdeaFormulator component
- [ ] Add chat message history

### Phase 6: Analysis & Context Features (Week 3-4)
- [ ] Implement analysis API endpoints
- [ ] Create keyword extraction visualization
- [ ] Create relationship graph visualization
- [ ] Create trend charts (recharts)
- [ ] Implement story context view
- [ ] Add related content suggestions
- [ ] Implement gist/summary generation

### Phase 7: Polish & UX (Week 4)
- [ ] Add tooltips throughout the UI
- [ ] Implement dark mode
- [ ] Add skeleton loading states
- [ ] Optimize bundle size and performance
- [ ] Add error boundaries
- [ ] Implement responsive design
- [ ] Add keyboard shortcuts
- [ ] User testing and feedback

### Phase 8: Documentation & Deployment (Week 4)
- [ ] Write comprehensive README
- [ ] Document API endpoints
- [ ] Create developer setup guide
- [ ] Create Docker Compose setup
- [ ] Set up CI/CD pipeline
- [ ] Deploy to staging environment
- [ ] Performance testing
- [ ] Production deployment

## 11. Testing Strategy

### 11.1 Backend Testing
- Unit tests for services (pytest)
- API endpoint tests
- Integration tests with mocked APIs
- Test coverage > 80%

### 11.2 Frontend Testing
- Component tests (Vitest + React Testing Library)
- Integration tests
- E2E tests (Playwright - optional)
- Test coverage > 70%

### 11.3 Background Job Testing
- Mock external API responses
- Test sync logic with sample data
- Test embedding generation
- Test relationship discovery algorithms

## 12. Documentation Requirements

### 12.1 README
- Project overview
- Prerequisites
- Installation steps
- Running locally
- Environment setup
- API documentation link
- Contributing guidelines

### 12.2 Inline Documentation
- JSDoc for TypeScript functions
- Docstrings for Python functions
- Component prop documentation
- API endpoint documentation

## 13. Success Metrics

- **Usability**: User can find relevant information within 3 clicks
- **Performance**: Dashboard loads in < 2s
- **Reliability**: 99% uptime
- **Coverage**: Captures 100% of consent-related Confluence pages
- **Adoption**: Daily active usage by team members

## 14. Technology Decisions & Rationale

### 14.1 Why PostgreSQL + pgvector?
- **Unified Storage**: Single database for all data (pages, features, embeddings)
- **Semantic Search**: pgvector enables efficient vector similarity search
- **ACID Compliance**: Ensures data consistency
- **Performance**: Excellent for complex queries and joins
- **Maturity**: Well-established with great Python support

### 14.2 Why APScheduler for Background Jobs?
- **Simplicity**: No external dependencies (Redis, RabbitMQ)
- **In-Process**: Runs within FastAPI application, easier deployment
- **Sufficient for Use Case**: Handles periodic sync and analysis tasks
- **Async Support**: Works well with async/await in FastAPI
- **Lower Overhead**: No message broker, fewer moving parts
- **Easy Development**: Simpler local development setup
- **Good Enough**: For single-server deployment with moderate load

**Note**: If you need distributed task processing at scale, Celery can be added later.

### 14.3 Why FastAPI?
- **Performance**: Async support for high concurrency
- **Type Safety**: Pydantic integration for validation
- **Auto Documentation**: OpenAPI/Swagger docs auto-generated
- **Modern**: Built on modern Python features
- **WebSocket Support**: For real-time features (future)

### 14.4 Why React + TypeScript?
- **Type Safety**: Catch errors at compile time
- **Component Reusability**: Build once, use everywhere
- **Rich Ecosystem**: Large library of components and tools
- **Developer Experience**: Hot reload, great debugging
- **Community**: Large community and extensive resources

### 14.5 Why shadcn/ui?
- **Customizable**: Components are copied into your project
- **Accessible**: Built with accessibility in mind
- **Modern**: Beautiful, modern design
- **TailwindCSS**: Consistent styling approach
- **No Lock-in**: You own the code

## 15. Future Enhancements (Post-MVP)

- **AI-Powered Insights**: GPT-based content summarization
- **Slack Integration**: Notifications for updates
- **Advanced Filtering**: Save custom filters
- **Export Features**: Export data to CSV/PDF
- **Mobile App**: Native mobile experience
- **Collaboration**: Comments and annotations
- **Automation**: Automated reporting
