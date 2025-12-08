"""
MarketSenseAI Evaluation Framework
===================================

Comprehensive evaluation system using:
1. LLM-as-a-Judge for qualitative assessment
2. Quantitative metrics for performance
3. Historical accuracy tracking
4. Multi-dimensional scoring

This gives you a competitive edge by ensuring consistent, high-quality analysis.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import statistics
from groq import Groq
import pandas as pd

# Import your system components
from src.application.services.analysis_service import AnalysisService
from src.domain.value_objects.timeframe import TimeframeVO
from src.utilities.logger import get_logger

logger = get_logger(__name__)


@dataclass
class EvaluationMetrics:
    """Comprehensive evaluation metrics"""
    
    # LLM Judge Scores (0-100)
    coherence_score: float
    factual_accuracy_score: float
    reasoning_quality_score: float
    actionability_score: float
    risk_assessment_score: float
    overall_quality_score: float
    
    # Quantitative Metrics
    response_time_seconds: float
    data_sources_used: int
    confidence_score: float
    
    # Agent Performance
    macro_agent_score: float
    technical_agent_score: float
    sentiment_agent_score: float
    synthesis_quality_score: float
    
    # Consistency Metrics
    internal_consistency_score: float
    cross_agent_agreement_score: float
    
    # Metadata
    asset_symbol: str
    query: str
    timestamp: str
    evaluation_model: str
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def get_overall_score(self) -> float:
        """Calculate weighted overall score"""
        weights = {
            'quality': 0.30,  # LLM judge overall quality
            'reasoning': 0.25,  # Reasoning quality
            'actionability': 0.20,  # Practical usefulness
            'accuracy': 0.15,  # Factual accuracy
            'risk': 0.10,  # Risk assessment quality
        }
        
        return (
            self.overall_quality_score * weights['quality'] +
            self.reasoning_quality_score * weights['reasoning'] +
            self.actionability_score * weights['actionability'] +
            self.factual_accuracy_score * weights['accuracy'] +
            self.risk_assessment_score * weights['risk']
        )


class LLMJudge:
    """LLM-as-a-Judge evaluator using Groq"""
    
    def __init__(self, model: str = "llama-3.1-8b-instant"):
        import os
        from dotenv import load_dotenv
        
        # Load environment variables
        load_dotenv()
        
        # Get API key from environment
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError(
                "GROQ_API_KEY not found in environment variables. "
                "Please add it to your .env file."
            )
        
        self.client = Groq(api_key=api_key)
        self.model = model
    
    async def evaluate_analysis(
        self, 
        query: str, 
        analysis_result: Dict[str, Any],
        market_data: Optional[Dict] = None
    ) -> Dict[str, float]:
        """
        Evaluate analysis quality using LLM as judge
        
        Returns scores for:
        - Coherence (0-100)
        - Factual Accuracy (0-100)
        - Reasoning Quality (0-100)
        - Actionability (0-100)
        - Risk Assessment (0-100)
        - Overall Quality (0-100)
        """
        
        evaluation_prompt = self._create_evaluation_prompt(
            query, analysis_result, market_data
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_judge_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": evaluation_prompt
                    }
                ],
                temperature=0.1,  # Low temperature for consistent evaluation
                response_format={"type": "json_object"}
            )
            
            scores = json.loads(response.choices[0].message.content)
            return scores
            
        except Exception as e:
            logger.error(f"LLM Judge evaluation failed: {e}")
            return self._get_default_scores()
    
    def _get_judge_system_prompt(self) -> str:
        """System prompt for LLM judge"""
        return """You are an expert financial analysis evaluator. Your task is to objectively assess the quality of cryptocurrency market analysis.

Evaluate the analysis on these dimensions (score 0-100 for each):

1. **Coherence** (0-100): Is the analysis logically structured and easy to follow?
2. **Factual Accuracy** (0-100): Are the facts, data points, and market conditions accurately represented?
3. **Reasoning Quality** (0-100): Is the reasoning sound? Are conclusions well-supported by evidence?
4. **Actionability** (0-100): Does it provide clear, practical recommendations?
5. **Risk Assessment** (0-100): Are risks properly identified and quantified?
6. **Overall Quality** (0-100): Overall assessment of analysis quality

Provide scores as JSON:
{
  "coherence_score": 85,
  "factual_accuracy_score": 90,
  "reasoning_quality_score": 88,
  "actionability_score": 92,
  "risk_assessment_score": 87,
  "overall_quality_score": 88,
  "strengths": ["strength1", "strength2"],
  "weaknesses": ["weakness1", "weakness2"],
  "suggestions": ["suggestion1", "suggestion2"]
}

