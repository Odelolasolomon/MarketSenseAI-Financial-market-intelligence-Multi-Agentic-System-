# MarketSenseAI: Multi-Asset Financial Intelligence System

**Advanced multi-agent AI system for comprehensive cryptocurrency market analysis** using specialized AI agents with access to real-time on-chain data and news sources.

## 📖 What is MarketSense?

MarketSenseAI is an intelligent financial analysis platform that combines the power of multiple specialized AI agents to provide institutional-grade cryptocurrency market insights. Unlike traditional analysis tools that rely on a single AI model, MarketSense employs a **coordinated multi-agent architecture** where each agent specializes in a specific aspect of market analysis:

- **Macro Economic Analysis**: Monitors global economic indicators, monetary policy, and institutional trends
- **Technical Analysis**: Analyzes price action, technical indicators, and market structure across multiple timeframes
- **Sentiment Analysis**: Gauges market psychology from social media, news, and on-chain metrics
- **Synthesis & Coordination**: Intelligently combines insights from all agents to generate actionable recommendations

### 🎯 Key Differentiators

**1. Real-Time Multi-Source Data Integration**
- Live price data from CoinGecko and Binance APIs
- Economic indicators from FRED (Federal Reserve Economic Data)
- Social sentiment from Reddit (15+ cryptocurrency subreddits)
- Breaking news from NewsAPI, Serper, and financial news aggregators
- On-chain metrics and market depth analysis

**2. Intelligent Conversation Memory**
- **Asset-Specific Conversations**: Separate conversation threads for each cryptocurrency
- **Smart Caching**: Avoids redundant analysis by caching results for 30 minutes
- **Context Awareness**: Gemini AI maintains full conversation context for natural follow-up questions
- **Instant Responses**: Follow-up questions leverage cached data for sub-second response times

**3. Production-Grade Architecture**
- **Clean Architecture**: Domain-Driven Design with clear separation of concerns
- **Async Processing**: All agents run in parallel using Python asyncio for maximum performance
- **Scalable Infrastructure**: PostgreSQL database, Redis caching, and horizontal scaling support
- **Comprehensive Error Handling**: Graceful degradation and detailed logging

**4. Modern User Experience**
- **Next.js 16 Frontend**: Fast, responsive UI with Turbopack
- **Streaming Responses**: Real-time AI responses using Gemini 2.5 Flash
- **Interactive Chat Interface**: Natural language queries with conversation history
- **Multi-Asset Support**: Seamlessly switch between different cryptocurrencies

## 🌟 Key Features

- **Multi-Agent Architecture**: Four specialized AI agents (Macro, Technical, Sentiment, Synthesis) working in coordinated parallel execution
- **RAG-Powered Analysis**: Context-aware insights using ChromaDB vector store with semantic search
- **Real-time Market Data**: Live integration with Binance, CoinGecko, FRED, Reddit, and news APIs
- **Conversational Memory**: Maintains context across conversations with asset-specific conversation threads and 30-minute smart caching
- **Interactive Frontend**: Next.js 16 web interface with streaming AI responses and conversation history
- **Clean Architecture**: Domain-Driven Design with proper separation of concerns and async processing
- **Production-Ready**: PostgreSQL database, Redis caching, comprehensive error handling, and horizontal scaling support


## 🏗️ System Architecture

![MarketSense System Architecture](./Sys.jpg)

The diagram above illustrates the complete system architecture, showing how data flows through our multi-agent system, from data sources through specialist agents to the synthesis layer, and finally to the user interface.



## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.10+** (Python 3.11 recommended)
- **Node.js 18+** and npm/pnpm
- **PostgreSQL 15+** (or SQLite for development)
- **Redis 7+** (optional, for caching)
- **API Keys**:
  - Groq API (for AI agents)
  - Google Generative AI (for frontend chat)
  - CoinGecko API (for crypto data)
  - FRED API (for economic data)
  - NewsAPI/Serper (for news sentiment)

## 🚀 Quick Start Guide

### 1. Clone the Repository

```bash
git clone <repository-url>
cd multi-asset-ai
```

### 2. Backend Setup

#### Install Python Dependencies

We use `uv` for fast dependency management. First, create and activate a virtual environment:

**Windows (PowerShell):**
```powershell
# Create virtual environment
python -m venv uv

# Activate
.\uv\Scripts\Activate
```

**macOS/Linux:**
```bash
# Create virtual environment
python -m venv uv

# Activate
source uv/bin/activate
```

#### Install Dependencies with uv

```bash
# Install uv if you haven't already
pip install uv

# Sync dependencies (recommended - keeps environment clean)
uv pip sync requirements.txt

# Alternative: install without removing extras
# uv pip install -r requirements.txt
```

#### Configure Environment Variables

Create a `.env` file in the project root:

```env
# API Keys
GROQ_API_KEY=your_groq_api_key_here
FRED_API_KEY=your_fred_api_key_here
COINGECKO_API_KEY=your_coingecko_api_key_here
NEWSAPI_KEY=your_newsapi_key_here
SERPER_API_KEY=your_serper_api_key_here

# Database (SQLite for development)
DATABASE_URL=sqlite:///./multiasset.db

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=True

# Agent Settings
LLM_MODEL=llama-3.3-70b-versatile
AGENT_TEMPERATURE= None
MAX_AGENT_ITERATIONS=None

# Logging
LOG_LEVEL=INFO
```

#### Start the Backend Server

```bash
python -m src.entry_scripts.start_api
```

The API will be available at:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/

### 3. Frontend Setup

Navigate to the frontend directory and install dependencies:

```bash
cd frontend

# Install dependencies (choose one)
npm install
# or
pnpm install
```

#### Configure Frontend Environment

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_BASE_API_URL=http://localhost:8000
GOOGLE_GENERATIVE_AI_API_KEY=your_google_ai_key_here
```

> **Important**: Enable the Google Generative Language API for your project at:
> https://console.developers.google.com/apis/api/generativelanguage.googleapis.com

#### Start the Frontend Development Server

```bash
npm run dev
# or
pnpm dev
```

The frontend will be available at: **http://localhost:3000**

### 4. Access the Application

Open your browser and navigate to:
- **Frontend UI**: http://localhost:3000/chat
- **API Documentation**: http://localhost:8000/docs

## 📁 Project Structure

```
multi-asset-ai/
├── src/                           # Backend source code
│   ├── adapters/                  # External integrations & web layer
│   │   ├── external/              # API clients (Binance, CoinGecko, NewsAPI, etc.)
│   │   └── web/                   # FastAPI routes and application
│   ├── application/               # Business logic layer
│   │   ├── agents/                # AI agents (Macro, Technical, Sentiment, Synthesis)
│   │   └── services/              # Application services (Analysis, RAG, Memory, etc.)
│   ├── config/                    # Configuration and constants
│   ├── domain/                    # Domain layer (entities & value objects)
│   │   ├── entities/              # Business entities (Analysis, Conversation, etc.)
│   │   └── value_objects/         # Immutable value objects (Timeframe, etc.)
│   ├── infrastructure/            # Infrastructure layer
│   │   ├── database.py            # Database manager (PostgreSQL/SQLite)
│   │   ├── cache.py               # Redis cache manager
│   │   └── orm.py                 # SQLAlchemy ORM mappings
│   ├── utilities/                 # Helper functions and utilities
│   └── entry_scripts/             # Application entry points
│       └── start_api.py           # FastAPI server startup
├── frontend/                      # Next.js web interface
│   ├── app/                       # Next.js app directory
│   │   ├── api/chat/              # Chat API route
│   │   └── chat/                  # Chat page
│   ├── components/                # React components
│   │   ├── ai-elements/           # AI chat UI components
│   │   ├── ui/                    # shadcn/ui components
│   │   └── sidebar.tsx            # Conversation history sidebar(for future integrations)
│   └── lib/                       # Utility functions
├── tests/                         # Unit and integration tests
├── docs/                          # Documentation
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

## 🔑 API Endpoints

### Core Analysis Endpoints

#### Health Check
```bash
GET /
GET /api/v1/health
```

#### Analyze Market (Primary Endpoint)
```bash
POST /api/v1/analyze
Content-Type: application/json

{
  "query": "Should I invest in buying Bitcoin now?",
  "asset": "BTC",
  "timeframe": "medium",
  "session_id": "optional-session-uuid",
  "conversation_id": "optional-conversation-uuid"
}
```

**Response:**
```json
{
  "query": "Should I invest in buying Bitcoin now?",
  "asset_symbol": "BTC",
  "analysis": {
    "executive_summary": "...",
    "investment_thesis": "...",
    "outlook": "bullish",
    "overall_confidence": 0.75,
    "trading_action": "buy",
    "position_sizing": "medium",
    "macro_analysis": {...},
    "technical_analysis": {...},
    "sentiment_analysis": {...}
  },
  "confidence": 0.75,
  "timestamp": "2025-12-07T16:00:00"
}
```

#### Quick Analysis
```bash
GET /api/v1/analyze/BTC?timeframe=medium
```



### Market Data Endpoints

#### Get Market Data
```bash
GET /api/v1/market/{symbol}
```

#### Get Trending Assets
```bash
GET /api/v1/trending
```

## 🤖 The Multi-Agent System

### Agent Architecture

The system uses four specialized AI agents that work together to provide comprehensive market analysis:

#### 1. **Macro Analyst** (`MacroAnalyst`)
- **Purpose**: Analyzes macroeconomic conditions affecting crypto markets
- **Data Sources**: 
  - FRED Economic Data (interest rates, inflation, GDP)
  - Crypto-specific news (regulatory changes, institutional adoption)
- **Output**: Macroeconomic context, policy impacts, institutional trends

#### 2. **Technical Analyst** (`TechnicalAnalyst`)
- **Purpose**: Analyzes price action and technical indicators
- **Data Sources**:
  - CoinGecko API (price, volume, market cap)
  - Historical price data
- **Analysis**:
  - Multi-timeframe trends (1h, 24h, 7d, 14d, 30d)
  - Technical indicators (RSI, MACD, Moving Averages)
  - Support/resistance levels
  - Liquidity metrics and orderbook depth

#### 3. **Sentiment Analyst** (`SentimentAnalyst`)
- **Purpose**: Gauges market sentiment from news and social media
- **Data Sources**:
  - Reddit (r/Bitcoin, r/Cryptocurrency, etc.)
  - News APIs (Serper, NewsAPI)
  - Financial news websites
- **Analysis**:
  - News sentiment scoring
  - Social media trends
  - Market narratives
  - Fear & Greed indicators

#### 4. **Synthesis Agent** (`SynthesisAgent`)
- **Purpose**: Coordinates all agents and synthesizes final recommendations
- **Process**:
  1. Distributes query to all specialist agents (parallel execution)
  2. Collects and analyzes agent outputs
  3. Identifies agreements and contradictions
  4. Generates unified investment thesis
  5. Provides actionable recommendations with confidence scores
- **Output**: Executive summary, trading action, position sizing, risk assessment

### RAG (Retrieval-Augmented Generation)(Was Optional)

The system uses ChromaDB(optional) for vector storage and retrieval:

- **Collections**:
  - `macro_data`: Economic indicators and policy data
  - `crypto_data`: Cryptocurrency market data
  - `news_sentiment`: News articles and sentiment analysis
- **Embedding Model**: `all-MiniLM-L6-v2` (SentenceTransformers)
- **Purpose**: Provides context-aware analysis by retrieving relevant historical data



## 🎯 Usage Examples

### Python SDK Example

```python
import asyncio
from src.application.services.analysis_service import AnalysisService
from src.domain.value_objects.timeframe import TimeframeVO

async def analyze_bitcoin():
    service = AnalysisService()
    
    result = await service.analyze(
        query="Should I buy Bitcoin now?",
        asset_symbol="BTC",
        timeframe=TimeframeVO.from_string("medium"),
        context={
            "session_id": "my-session-id",
            "conversation_id": "my-conversation-id"
        }
    )
    
    print(f"Outlook: {result.outlook}")
    print(f"Confidence: {result.overall_confidence}")
    print(f"Action: {result.trading_action}")
    print(f"Position Size: {result.position_sizing}")
    print(f"\nExecutive Summary:\n{result.executive_summary}")

# Run the analysis
asyncio.run(analyze_bitcoin())
```

