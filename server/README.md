# ScioScribe Backend API

AI-powered research co-pilot backend with intelligent data cleaning and analysis capabilities.

## 🚀 Features

### Phase 1: Foundation ✅
- **Multi-format File Processing** - CSV, Excel (XLSX/XLS) support
- **Data Preview Generation** - Automatic data analysis and statistics
- **RESTful API** - Complete endpoints with automatic documentation
- **Background Processing** - Async file handling for better performance
- **Error Handling** - Comprehensive validation and error management

### Phase 2: AI-Powered Analysis ✅
- **OpenAI Integration** - GPT-4o-mini for cost-effective data analysis
- **Data Quality Agent** - AI-powered quality issue detection
- **Intelligent Suggestions** - Actionable recommendations with confidence scoring
- **Multiple Analysis Types**:
  - Data type inference and validation
  - Missing value analysis
  - Consistency issue detection
  - Outlier identification
- **Quality Scoring** - Automatic data quality assessment

## 🛠️ Setup

### Prerequisites
- Python 3.11+
- Virtual environment (recommended)
- OpenAI API key (for AI features)

### Installation

1. **Clone and navigate to the server directory**
   ```bash
   cd server
   ```

2. **Activate virtual environment**
   ```bash
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   # Create .env file (copy from .env.example)
   cp .env.example .env
   ```

   Edit `.env` file with your settings:
   ```env
   # Required for AI features
   OPENAI_API_KEY=sk-your-openai-api-key-here
   
   # Optional configurations
   OPENAI_MODEL=gpt-4o-mini
   OPENAI_MAX_TOKENS=1000
   OPENAI_TEMPERATURE=0.1
   ```

5. **Start the server**
   ```bash
   uvicorn main:app --reload --port 8000
   ```

## 🔑 OpenAI Setup

