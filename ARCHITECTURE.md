# Voice Business Onboarding - Architecture Documentation

## Overview

The Voice Business Onboarding system is a web-based application that uses speech-to-text and natural language understanding to automate business profile and product catalog creation. The system is built with a Flask backend and vanilla JavaScript frontend, leveraging AI models for intelligent data extraction.

## System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend        │    │   AI Services   │
│                 │    │                  │    │                 │
│ - HTML5 UI      │◄──►│ - Flask API      │◄──►│ - Whisper STT   │
│ - JavaScript    │    │ - Session Mgmt   │    │ - Groq LLM      │
│ - Audio Recording│    │ - File Storage  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Component Architecture

### 1. Frontend Layer

#### 1.1 User Interface Components
- **Recording Interface**: Voice recording controls with visual feedback
- **Transcription Display**: Real-time transcription preview
- **Data Editor**: Edit forms for business and product information
- **JSON Viewer**: Final data display with export options

#### 1.2 JavaScript Modules
```javascript
// Core Modules
- Audio Recording (MediaRecorder API)
- HTTP Client (Fetch API)
- UI State Management
- Form Validation
- Timer Management
```

#### 1.3 Key Features
- **Responsive Design**: Mobile-first approach with CSS Grid/Flexbox
- **Progressive Enhancement**: Works without JavaScript (basic functionality)
- **Accessibility**: ARIA labels, keyboard navigation
- **Error Handling**: User-friendly error messages and recovery

### 2. Backend Layer

#### 2.1 Flask Application Structure
```
app.py
├── Configuration & Setup
├── AI Model Initialization
├── Session Management
├── Business Extraction Logic
├── Product Extraction Logic
├── API Endpoints
└── File Management
```

#### 2.2 Core Components

##### 2.2.1 Audio Processing
```python
def transcribe_audio(path):
    segments, _ = model.transcribe(path, beam_size=5, language="en")
    return " ".join(seg.text.strip() for seg in segments)
```

##### 2.2.2 Business Information Extraction
```python
def extract_business_info(text):
    # LLM prompt engineering for structured extraction
    # Returns JSON with business details
```

##### 2.2.3 Product Information Extraction
```python
def extract_products(text):
    # Specialized LLM prompt for product details
    # Handles units, prices, and quantities
```

#### 2.3 Session Management
- **File-based Sessions**: JSON files in `/data` directory
- **Unique Identifiers**: Timestamp-based naming
- **Data Persistence**: Automatic saving after each phase
- **Edit Tracking**: Version control for changes

### 3. AI Services Integration

#### 3.1 Whisper Speech-to-Text
- **Model**: Medium (balanced accuracy/speed)
- **Configuration**: CPU-optimized with int8 quantization
- **Language**: English-only (configurable)
- **Output**: Clean transcription text

#### 3.2 Groq LLM Integration
- **Model**: Llama 3.3 70B Versatile
- **Use Case**: Natural language understanding
- **Prompt Engineering**: Structured extraction prompts
- **Response Parsing**: JSON extraction and validation

## Data Flow Architecture

### Phase 1: Business Information Flow
```
User Speech → Audio Recording → Whisper STT → Transcription Text → 
Groq LLM → Structured JSON → Frontend Display → User Edit → Save
```

### Phase 2: Product Information Flow
```
User Speech → Audio Recording → Whisper STT → Transcription Text → 
Groq LLM → Product JSON → Merge with Business Data → Frontend Display → 
User Edit → Save
```

## API Architecture

### Endpoints

#### 1. Business Audio Upload
```
POST /upload_business_audio
Content-Type: multipart/form-data
Body: audio file (webm)
Response: {
  "data": { business_details },
  "filename": "session_timestamp.json",
  "transcription": "text"
}
```

#### 2. Product Audio Upload
```
POST /upload_product_audio
Content-Type: multipart/form-data
Body: audio file (webm)
Response: {
  "data": { business_and_products },
  "filename": "session_timestamp.json",
  "transcription": "text"
}
```

#### 3. Save Edited Data
```
POST /save
Content-Type: application/json
Body: {
  "filename": "session_timestamp.json",
  "data": { edited_data }
}
Response: {
  "success": true,
  "message": "Data saved successfully"
}
```

#### 4. View Session Data
```
GET /editor
Response: Latest session data or "No sessions found"
```

### Error Handling
- **400 Bad Request**: Missing data or validation errors
- **500 Internal Server**: AI service failures
- **Audio Errors**: Microphone access, format issues
- **Network Errors**: Connection problems, timeouts

## Data Models

### Business Data Structure
```json
{
  "name": "string",
  "address": "string",
  "city": "string",
  "category": "Retail|Food & Restaurant|Services|Manufacturing|Healthcare|Education|Technology",
  "subcategory": "string",
  "phone": "string",
  "products": [
    {
      "name": "string",
      "unit": "string",
      "price": "number"
    }
  ]
}
```

