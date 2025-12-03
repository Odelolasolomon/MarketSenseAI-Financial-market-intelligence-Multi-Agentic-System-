"""
API Connection Diagnostic Script
Tests all external API connections and RAG service
"""
import asyncio
from src.adapters.external.binance_client import BinanceClient
from src.adapters.external.coingecko_client import CoinGeckoClient
from src.adapters.external.fred_client import FREDClient
from src.adapters.external.newsapi_client import NewsAPIClient
from src.application.services.rag_service import RAGService
from src.utilities.logger import get_logger
from src.config.settings import get_settings

logger = get_logger(__name__)
settings = get_settings()


async def test_binance():
    """Test Binance API connection"""
    print("\n" + "="*60)
    print("TESTING BINANCE API")
    print("="*60)
    try:
        async with BinanceClient() as client:
            # Test ticker
            ticker = await client.get_24h_ticker("BTCUSDT")
            print(f"✓ Binance connected successfully")
            print(f"  BTC Price: ${ticker['lastPrice']}")
            print(f"  24h Change: {ticker['priceChangePercent']}%")
            
            # Test klines
            klines = await client.get_klines("BTCUSDT", interval="1d", limit=5)
            print(f"✓ Retrieved {len(klines)} historical candles")
            return True
    except Exception as e:
        print(f"✗ Binance FAILED: {str(e)}")
        return False


async def test_coingecko():
    """Test CoinGecko API connection"""
    print("\n" + "="*60)
    print("TESTING COINGECKO API")
    print("="*60)
    try:
        async with CoinGeckoClient() as client:
            # Test simple price
            price_data = await client.get_simple_price(
                coin_ids=["bitcoin"],
                include_24h_change=True
            )
            print(f"✓ CoinGecko connected successfully")
            print(f"  BTC Price: ${price_data['bitcoin']['usd']}")
            print(f"  24h Change: {price_data['bitcoin']['usd_24h_change']:.2f}%")
            
            # Test market chart
            chart = await client.get_market_chart("bitcoin", days=7)
            print(f"✓ Retrieved {len(chart['prices'])} historical price points")
            
            # Test coin data
            coin_data = await client.get_coin_data("bitcoin")
            print(f"✓ Retrieved comprehensive coin data")
            print(f"  Market Cap Rank: #{coin_data['market_cap_rank']}")
            return True
    except Exception as e:
        print(f"✗ CoinGecko FAILED: {str(e)}")
        return False


async def test_fred():
    """Test FRED API connection"""
    print("\n" + "="*60)
    print("TESTING FRED API")
    print("="*60)
    
    if not settings.fred_api_key:
        print(f"✗ FRED API key not configured")
        return False
    
    try:
        async with FREDClient() as client:
            # Test getting series
            gdp = await client.get_series("GDP")
            print(f"✓ FRED connected successfully")
            print(f"  Retrieved GDP data: {len(gdp)} observations")
            
            unemployment = await client.get_series("UNRATE")
            print(f"  Retrieved Unemployment data: {len(unemployment)} observations")
            return True
    except Exception as e:
        print(f"✗ FRED FAILED: {str(e)}")
        return False


async def test_newsapi():
    """Test NewsAPI connection"""
    print("\n" + "="*60)
    print("TESTING NEWSAPI")
    print("="*60)
    
    if not settings.newsapi_key:
        print(f"✗ NewsAPI key not configured")
        return False
    
    try:
        async with NewsAPIClient() as client:
            # Test getting news
            articles = await client.get_everything(
                query="Bitcoin",
                page_size=5
            )
            print(f"✓ NewsAPI connected successfully")
            print(f"  Retrieved {len(articles)} articles")
            if articles:
                print(f"  Latest: {articles[0]['title'][:60]}...")
            return True
    except Exception as e:
        print(f"✗ NewsAPI FAILED: {str(e)}")
        return False


async def test_rag_service():
    """Test RAG service"""
    print("\n" + "="*60)
    print("TESTING RAG SERVICE")
    print("="*60)
    try:
        rag = RAGService()
        
        # Test adding documents
        test_docs = [
            {
                "text": "Bitcoin is a decentralized cryptocurrency",
                "metadata": {"type": "test", "source": "diagnostic"}
            },
            {
                "text": "The Federal Reserve controls monetary policy",
                "metadata": {"type": "test", "source": "diagnostic"}
            }
        ]
        
        success = await rag.add_documents(test_docs, "crypto")
        if success:
            print(f"✓ Successfully added test documents")
        else:
            print(f"✗ Failed to add documents")
            return False
        
        # Test querying
        results = await rag.query_collection("Bitcoin cryptocurrency", "crypto", n_results=2)
        print(f"✓ Query returned {len(results)} results")
        
        if results:
            print(f"  Top result: {results[0]['text'][:60]}...")
            print(f"  Distance: {results[0]['distance']:.4f}")
            return True
        else:
            print(f"✗ No results returned from query")
            return False
            
    except Exception as e:
        print(f"✗ RAG Service FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def check_api_keys():
    """Check which API keys are configured"""
    print("\n" + "="*60)
    print("API KEY CONFIGURATION")
    print("="*60)
    
    keys = {
        "Binance API Key": bool(settings.binance_api_key),
        "Binance Secret": bool(settings.binance_api_secret),
        "CoinGecko API Key": bool(settings.coingecko_api_key),
        "FRED API Key": bool(settings.fred_api_key),
        "NewsAPI Key": bool(settings.newsapi_key),
        "Groq API Key": bool(settings.groq_api_key),
    }
    
    for key_name, configured in keys.items():
        status = "✓ Configured" if configured else "✗ Missing"
        print(f"  {key_name}: {status}")
    
    print(f"\n  ChromaDB Directory: {settings.chroma_persist_directory}")


async def main():
    """Run all diagnostic tests"""
    print("\n" + "="*60)
    print("MULTI-ASSET AI - API DIAGNOSTIC TOOL")
    print("="*60)
    
    # Check API keys first
    await check_api_keys()
    
    # Run tests
    results = {
        "Binance": await test_binance(),
        "CoinGecko": await test_coingecko(),
        "FRED": await test_fred(),
        "NewsAPI": await test_newsapi(),
        "RAG Service": await test_rag_service(),
    }
    
    # Summary
    print("\n" + "="*60)
    print("DIAGNOSTIC SUMMARY")
    print("="*60)
    
    for service, status in results.items():
        status_text = "✓ WORKING" if status else "✗ FAILED"
        print(f"  {service}: {status_text}")
    
    working = sum(results.values())
    total = len(results)
    print(f"\n  Overall: {working}/{total} services working")
    
    if working < total:
        print("\n  ⚠ WARNING: Some services are not working!")
        print("  Your analysis results may be incomplete or inaccurate.")
        print("  Please check your API keys and network connection.")
    else:
        print("\n  ✓ All services are working correctly!")


if __name__ == "__main__":
    asyncio.run(main()) 