Be objective and critical. High scores (90+) should be rare and reserved for exceptional analysis."""
    
    def _create_evaluation_prompt(
        self, 
        query: str, 
        analysis: Dict[str, Any],
        market_data: Optional[Dict] = None
    ) -> str:
        """Create evaluation prompt"""
        
        prompt = f"""Evaluate this cryptocurrency market analysis:

**User Query**: {query}

**Analysis Output**:
- Asset: {analysis.get('asset_symbol', 'N/A')}
- Outlook: {analysis.get('outlook', 'N/A')}
- Confidence: {analysis.get('overall_confidence', 0):.2f}
- Trading Action: {analysis.get('trading_action', 'N/A')}
- Risk Level: {analysis.get('risk_level', 'N/A')}

**Executive Summary**:
{analysis.get('executive_summary', 'N/A')}

**Investment Thesis**:
{analysis.get('investment_thesis', 'N/A')}

**Risk Factors**:
{json.dumps(analysis.get('key_risks', []), indent=2)}

**Risk Mitigations**:
{json.dumps(analysis.get('risk_mitigations', []), indent=2)}
"""
        
        if market_data:
            prompt += f"\n**Actual Market Data** (for fact-checking):\n{json.dumps(market_data, indent=2)}\n"
        
        prompt += "\nProvide your evaluation scores and feedback in JSON format."
        
        return prompt
    
    def _get_default_scores(self) -> Dict[str, float]:
        """Default scores if evaluation fails"""
        return {
            "coherence_score": 50.0,
            "factual_accuracy_score": 50.0,
            "reasoning_quality_score": 50.0,
            "actionability_score": 50.0,
            "risk_assessment_score": 50.0,
            "overall_quality_score": 50.0,
            "strengths": [],
            "weaknesses": ["Evaluation failed"],
            "suggestions": []
        }


class AgentPerformanceEvaluator:
    """Evaluate individual agent performance"""
    
    @staticmethod
    def evaluate_agent_output(
        agent_name: str,
        agent_output: Dict[str, Any]
    ) -> float:
        """
        Evaluate individual agent output quality (0-100)
        
        Criteria:
        - Completeness of analysis
        - Relevance of insights
        - Data quality
        - Confidence calibration
        """
        score = 0.0
        
        # Check for required fields
        required_fields = ['summary', 'key_points', 'confidence']
        completeness = sum(
            1 for field in required_fields 
            if field in agent_output and agent_output[field]
        ) / len(required_fields)
        score += completeness * 30
        
        # Check key points quality
        key_points = agent_output.get('key_points', [])
        if len(key_points) >= 3:
            score += 20
        elif len(key_points) >= 1:
            score += 10
        
        # Check summary length (should be substantial)
        summary = agent_output.get('summary', '')
        if len(summary) > 200:
            score += 20
        elif len(summary) > 100:
            score += 10
        
        # Check confidence calibration
        confidence = agent_output.get('confidence', 0)
        if 0.3 <= confidence <= 0.9:  # Reasonable confidence range
            score += 15
        
        # Check for detailed analysis
        if agent_output.get('detailed_analysis'):
            score += 15
        
        return min(score, 100.0)
    
    @staticmethod
    def evaluate_cross_agent_consistency(
        macro_output: Dict,
        technical_output: Dict,
        sentiment_output: Dict
    ) -> float:
        """
        Evaluate consistency across agents (0-100)
        
        Higher score = agents agree more
        """
        # Extract outlooks/sentiments
        outlooks = []
        
        if 'outlook' in macro_output:
            outlooks.append(macro_output['outlook'])
        if 'trend' in technical_output:
            outlooks.append(technical_output['trend'])
        if 'sentiment' in sentiment_output:
            outlooks.append(sentiment_output['sentiment'])
        
        if len(outlooks) < 2:
            return 50.0  # Not enough data
        
        # Simple agreement check
        positive_terms = ['bullish', 'positive', 'uptrend', 'buy']
        negative_terms = ['bearish', 'negative', 'downtrend', 'sell']
        neutral_terms = ['neutral', 'sideways', 'hold']
        
        categorized = []
        for outlook in outlooks:
            outlook_lower = str(outlook).lower()
            if any(term in outlook_lower for term in positive_terms):
                categorized.append('positive')
            elif any(term in outlook_lower for term in negative_terms):
                categorized.append('negative')
            else:
                categorized.append('neutral')
        
        # Calculate agreement
        if len(set(categorized)) == 1:
            return 100.0  # Perfect agreement
        elif len(set(categorized)) == 2:
            return 60.0  # Partial agreement
        else:
            return 30.0  # Disagreement
