from sqlalchemy import Table, Column, Integer, String, Float, DateTime, JSON, Text, TypeDecorator, ForeignKey
from sqlalchemy.orm import registry
from src.infrastructure.database import metadata
from src.domain.entities.analysis import Analysis, AgentAnalysis
from src.domain.entities.conversation import ConversationContext, ConversationMessage
from src.config.constants import MarketOutlook, TradingAction, RiskLevel
import json
from datetime import datetime

mapper_registry = registry()

class AgentAnalysisType(TypeDecorator):
    """Custom type for saving AgentAnalysis as JSON"""
    impl = JSON
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, AgentAnalysis):
            return value.to_dict()
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        # Convert dictionary back to AgentAnalysis object
        try:
            # Handle timestamp conversion if it's a string
            if "timestamp" in value and isinstance(value["timestamp"], str):
                 try:
                     value["timestamp"] = datetime.fromisoformat(value["timestamp"])
                 except:
                     pass
            
            # AgentAnalysis might have extra fields in detailed_analysis that are just passed through
            return AgentAnalysis(**value)
        except Exception:
            return value

analysis_table = Table(
    "analysis",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("query", Text, nullable=False),
    Column("asset_symbol", String(20), nullable=False),
    Column("executive_summary", Text, nullable=False),
    Column("investment_thesis", Text, nullable=False),
    Column("outlook", String(20), nullable=False),
    Column("overall_confidence", Float, nullable=False),
    Column("risk_level", String(20), nullable=False),
    Column("risk_score", Float, nullable=False),
    Column("trading_action", String(20), nullable=False),
    Column("position_sizing", String(50), nullable=False),
    Column("entry_points", JSON, nullable=True),
    Column("stop_loss", Float, nullable=True),
    Column("take_profit", Float, nullable=True),
    Column("time_horizon", String(20), default="medium"),
    Column("bullish_factors", JSON, nullable=True),
    Column("bearish_factors", JSON, nullable=True),
    Column("critical_factors", JSON, nullable=True),
    Column("key_risks", JSON, nullable=True),
    Column("risk_mitigations", JSON, nullable=True),
    # Use custom type for complex objects
    Column("macro_analysis", AgentAnalysisType, nullable=True),
    Column("technical_analysis", AgentAnalysisType, nullable=True),
    Column("sentiment_analysis", AgentAnalysisType, nullable=True),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
    Column("metadata", JSON, nullable=True),
)

# Conversations table
conversations_table = Table(
    "conversations",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("conversation_id", String(36), unique=True, nullable=False, index=True),
    Column("user_id", String(36), nullable=False, index=True),
    Column("session_id", String(36), nullable=False),
    Column("asset_symbol", String(20), nullable=True),
    Column("created_at", DateTime, nullable=False),
    Column("last_updated", DateTime, nullable=False),
    Column("message_count", Integer, default=0),
    Column("previous_outlook", String(20), nullable=True),
    Column("previous_confidence", Float, nullable=True),
    Column("previous_action", String(20), nullable=True),
    Column("metadata", JSON, nullable=True),
)

# Messages table
messages_table = Table(
    "messages",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("message_id", String(36), unique=True, nullable=False, index=True),
    Column("conversation_id", String(36), nullable=False, index=True),
    Column("role", String(20), nullable=False),  # 'user' or 'assistant'
    Column("content", Text, nullable=False),
    Column("timestamp", DateTime, nullable=False),
    Column("metadata", JSON, nullable=True),
)

def start_mappers():
    """Start ORM mappers"""
    # Check if already mapped to avoid errors on reload
    if mapper_registry.mappers:
        return

    # Map Analysis entity
    mapper_registry.map_imperatively(
        Analysis,
        analysis_table,
        properties={
            # Map enums to strings
            "outlook": analysis_table.c.outlook,
            "risk_level": analysis_table.c.risk_level,
            "trading_action": analysis_table.c.trading_action,
        }
    )
    
    # Map ConversationContext entity
    mapper_registry.map_imperatively(
        ConversationContext,
        conversations_table,
        properties={
            "conversation_id": conversations_table.c.conversation_id,
            "user_id": conversations_table.c.user_id,
            "session_id": conversations_table.c.session_id,
            "asset_symbol": conversations_table.c.asset_symbol,
            "created_at": conversations_table.c.created_at,
            "last_updated": conversations_table.c.last_updated,
            "previous_outlook": conversations_table.c.previous_outlook,
            "previous_confidence": conversations_table.c.previous_confidence,
            "previous_action": conversations_table.c.previous_action,
            "metadata": conversations_table.c.metadata,
            # Note: messages list is not mapped here - will be loaded separately
        }
    )
    
    # Map ConversationMessage entity
    mapper_registry.map_imperatively(
        ConversationMessage,
        messages_table,
        properties={
            "id": messages_table.c.message_id,  # Map 'id' field to 'message_id' column
            "role": messages_table.c.role,
            "content": messages_table.c.content,
            "timestamp": messages_table.c.timestamp,
            "metadata": messages_table.c.metadata,
        }
    )
