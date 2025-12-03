"""
Analysis Entity - Represents analysis results
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.config.constants import MarketOutlook, TradingAction, RiskLevel


@dataclass
class AgentAnalysis:
    """Individual agent analysis result"""
    
    agent_name: str
    summary: str
    confidence: float
    key_factors: List[str] = field(default_factory=list)
    data_sources: List[str] = field(default_factory=list)
    detailed_analysis: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "agent_name": self.agent_name,
            "summary": self.summary,
            "confidence": self.confidence,
            "key_factors": self.key_factors,
            "data_sources": self.data_sources,
            "detailed_analysis": self.detailed_analysis,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class Analysis:
    """Comprehensive analysis result"""
    
    query: str
    asset_symbol: str
    executive_summary: str
    investment_thesis: str
    outlook: MarketOutlook
    overall_confidence: float
    risk_level: RiskLevel
    risk_score: float
    trading_action: TradingAction
    position_sizing: str
    entry_points: List[float] = field(default_factory=list)
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    time_horizon: str = "medium"
    bullish_factors: List[str] = field(default_factory=list)
    bearish_factors: List[str] = field(default_factory=list)
    critical_factors: List[str] = field(default_factory=list)
    key_risks: List[str] = field(default_factory=list)
    risk_mitigations: List[str] = field(default_factory=list)
    macro_analysis: Optional[AgentAnalysis] = None
    technical_analysis: Optional[AgentAnalysis] = None
    sentiment_analysis: Optional[AgentAnalysis] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate analysis"""
        if not 0 <= self.overall_confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1")
        
        if not 0 <= self.risk_score <= 1:
            raise ValueError("Risk score must be between 0 and 1")
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "query": self.query,
            "asset_symbol": self.asset_symbol,
            "executive_summary": self.executive_summary,
            "investment_thesis": self.investment_thesis,
            "outlook": self.outlook.value,
            "overall_confidence": self.overall_confidence,
            "risk_level": self.risk_level.value,
            "risk_score": self.risk_score,
            "trading_action": self.trading_action.value,
            "position_sizing": self.position_sizing,
            "entry_points": self.entry_points,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "time_horizon": self.time_horizon,
            "bullish_factors": self.bullish_factors,
            "bearish_factors": self.bearish_factors,
            "critical_factors": self.critical_factors,
            "key_risks": self.key_risks,
            "risk_mitigations": self.risk_mitigations,
            "macro_analysis": self.macro_analysis.to_dict() if self.macro_analysis else None,
            "technical_analysis": self.technical_analysis.to_dict() if self.technical_analysis else None,
            "sentiment_analysis": self.sentiment_analysis.to_dict() if self.sentiment_analysis else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }