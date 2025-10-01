# Recall AI 🧠

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

Recall AI is an intelligent Telegram bot that serves as your external brain, remembering everything for you and providing instant recall when needed. Built with advanced AI and vector search technology.

## ✨ Features

### 📄 **Advanced Document Processing**
- **PDF Files**: Extract text from regular and scanned PDFs with OCR support
- **Microsoft Office**: DOCX and PowerPoint (PPT/PPTX) with slide extraction
- **Web Content**: HTML files with clean text extraction and metadata
- **Text Formats**: Plain text (.txt) and Markdown (.md) files
- **Smart Limits**: Automatic page/word count validation (30 pages for PDFs, 50 slides for PowerPoint)

### 🌐 **Enhanced URL Processing**
- **Smart Web Scraping**: Extract content from websites with bot protection handling
- **Auto-Categorization**: Intelligent website classification (AI tools, sports, etc.)
- **Error Resilience**: Graceful handling of 404s, timeouts, and access restrictions
- **Metadata Extraction**: Title, content, and context preservation

### 🖼️ **Image Analysis**
- **OCR Technology**: Extract text from images and scanned documents
- **Visual Analysis**: AI-powered image understanding and description
- **Multiple Formats**: Support for common image formats

### 🎵 **Audio Processing**
- **Speech Recognition**: Convert MP3, WAV, OGG to text
- **Smart Transcription**: Handle various audio qualities and accents
- **Format Conversion**: Automatic audio format handling

### 🧠 **Intelligent Memory System**
- **LRU Cache**: Lightning-fast search with least-recently-used caching
- **Vector Search**: Advanced semantic search with Qdrant database
- **Cache-First Logic**: Instant results from recent queries
- **Smart Thresholds**: Optimized similarity scoring for better results

### 🔍 **Advanced Search & Memory Management**
- **Natural Language Queries**: Ask questions in plain English
- **Context-Aware Search**: Find related content across all stored materials
- **Memory Commands**: `/forget` and `/forgetall` for selective memory management
- **Preview Mode**: See what will be deleted before confirming
- **Batch Operations**: Efficient bulk memory operations

### 🔧 **Smart Content Recognition**
- **Auto-Detection**: Automatically detect questions vs. storage requests
- **List Queries**: Special handling for "list all" type queries
- **Content Categorization**: Smart tagging and organization
- **Metadata Preservation**: Store file types, sizes, and processing details

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- MongoDB
- Qdrant vector database
- Telegram Bot Token
- OpenAI API Key

### Installation

**⚠️ Use Virtual Environment to avoid dependency conflicts**

```bash
git clone https://github.com/UniquePratham/recall-ai.git
cd recall-ai
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1    # Windows PowerShell
# venv\Scripts\activate.bat    # Windows CMD  
# source venv/bin/activate     # Linux/Mac

pip install -r requirements.txt
cp .env.example .env           # Edit with your credentials
python create_collections.py  # Initialize database
python main.py                 # Start the bot
```

### 🚀 Railway Cloud Deployment (24/7 Operation)

Deploy to Railway for always-on cloud hosting:

```bash
# 1. Push to GitHub
git add . && git commit -m "Deploy to Railway" && git push

# 2. Deploy on Railway
# - Go to railway.app
# - Connect GitHub repo
# - Add environment variables
# - Auto-deploy with Dockerfile
```

**Railway Environment Variables**:
```env
BOT_TOKEN=your_telegram_bot_token
AI_PROVIDER=Gemini
GEMINI_API_KEY=your_gemini_api_key
QDRANT_URL=https://your-cluster.qdrant.tech:6333
QDRANT_API_KEY=your_qdrant_api_key
MONGODB_URI=your_mongodb_atlas_uri
SECRET_KEY=your_secret_key
```

**Cost**: $0-5/month (Railway free tier + Qdrant free tier)

### Docker Deployment (Local)

```bash
cp .env.example .env  # Edit with your credentials
docker-compose up -d
```

## 📖 Usage

### Commands
- `/start` - Initialize the bot and get welcome message
- `/help` - Show comprehensive help information  
- `/ask <question>` - Query your stored content with natural language
- `/forget` - Remove specific memories with preview and confirmation
- `/forgetall` - Clear all stored memories with safety confirmation
- `/activate <license_key>` - Activate with license key (if required)