### cURL Example

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Analyze Bitcoin market conditions",
    "asset": "BTC",
    "timeframe": "medium"
  }'
```

### Frontend Usage

1. Navigate to http://localhost:3000/chat
2. Type your investment question (e.g., "Should I buy Bitcoin?")
3. Select the asset and timeframe
4. Click send or press Enter
5. View the comprehensive analysis from all agents


## 🔧 Configuration

### Environment Variables Reference

#### Required API Keys

```env
# AI Model (Groq)
GROQ_API_KEY=gsk_...

# Frontend AI (Google Gemini)
GOOGLE_GENERATIVE_AI_API_KEY=AIza...

# Data Sources
COINGECKO_API_KEY=CG-...
FRED_API_KEY=...
NEWSAPI_KEY=...
SERPER_API_KEY=...
```

#### Database Configuration

```env
# PostgreSQL (Production)
DATABASE_URL=postgresql://user:password@localhost:5432/multiasset

# SQLite (Development)
DATABASE_URL=sqlite:///./multiasset.db
```

#### Redis Configuration

```env
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=1800  # 30 minutes
```

#### Agent Configuration

```env
LLM_MODEL=llama-3.3-70b-versatile
AGENT_TEMPERATURE=0.7
MAX_AGENT_ITERATIONS=5
```

## 💡 Use Cases & Real-World Applications

### 1. **Day Trading Decisions**
- **Scenario**: Quick market entry/exit decisions
- **How MarketSense Helps**: 
  - Real-time technical analysis with RSI, MACD indicators
  - Sentiment analysis from latest news and social media
  - Risk assessment with stop-loss recommendations
- **Example Query**: "Should I buy Bitcoin now for a short-term trade?"

### 2. **Long-Term Investment Analysis**
- **Scenario**: Building a crypto portfolio for the long term
- **How MarketSense Helps**:
  - Macro analysis of economic conditions and regulatory landscape
  - Fundamental analysis of project viability
  - Multi-timeframe trend analysis (30d, 90d, 1y)
- **Example Query**: "Is Ethereum a good long-term investment for the next 2 years?"

### 3. **Portfolio Rebalancing**
- **Scenario**: Adjusting portfolio allocation based on market conditions
- **How MarketSense Helps**:
  - Comparative analysis across multiple assets
  - Risk-adjusted position sizing recommendations
  - Correlation analysis between assets
- **Example Query**: "Should I increase my BTC allocation and reduce ETH?"

### 4. **Risk Assessment**
- **Scenario**: Understanding potential downside before investing
- **How MarketSense Helps**:
  - Comprehensive risk scoring (0-100)
  - Identification of key risk factors
  - Risk mitigation strategies
- **Example Query**: "What are the main risks of investing in Bitcoin right now?"

### 5. **Market Research**
- **Scenario**: Understanding market dynamics and trends
- **How MarketSense Helps**:
  - Aggregated insights from multiple data sources
  - Historical context and pattern recognition
  - Narrative analysis from news and social media
- **Example Query**: "What's driving the recent Bitcoin price movement?"

## 📊 Performance Metrics

### Response Times
- **First Query (Cold Start)**: ~8-12 seconds
  - Includes data fetching from all sources
  - Parallel agent execution
  - Vector database retrieval
- **Cached Query**: ~2-4 seconds
  - Redis cache hit for recent similar queries
  - Reduced API calls
- **Subsequent Queries (Same Session)**: ~6-10 seconds
  - Conversational memory reduces context gathering

### Data Coverage
- **Data Sources Queried**: 5-7 per analysis
  - CoinGecko (price data)
  - FRED (economic indicators)
  - NewsAPI/Serper (news sentiment)
  - Reddit (social sentiment)
  - Binance (market depth)
- **Historical Data Range**: Up to 1 year
- **Update Frequency**: Real-time to 15-minute intervals

### Analysis Depth
- **Specialist Agents**: 4 (Macro, Technical, Sentiment, Synthesis)
- **Data Points Analyzed**: 50-100+ per query
- **Confidence Scoring**: 0.0-1.0 scale with explanation
- **Risk Factors Identified**: Typically 5-10 per analysis

### Accuracy Metrics
- **Sentiment Accuracy**: ~75-85% (based on news correlation)
- **Technical Signal Reliability**: Varies by market conditions
- **Macro Trend Identification**: High accuracy for major trends
- **Note**: Past performance does not guarantee future results

## 💻 System Requirements

### Minimum Requirements
- **CPU**: 2 cores, 2.0 GHz
- **RAM**: 4 GB
- **Storage**: 2 GB free space
- **Network**: Stable internet connection (1 Mbps+)
- **OS**: Windows 10+, macOS 10.15+, Ubuntu 20.04+

### Recommended Requirements
- **CPU**: 4+ cores, 3.0 GHz
- **RAM**: 8 GB+
- **Storage**: 5 GB+ SSD
- **Network**: Broadband connection (10 Mbps+)
- **OS**: Latest stable versions

### For Production Deployment
- **CPU**: 8+ cores
- **RAM**: 16 GB+
- **Storage**: 20 GB+ SSD
- **Database**: PostgreSQL 15+ (dedicated server recommended)
- **Cache**: Redis 7+ (dedicated instance)
- **Network**: High-speed connection with low latency

### API Rate Limits Considerations
- **Groq API**: 30 requests/minute (free tier)
- **CoinGecko**: 10-50 calls/minute (depending on plan)
- **NewsAPI**: 100 requests/day (free tier)
- **FRED**: 120 requests/minute

## 🆚 Comparison with Alternatives

| Feature | MarketSenseAI | Traditional Platforms | Single-AI Tools | Manual Research |
|---------|---------------|----------------------|-----------------|-----------------|
| **Multi-Agent Analysis** | ✅ 4 specialist agents | ❌ Single perspective | ⚠️ 1 generalist AI | ❌ Manual only |
| **Real-time Data** | ✅ Multiple sources | ✅ Limited sources | ⚠️ Varies | ❌ Time-consuming |
| **Risk Assessment** | ✅ Comprehensive scoring | ⚠️ Basic metrics | ⚠️ Generic | ✅ Subjective |
| **Customization** | ✅ Open-source | ❌ Proprietary | ❌ Closed | ✅ Fully custom |
| **Cost** | 💰 API costs only | 💰💰💰 Subscription fees | 💰💰 Monthly fees | 💰 Time investment |
| **Technical Analysis** | ✅ good indicators | ✅ Professional tools | ⚠️ Basic | ⚠️ Manual charts |
| **Sentiment Analysis** | ✅ News + Social media | ⚠️ News only | ⚠️ Limited | ❌ Manual reading |
| **Macro Analysis** | ✅ Economic indicators | ⚠️ Basic | ❌ Not included | ✅ Research required |
| **Speed** | ⚡ 8-12 seconds | ⚡ Instant (limited) | ⚡ 5-10 seconds | 🐌 Hours/Days |
| **Transparency** | ✅ Full reasoning shown | ⚠️ Black box | ⚠️ Limited | ✅ Your analysis |
| **Learning Curve** | ⚠️ Moderate | ⚠️ Steep | ✅ Easy | ⚠️ Steep |

**Legend**: ✅ Excellent | ⚠️ Partial/Limited | ❌ Not Available | 💰 Cost Level

## ❓ Frequently Asked Questions (FAQ)

### General Questions

**Q: How accurate are the predictions?**  
A: MarketSenseAI provides analysis and insights, not predictions. The system aggregates data from multiple sources and provides confidence scores (0.0-1.0) for its recommendations. Accuracy varies by market conditions. Always conduct your own research and never invest more than you can afford to lose.

**Q: Can I use this for automated trading bots?**  
A: While the API can be integrated with trading systems, MarketSenseAI is designed for decision support, not automated trading. We strongly recommend human oversight for all trading decisions. The system does not execute trades.

**Q: What's the cost to run MarketSenseAI?**  
A: The software is free and open-source. Costs include:
- API keys (Groq, CoinGecko, etc.) - $0-50/month depending on usage
- Server hosting (if deploying) - $5-50/month
- Database (PostgreSQL) - Free (self-hosted) or $10-30/month (managed)

**Q: How often is data updated?**  
A: Data freshness varies by source:
- Price data: Real-time to 1-minute intervals
- News sentiment: 15-minute to 1-hour intervals
- Economic indicators: Daily to monthly (depends on indicator)
- Social media: Hourly aggregation

**Q: Is my data private and secure?**  
A: Yes. All data is stored locally in your database.  API calls to external services (Groq, CoinGecko) follow their respective privacy policies.

### Technical Questions

**Q: Can I run this on my laptop?**  
A: Yes! The system works on modern laptops with 4GB+ RAM. Performance is better with 8GB+ RAM and SSD storage.

**Q: Do I need a GPU?**  
A: No. The system uses cloud-based AI APIs (Groq) for inference, so no local GPU is required.

**Q: Can I add support for stocks or forex?**  
A: Yes! The architecture is designed to be extensible. You can add new data sources and adapt the agents for other asset classes. See the "Adding a New Data Source" section.

**Q: How do I update to the latest version?**  
A: Pull the latest changes from the repository and reinstall dependencies:
```bash
git pull origin master
uv pip sync requirements.txt
cd frontend && npm install
```

**Q: Can I deploy this to the cloud?**  
A: Yes! The system supports deployment to platforms like Render, Railway, Heroku, AWS, or DigitalOcean. See the Docker deployment section.

### Usage Questions

**Q: What assets are supported?**  
A: Currently optimized for major cryptocurrencies (BTC, ETH, etc.). The system can analyze any asset with available data from CoinGecko.

**Q: Can I analyze multiple assets at once?**  
A: Currently, each query analyzes one asset. For portfolio analysis, make separate queries and compare results.

**Q: How far back does historical analysis go?**  
A: Technical analysis uses up to 1 year of historical data. Macro analysis considers longer-term economic trends.

**Q: Can I export the analysis results?**  
A: Yes! Analysis results are stored in the database and can be exported via the API or database queries.

**Q: Does it work offline?**  
A: No. The system requires internet connectivity to fetch real-time data and access AI APIs.

### Troubleshooting

**Q: Why am I getting API rate limit errors?**  
A: Free tier API keys have rate limits. Consider upgrading to paid tiers or implementing request throttling. The system includes caching to reduce API calls.

**Q: The analysis is taking too long. How can I speed it up?**  
A: Enable Redis caching, use a faster internet connection, and ensure your database is optimized. Consider upgrading API tiers for faster response times.

**Q: Can I use different AI models?**  
A: Yes! The system is designed to be model-agnostic. You can configure different models in the `.env` file. Currently supports Groq's models.



## 🐳 Docker Deployment (Optional)

### Using Docker Compose

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Services

- **API**: FastAPI backend (port 8000)
- **Frontend**: Next.js app (port 3000)
- **PostgreSQL**: Database (port 5432)
- **Redis**: Cache (port 6379)

## 🔍 Troubleshooting

### Common Issues

#### 1. Database Connection Error

**Error**: `sqlite3.OperationalError: no such table: analysis`

**Solution**: The database tables are created automatically on first run. If you see this error, restart the backend:

```bash
# Stop the server (Ctrl+C)
# Start again
python -m src.entry_scripts.start_api
```

#### 2. Frontend API Connection Error

**Error**: `Failed to fetch` or `Network Error`

**Solution**: Ensure backend is running and environment variables are correct:

```bash
# Check backend is running
curl http://localhost:8000/

# Verify frontend .env.local
cat frontend/.env.local
```

#### 3. Google AI API Error

**Error**: `Generative Language API has not been used in project...`

**Solution**: Enable the API at:
https://console.developers.google.com/apis/api/generativelanguage.googleapis.com

#### 4. Missing Dependencies

**Error**: `ModuleNotFoundError: No module named '...'`

**Solution**: Reinstall dependencies:

```bash
# Activate virtual environment
source uv/Scripts/Activate  # Windows
source uv/bin/activate      # macOS/Linux

# Reinstall
uv pip sync requirements.txt
```

#### 5. Port Already in Use

**Error**: `Address already in use`

**Solution**: Kill the process using the port:

```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# macOS/Linux
lsof -ti:8000 | xargs kill -9
```

## 📊 Performance Optimization

- **Caching**: Redis caches analysis results for 30 minutes
- **Parallel Processing**: All agents run concurrently using `asyncio.gather()`
- **Database Indexing**: Indexed queries on `asset_symbol`, `created_at`
- **Rate Limiting**: Built-in protection for external API calls
- **Connection Pooling**: SQLAlchemy connection pool for database efficiency

## 🔒 Security Features

- **API Key Validation**: All external API calls use secure key management
- **Input Validation**: Pydantic models validate all API inputs
- **SQL Injection Protection**: SQLAlchemy ORM prevents SQL injection
- **CORS Configuration**: Configurable CORS for frontend-backend communication
- **Environment Variables**: Sensitive data stored in `.env` (not committed to git)

## 🛠️ Development

### Code Style

```bash
# Format code
black src/

