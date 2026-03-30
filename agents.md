# AI Agents in Consent Dashboard

This document outlines the AI agents and intelligent services implemented in the Consent Dashboard project.

## Overview

The Consent Dashboard incorporates several AI-powered agents to assist with consent engineering work, providing intelligent analysis, Q&A capabilities, and context-aware assistance.

## Implemented Agents

### 1. Chatbot Service (`ChatbotService`)

**Location**: `backend/app/services/chatbot_service.py`

**Purpose**: Developer-focused Q&A and idea formulation assistant that helps engineers implement consent functionality by providing contextual answers based on Confluence documentation and Aha user stories.

**Core Capabilities**:
- **Contextual Q&A**: Answers questions about consent implementation using indexed Confluence pages and Aha features
- **Smart Matching**: Uses token-based matching with term aliases (e.g., "crdb" → "cockroachdb") to find relevant content
- **Source Attribution**: Provides sources for answers with links to original Confluence pages and Aha features
- **Fallback Responses**: Gracefully handles cases where no relevant content is found
- **Azure OpenAI Integration**: Uses Azure OpenAI for intelligent response generation when configured

**Key Methods**:
- `ask(message, context_title, context_hint)`: Main Q&A interface
- `_match_items(items, query, key)`: Intelligent content matching
- `_generate_answer()`: AI-powered response generation

**Integration Points**:
- `AhaService`: Fetches user stories and features
- `ConfluenceService`: Fetches documentation pages
- `AzureOpenAIService`: Provides AI chat capabilities

### 2. Cosmos Assistant Service (`CosmosAssistantService`)

**Location**: `backend/app/services/cosmos_assistant_service.py`

**Purpose**: Cosmos DB diagnostics assistant that helps developers prepare queries, explain diagnostics results, and optimize database performance.

**Core Capabilities**:
- **Query Assistance**: Helps prepare and optimize Cosmos SQL queries
- **Diagnostics Explanation**: Explains Cosmos DB diagnostic results in technical terms
- **Query Recreation**: Suggests improved queries based on diagnostics
- **Context-Aware**: Uses container info, partition keys, and current query context
- **SQL Extraction**: Automatically extracts suggested queries from AI responses

**Supported Actions**:
- `prepare_query`: Help create new queries
- `explain_response`: Explain diagnostics results
- `recreate_query`: Improve existing queries

**Key Methods**:
- `assist(payload)`: Main assistant interface
- `_build_prompt()`: Context-aware prompt generation
- `_extract_suggested_query()`: SQL query extraction from responses

**Integration Points**:
- `AzureOpenAIService`: Provides AI chat capabilities
- Cosmos DB diagnostics context and query analysis

### 3. Analysis Service (`AnalysisService`)

**Location**: `backend/app/services/analysis_service.py`

**Purpose**: Background analysis agent that processes consent-related content to extract insights, trends, and relationships.

**Core Capabilities**:
- **Content Summarization**: Generates summaries of recent activity
- **Keyword Extraction**: Identifies frequently mentioned terms across content
- **Trend Analysis**: Tracks changes over time
- **Activity Monitoring**: Monitors updates to Confluence pages and Aha features

**Key Methods**:
- `summary(days)`: Generates comprehensive analysis summary
- `_extract_tokens(text)`: Token extraction for keyword analysis

**Integration Points**:
- Database models for Confluence pages and Aha features
- Background job scheduler for periodic analysis

## Supporting AI Infrastructure

### Azure OpenAI Service (`AzureOpenAIService`)

**Location**: `backend/app/services/azure_openai_service.py`

**Purpose**: Centralized Azure OpenAI integration providing chat completion capabilities for all AI agents.

**Features**:
- Environment-based configuration
- Chat client management
- Error handling and fallback support
- Support for multiple deployment models

## Agent Architecture

### Design Principles

1. **Modular Design**: Each agent is self-contained with clear responsibilities
2. **Graceful Degradation**: All agents provide fallback responses when AI services are unavailable
3. **Context Awareness**: Agents leverage workspace context and user focus
4. **Source Attribution**: AI responses include references to source materials
5. **Error Handling**: Robust error handling with logging

### Common Patterns

**Fallback Responses**: All agents implement fallback logic when AI services are unavailable
```python
if not self.azure_openai_service.is_configured():
    return fallback_response
```

**Context Building**: Agents construct detailed prompts with relevant context
```python
prompt = (
    f"Action: {payload.action}\n"
    f"Container: {payload.container_name}\n"
    f"User request: {payload.prompt}\n"
    # ... additional context
)
```

**Source Integration**: Agents integrate with multiple data sources
- Confluence pages for documentation
- Aha features for user stories
- Database queries for technical context

## Configuration

### Environment Variables

All AI agents use environment-based configuration:

```bash
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
```

### Service Dependencies

- **PostgreSQL**: Data storage for all content
- **Azure OpenAI**: AI/LLM capabilities (optional - agents work with fallbacks)
- **External APIs**: Confluence and Aha for content ingestion

## Future Agent Enhancements

### Planned Capabilities

1. **Semantic Search**: Enhanced search using vector embeddings
2. **Code Generation**: Automatic code snippet generation for consent patterns
3. **Relationship Discovery**: Advanced relationship mapping between stories and documentation
4. **Predictive Analysis**: Trend prediction and proactive recommendations
5. **Multi-Modal Support**: Image and diagram analysis from Confluence

### Integration Opportunities

- **Azure AI Foundry**: Advanced AI capabilities and model management
- **LangChain**: Enhanced LLM orchestration and tool usage
- **Vector Databases**: Improved semantic search with pgvector
- **Knowledge Graphs**: Relationship visualization and discovery

## Usage Examples

### Chatbot Agent Usage

```python
chatbot = ChatbotService()
response = await chatbot.ask(
    message="How do I implement GDPR consent for mobile apps?",
    context_title="Mobile Consent Implementation",
    context_hint="Focus on iOS and Android patterns"
)
```

### Cosmos Assistant Usage

```python
assistant = CosmosAssistantService()
response = await assistant.assist(CosmosAssistantRequest(
    action="prepare_query",
    container_name="user-consents",
    logical_type="consent-record",
    prompt="Help me query all active consent records for EU users"
))
```

## Monitoring and Logging

All agents include comprehensive logging:
- Request/response logging
- Error tracking and reporting
- Performance metrics
- Fallback activation alerts

## Security Considerations

- **No Data Exposure**: Agents don't expose internal IDs in API responses
- **Context Limitation**: Agents operate within scoped consent engineering context
- **Input Validation**: All user inputs are validated and sanitized
- **Error Sanitization**: Error messages don't expose sensitive system information
