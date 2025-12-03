"""
FRED (Federal Reserve Economic Data) API Client
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import aiohttp 
from src.config.settings import get_settings
from src.utilities.logger import get_logger
from src.error_trace.exceptions import ExternalAPIError

logger = get_logger(__name__)
settings = get_settings()


class FREDClient:
    """Client for FRED API"""
    
    BASE_URL = "https://api.stlouisfed.org/fred"
    
    # Common economic indicators
    INDICATORS = {
        "fed_funds_rate": "FEDFUNDS",
        "inflation_cpi": "CPIAUCSL",
        "unemployment": "UNRATE",
        "gdp": "GDP",
        "pce": "PCE",
        "treasury_10y": "DGS10",
        "treasury_2y": "DGS2",
        "m2_money_supply": "M2SL",
        "retail_sales": "RSXFS",
        "industrial_production": "INDPRO"
    }
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.fred_api_key
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _request(
        self,
        endpoint: str,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make API request"""
        if not self.api_key:
            raise ExternalAPIError(
                message="FRED API key not configured",
                api_name="fred"
            )
        
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        url = f"{self.BASE_URL}/{endpoint}"
        params = params or {}
        params["api_key"] = self.api_key
        params["file_type"] = "json"
        
        try:
            async with self.session.get(
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status != 200:
                    text = await response.text()
                    raise ExternalAPIError(
                        message=f"FRED API error: {text}",
                        api_name="fred",
                        status_code=response.status
                    )
                
                return await response.json()
                
        except aiohttp.ClientError as e:
            logger.error(f"FRED API request error: {str(e)}")
            raise ExternalAPIError(
                message=f"FRED connection error: {str(e)}",
                api_name="fred"
            )
    
    async def get_series(
        self,
        series_id: str,
        observation_start: Optional[str] = None,
        observation_end: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get economic data series
        
        Args:
            series_id: FRED series ID
            observation_start: Start date (YYYY-MM-DD)
            observation_end: End date (YYYY-MM-DD)
            limit: Number of observations
            
        Returns:
            Series data
        """
        endpoint = "series/observations"
        
        params = {
            "series_id": series_id,
            "limit": limit,
            "sort_order": "desc"
        }
        
        if observation_start:
            params["observation_start"] = observation_start
        if observation_end:
            params["observation_end"] = observation_end
        
        return await self._request(endpoint, params)
    
    async def get_latest_value(self, series_id: str) -> Optional[float]:
        """
        Get latest value for a series
        
        Args:
            series_id: FRED series ID
            
        Returns:
            Latest value or None
        """
        data = await self.get_series(series_id, limit=1)
        observations = data.get("observations", [])
        
        if observations:
            value = observations[0].get("value")
            try:
                return float(value) if value != "." else None
            except (ValueError, TypeError):
                return None
        return None
    
    async def get_multiple_series(
        self,
        series_ids: List[str],
        days_back: int = 90
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get multiple series data
        
        Args:
            series_ids: List of FRED series IDs
            days_back: Number of days of historical data
            
        Returns:
            Dictionary mapping series IDs to their data
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        results = {}
        for series_id in series_ids:
            try:
                data = await self.get_series(
                    series_id,
                    observation_start=start_date.strftime("%Y-%m-%d"),
                    observation_end=end_date.strftime("%Y-%m-%d")
                )
                results[series_id] = data.get("observations", [])
            except Exception as e:
                logger.error(f"Error fetching series {series_id}: {str(e)}")
                results[series_id] = []
        
        return results
    
    async def get_economic_indicators(self) -> Dict[str, Any]:
        """
        Get current values for key economic indicators
        
        Returns:
            Dictionary of indicator values
        """
        indicators = {}
        
        for name, series_id in self.INDICATORS.items():
            try:
                value = await self.get_latest_value(series_id)
                indicators[name] = {
                    "value": value,
                    "series_id": series_id,
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                logger.error(f"Error fetching {name}: {str(e)}")
                indicators[name] = {
                    "value": None,
                    "series_id": series_id,
                    "error": str(e)
                }
        
        return indicators