# Lint
flake8 src/

# Type checking
mypy src/
```

### Adding a New Agent

1. Create new agent file in `src/application/agents/`
2. Inherit from `BaseAgent`
3. Implement required methods:
   ```python
   class MyNewAgent(BaseAgent):
       async def analyze(self, query: str, context: dict) -> dict:
           # Your analysis logic
           pass
       
       def get_system_prompt(self) -> str:
           # Your agent's system prompt
           pass
   ```
4. Register in `SynthesisAgent.analyze()`

### Adding a New Data Source

1. Create client in `src/adapters/external/`
2. Implement async methods for data fetching
3. Add to `DataService` or relevant service
4. Update agent to use new data source

## 📚 Additional Documentation

- **Architecture Guide**: See `docs/architecture.md` (coming soon)
- **API Reference**: http://localhost:8000/docs (when running)
- **Agent Development**: See agent source files for examples

## Future Directions 
### Conversation Management Endpoints

#### Get User Conversations
```bash
GET /api/v1/conversations/user/{user_id}
```

#### Get Conversation History
```bash
GET /api/v1/conversations/sessions/{session_id}/conversations/{conversation_id}
```

#### Create Session
```bash
POST /api/v1/conversations/sessions
{
  "user_id": "user-uuid"
}
```

#### Conversational Memory

- **Implementation**: LangChain `ConversationBufferWindowMemory`
- **Window Size**: Last 5 conversations per user
- **Storage**: In-memory with Redis caching
- **Purpose**: Maintains context across multiple queries in a session

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and commit: `git commit -m 'Add amazing feature'`
4. Push to your branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Contribution Guidelines

- Follow existing code style (use `black` for formatting)
- Add tests for new features
- Update documentation as needed
- Ensure all tests pass before submitting PR

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

**Important**: This system is for informational and educational purposes only. It does NOT give financial advice. 

- Always conduct your own research (DYOR)
- Consult with qualified financial advisors before making investment decisions
- Cryptocurrency investments carry significant risk
- Past performance does not guarantee future results

## 🙏 Acknowledgments

- **AI Providers**: OpenAI, Anthropic (Claude), Groq, Google (Gemini)
- **Frameworks**: LangChain, FastAPI, Next.js, React
- **Data Sources**: CoinGecko, Binance, FRED, NewsAPI, Reddit
- **Storage**: ChromaDB, PostgreSQL, Redis
- **UI Components**: shadcn/ui, Radix UI
- **Community**: All open-source contributors

## 📞 Support & Contact

- **Issues**: [GitHub Issues](https://github.com/yourusername/multi-asset-ai/issues)
- **Email1**: odelolasolomon5@gmail.com
- **Email2**: kingsleyibekwe.c@gmail.com
- **Email3**: danielokpara29@gmail.com

---

**Built with ❤️ by the MarketSense Team**

*Empowering informed investment decisions through AI-powered multi-agent analysis*