### Getting Your API Key
1. Visit [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create an account or sign in
3. Generate a new API key
4. Copy the key (starts with `sk-`)

### Setting the API Key
```bash
# Option 1: Environment variable
export OPENAI_API_KEY='sk-your-key-here'

# Option 2: Add to .env file
echo "OPENAI_API_KEY=sk-your-key-here" >> .env
```

### Verifying Setup
```bash
python -c "from config import validate_openai_config; print('✅ OpenAI configured!' if validate_openai_config() else '❌ OpenAI not configured')"
```

## 📡 API Endpoints

### Core Endpoints
- **`GET /`** - Health check and API info
- **`GET /health`** - System health status
- **`GET /docs`** - Interactive API documentation (Swagger UI)

### Data Cleaning Endpoints
- **`POST /api/dataclean/upload-file`** - Upload and process files
- **`GET /api/dataclean/data-artifact/{id}`** - Get processing status and AI suggestions
- **`POST /api/dataclean/apply-suggestion`** - Apply AI-generated suggestions
- **`POST /api/dataclean/update-notes`** - Add user notes to data
- **`POST /api/dataclean/finalize-data/{id}`** - Mark data ready for analysis

### Example Usage

#### 1. Upload a File
```bash
curl -X POST "http://localhost:8000/api/dataclean/upload-file" \
  -F "file=@your-data.csv" \
  -F "experiment_id=my-experiment"
```

#### 2. Check Processing Status
```bash
curl -X GET "http://localhost:8000/api/dataclean/data-artifact/{artifact_id}"
```

#### 3. Apply AI Suggestion
```bash
curl -X POST "http://localhost:8000/api/dataclean/apply-suggestion" \
  -H "Content-Type: application/json" \
  -d '{"artifact_id": "your-id", "suggestion_id": "suggestion-id", "action": "accept"}'
```

## 🤖 AI Features

### Data Quality Analysis
The AI agent automatically analyzes uploaded data for:

1. **Data Type Issues**
   - Numeric data stored as text
   - Date formats that need standardization
   - Categorical data inconsistencies

2. **Missing Value Patterns**
   - Identifies columns with missing data
   - Suggests appropriate handling strategies
   - Calculates impact on data quality

3. **Consistency Problems**
   - Inconsistent categorical values (e.g., 'Yes', 'Y', 'yes')
   - Format inconsistencies
   - Capitalization and spacing issues

4. **Outlier Detection**
   - Statistical outlier identification
   - Context-aware outlier assessment
   - Risk evaluation for outlier handling

### AI Suggestions
Each suggestion includes:
- **Action**: Specific steps to fix the issue
- **Confidence**: AI confidence score (0.0-1.0)
- **Risk Level**: Impact assessment (low/medium/high)
- **Explanation**: Why this suggestion helps

### Quality Scoring
Automatic calculation based on:
- Number of issues found
- Severity of issues
- Data completeness
- Overall data health

## 🔧 Configuration Options

### Model Settings
```env
OPENAI_MODEL=gpt-4o-mini          # Cost-effective model
OPENAI_MAX_TOKENS=1000            # Response length limit
OPENAI_TEMPERATURE=0.1            # Low temperature for consistent analysis
```

### File Upload Settings
```env
MAX_FILE_SIZE=52428800            # 50MB limit
ALLOWED_FILE_TYPES=.csv,.xlsx,.xls,.png,.jpg,.jpeg,.pdf
TEMP_DIR=/tmp                     # Temporary file storage
```

### CORS Settings
```env
CORS_ORIGINS=*                    # Configure for production
```

## 🔍 Monitoring & Debugging

### Logs
The application provides detailed logging for:
- File processing status
- AI analysis progress
- Error tracking
- Performance metrics

### Without OpenAI
The system gracefully degrades when OpenAI is not configured:
- File processing still works
- Basic data preview is generated
- No AI suggestions are provided
- Clear warnings in logs

## 🧪 Testing

### Test File Processing
```python
from agents.dataclean.file_processor import FileProcessingAgent
processor = FileProcessingAgent()
# Test with your files
```

### Test AI Integration (requires OpenAI key)
```python
from config import get_openai_client
from agents.dataclean.quality_agent import DataQualityAgent

client = get_openai_client()
agent = DataQualityAgent(client)
# Test with sample data
```

## 📈 Performance

### Expected Response Times
- **File Upload**: < 1 second (up to 50MB)
- **File Processing**: 5-30 seconds (depending on size)
- **AI Analysis**: 10-60 seconds (depending on data complexity)
- **Suggestion Generation**: 5-20 seconds per issue

### Cost Optimization
- Uses `gpt-4o-mini` for cost-effective analysis
- Analyzes sample data (not entire datasets)
- Batches multiple analysis types
- Caches common patterns

## 🔜 Roadmap

### Phase 3: Advanced Features
- OCR support for image-based data
- Audio transcription capabilities
- Handwriting recognition
- Firebase/Firestore integration
- Real-time collaboration features

## 🛡️ Security

### Data Privacy
- Files are processed locally and cleaned up automatically
- OpenAI data retention policies apply to AI features
- No training data usage (opt-out configured)
- Temporary file cleanup after processing

### API Security
- CORS configuration for production
- Input validation and sanitization
- Rate limiting (planned)
- Authentication (planned)

## 🐛 Troubleshooting

### Common Issues

1. **OpenAI API Key Not Working**
   ```bash
   # Check key format
   echo $OPENAI_API_KEY | grep "^sk-"
   
   # Test key validity
   curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models
   ```

2. **File Upload Fails**
   - Check file size (max 50MB)
   - Verify file format (CSV, Excel)
   - Check available disk space

3. **AI Analysis Fails**
   - Verify OpenAI API key
   - Check internet connection
   - Review OpenAI usage limits

### Getting Help
- Check the `/docs` endpoint for API documentation
- Review application logs for detailed error messages
- Ensure all environment variables are properly set

## 📄 License

Part of the ScioScribe AI Research Co-pilot project. 