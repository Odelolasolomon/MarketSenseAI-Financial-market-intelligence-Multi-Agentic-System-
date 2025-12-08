"""
Tests for Application Services
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.application.services.data_service import DataService
from src.application.services.analysis_service import AnalysisService
from src.domain.value_objects.timeframe import TimeframeVO


class TestDataService:
    """Tests for Data Service"""
    
    @pytest.mark.asyncio
    @patch('src.application.services.data_service.BinanceClient')
    async def test_get_market_data(self, mock_binance):
        """Test getting market data"""
        # Setup mock
        mock_binance_instance = AsyncMock()
        mock_binance_instance.get_24h_ticker = AsyncMock(return_value={
            "lastPrice": "45000",
            "openPrice": "44000",
            "highPrice": "46000",
            "lowPrice": "43000",
            "volume": "1000000",
            "quoteVolume": "45000000000",
            "priceChangePercent": "2.27"
        })
        mock_binance.return_value.__aenter__.return_value = mock_binance_instance
        
        service = DataService()
        
        with patch.object(service.cache, 'get', return_value=None):
            with patch.object(service.cache, 'set', return_value=True):
                result = await service.get_market_data("BTC")
                
                assert result is not None
                assert result.asset_symbol == "BTC"
                assert result.price == 45000.0
                assert result.change_24h == 2.27
    
    @pytest.mark.asyncio
    @patch('src.application.services.data_service.CoinGeckoClient')
    async def test_get_trending_assets(self, mock_coingecko):
        """Test getting trending assets"""
        # Setup mock
        mock_cg_instance = AsyncMock()
        mock_cg_instance.get_trending = AsyncMock(return_value={
            "coins": [{"item": {"id": "bitcoin", "name": "Bitcoin"}}]
        })
        mock_cg_instance.get_global_data = AsyncMock(return_value={
            "data": {"total_market_cap": {"usd": 2000000000000}}
        })
        mock_coingecko.return_value.__aenter__.return_value = mock_cg_instance
        
        service = DataService()
        result = await service.get_trending_assets()
        
        assert "trending_coins" in result
        assert "global_data" in result


class TestAnalysisService:
    """Tests for Analysis Service"""
    
    @pytest.mark.asyncio
    async def test_analysis_service_initialization(self):
        """Test service initialization"""
        service = AnalysisService()
        assert service.synthesis_agent is not None
        assert service.cache is not None
    
    @pytest.mark.asyncio
    async def test_analyze_with_cache(self):
        """Test analysis with cached result"""
        service = AnalysisService()
        
        cached_data = {
            "query": "Test query",
            "asset_symbol": "BTC",
            "executive_summary": "Test",
            "investment_thesis": "Test",
            "outlook": "bullish",
            "overall_confidence": 0.75,
            "risk_level": "medium",
            "risk_score": 0.3,
            "trading_action": "buy",
            "position_sizing": "medium",
            "time_horizon": "medium",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }
        
        with patch.object(service.cache, 'get', return_value=cached_data):
            result = await service.analyze(
                "Test query",
                "BTC",
                TimeframeVO.medium()
            )
            
            assert result.asset_symbol == "BTC"
 
 