### Content Processing
1. **Documents**: Send PDF, DOCX, PPT/PPTX files for automatic text extraction
2. **Web Content**: Send URLs or HTML files for content extraction and storage
3. **Text Files**: Send .txt or .md files for direct storage
4. **Images**: Send photos for OCR text extraction and visual analysis
5. **Audio**: Send voice messages or audio files for speech-to-text conversion
6. **Direct Text**: Type messages for immediate storage and indexing

### Smart Search Capabilities
- **Question Detection**: Automatically recognizes when you're asking vs. storing
- **List Queries**: Use "list all my..." to get comprehensive overviews
- **Semantic Search**: Find content by meaning, not just keywords
- **Cached Results**: Instant responses for recently searched queries
- **Cross-Content Search**: Find information across all your stored materials

## ⚙️ Configuration

### Multi-Provider AI Support

Recall AI supports multiple AI providers:
- **OpenAI** (GPT-4, GPT-3.5, embeddings)
- **Google Gemini** (gemini-1.5-flash, text-embedding-004)
- **Anthropic Claude** (claude-3-haiku, claude-3-sonnet)
- **GitHub Models** (Azure-hosted models)
- **Custom** (Your own API endpoint)

### Qdrant Cloud Configuration

Use Qdrant Cloud (free 1GB tier) for managed vector database:
1. Sign up at [cloud.qdrant.io](https://cloud.qdrant.io)
2. Create free cluster (no credit card required)
3. Copy cluster URL and API key

### Environment Setup

Create `.env` file:
```env
# Telegram Bot
BOT_TOKEN=your_telegram_bot_token

# Database
MONGODB_URI=mongodb://localhost:27017
DB_NAME=recall_ai

# AI Provider (OpenAI | Gemini | Claude | GitHub | Custom)
AI_PROVIDER=Gemini
AI_MODEL=gemini-1.5-flash
EMBEDDING_MODEL=text-embedding-004

# API Keys (use only the one for your provider)
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key
CLAUDE_API_KEY=your_claude_api_key
GITHUB_TOKEN=your_github_token

# Qdrant Cloud
QDRANT_URL=https://your-cluster-url.qdrant.tech:6333
QDRANT_API_KEY=your_qdrant_cloud_api_key
QDRANT_COLLECTION_NAME=recall_documents

# Security
SECRET_KEY=your_secret_key
```

## 🏗️ Project Structure

```
recall-ai/
├── main.py              # Application entry point
├── config.py            # Configuration management
├── handlers.py          # Telegram bot handlers and commands
├── processors.py        # Multi-format content processing
├── utils.py             # AI operations and enhanced search
├── database.py          # Database operations and management
├── cache_manager.py     # LRU cache and memory management
├── validators.py        # Input validation and security
├── exceptions.py        # Custom exception handling
├── logging_config.py    # Comprehensive logging setup
├── admin_tools.py       # Administration utilities
├── create_collections.py # Database initialization
├── requirements.txt     # Python dependencies
├── Dockerfile          # Production container definition
├── docker-compose.yml  # Multi-service development setup
├── railway.json        # Railway deployment configuration
└── .env.example        # Environment template with all options
```

## 🐳 Docker Support

The project includes comprehensive Docker support with optimized configurations:
- **Dockerfile**: Production-ready container with security best practices
- **docker-compose.yml**: Complete development environment with MongoDB and Qdrant
- **Multi-stage builds**: Optimized image sizes and build caching
- **Health checks**: Automatic service monitoring and restart capabilities
- **Volume persistence**: Data preservation across container restarts

## 🔧 Administration

Generate license keys:
```bash
python admin_tools.py
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes  
4. Test your changes
5. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Special thanks to **Raihan Khan** for creating the original Recall AI project and making it available under the MIT License. This implementation builds upon their foundational work while adding enhanced features and capabilities.

Original concept and base implementation: © 2024 Raihan Khan

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/UniquePratham/recall-ai/issues)
- **Documentation**: Check the code comments and docstrings

---

Made with ❤️ for intelligent memory assistance