### Session File Structure
```
data/
├── session_20260202_002522.json
├── session_20260202_014530.json
└── session_20260202_023415.json
```

## Security Architecture

### 1. Input Validation
- **Audio Files**: Format validation (webm)
- **JSON Data**: Schema validation
- **File Paths**: Path traversal prevention
- **API Keys**: Environment variable storage

### 2. Data Privacy
- **Local Processing**: Audio processed locally
- **No Cloud Storage**: Data stored on server only
- **Session Isolation**: Separate files per session
- **Data Retention**: Manual cleanup required

### 3. API Security
- **CORS Configuration**: Restricted origins
- **Rate Limiting**: Basic implementation possible
- **Input Sanitization**: XSS prevention
- **Error Messages**: Non-sensitive error details

## Performance Architecture

### 1. Optimization Strategies
- **Lazy Loading**: Components loaded on demand
- **Audio Compression**: WebM format optimization
- **Caching**: Session data in memory
- **Async Processing**: Non-blocking operations

### 2. Resource Management
- **Memory**: Whisper model optimization (int8)
- **CPU**: Efficient transcription processing
- **Storage**: JSON file management
- **Network**: Minimal API calls

### 3. Scalability Considerations
- **Horizontal Scaling**: Multiple Flask instances
- **Load Balancing**: Nginx reverse proxy
- **Database Migration**: PostgreSQL for production
- **Caching Layer**: Redis for session data

## Deployment Architecture

### Development Environment
```
Local Machine
├── Python 3.8+
├── Flask Development Server
├── Local File System
└── Environment Variables (.env)
```

### Production Architecture (Recommended)
```
Load Balancer (Nginx)
├── Flask Application Servers (Gunicorn)
├── AI Model Servers (GPU for Whisper)
├── Database (PostgreSQL)
├── Cache (Redis)
└── File Storage (AWS S3)
```

### Container Architecture
```dockerfile
# Multi-stage build
FROM python:3.9-slim as base
# Install dependencies
FROM base as runtime
# Copy application
# Expose port 5000
```

## Monitoring & Logging

### 1. Application Logging
```python
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

### 2. Performance Metrics
- **Response Times**: API endpoint latency
- **AI Processing**: STT and LLM processing time
- **Error Rates**: Success/failure ratios
- **Resource Usage**: CPU, memory, disk

### 3. User Analytics
- **Session Duration**: Time spent per phase
- **Edit Frequency**: User correction patterns
- **Success Rate**: Completed onboarding percentage
- **Error Types**: Common user issues

## Testing Architecture

### 1. Unit Tests
```python
# Test AI extraction functions
def test_business_extraction():
    # Test with various inputs
    
def test_product_extraction():
    # Test unit/price extraction
```

### 2. Integration Tests
- **API Endpoints**: Request/response validation
- **AI Services**: Mock external dependencies
- **File Operations**: Session management
- **Error Scenarios**: Failure handling

### 3. End-to-End Tests
- **User Workflows**: Complete onboarding flow
- **Browser Testing**: Cross-browser compatibility
- **Mobile Testing**: Responsive design validation
- **Performance Testing**: Load and stress testing

## Future Architecture Enhancements

### 1. Microservices Migration
```
API Gateway
├── Audio Service (Whisper)
├── NLU Service (Groq)
├── Session Service
├── User Service
└── Notification Service
```

### 2. Event-Driven Architecture
```
Event Bus (Kafka/RabbitMQ)
├── Audio Processing Events
├── Data Extraction Events
├── User Action Events
└── System Events
```

### 3. Cloud-Native Features
- **Serverless Functions**: AWS Lambda for AI processing
- **Managed Services**: AWS Transcribe, Comprehend
- **Auto-scaling**: Dynamic resource allocation
- **Global CDN**: Static asset distribution

## Technology Rationale

### Why Flask?
- **Lightweight**: Minimal overhead for simple APIs
- **Flexibility**: Easy integration with AI services
- **Python Ecosystem**: Rich ML/AI library support
- **Rapid Development**: Quick prototyping capabilities

### Why Whisper?
- **Accuracy**: High-quality transcription
- **Open Source**: No vendor lock-in
- **Local Processing**: Data privacy maintained
- **Flexibility**: Multiple model sizes available

### Why Groq?
- **Speed**: Ultra-fast inference
- **Cost-Effective**: Generous free tier
- **Quality**: State-of-the-art LLM
- **API Simplicity**: Easy integration

### Why Vanilla JavaScript?
- **Performance**: No framework overhead
- **Compatibility**: Universal browser support
- **Simplicity**: Easy maintenance
- **Learning**: Clear implementation patterns

---

*Last Updated: February 5, 2026*
*Version: 1.0*
*Architect: Ekthaa Technologies*
