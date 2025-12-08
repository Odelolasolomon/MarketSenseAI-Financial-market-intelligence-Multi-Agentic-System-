"""
MarketSenseAI Evaluation Framework - Part 2
System Evaluator and Benchmarking
"""

from src.evaluation.evaluation_framework import (
    EvaluationMetrics, LLMJudge, AgentPerformanceEvaluator
)
from typing import List, Dict, Any, Optional
from datetime import datetime
import time
import asyncio
import pandas as pd
from src.utilities.logger import get_logger
from src.application.services.analysis_service import AnalysisService
from src.domain.value_objects.timeframe import TimeframeVO

logger = get_logger(__name__)


class SystemEvaluator:
    """Main system evaluator"""
    
    def __init__(self):
        self.analysis_service = AnalysisService()
        self.llm_judge = LLMJudge()
        self.agent_evaluator = AgentPerformanceEvaluator()
    
    async def evaluate_single_query(
        self,
        query: str,
        asset_symbol: str,
        timeframe: str = "medium",
        market_data: Optional[Dict] = None
    ) -> EvaluationMetrics:
        """
        Comprehensive evaluation of a single query
        """
        logger.info(f"Evaluating query: {query} for {asset_symbol}")
        
        # Run analysis and measure time
        start_time = time.time()
        
        try:
            result = await self.analysis_service.analyze(
                query=query,
                asset_symbol=asset_symbol,
                timeframe=TimeframeVO.from_string(timeframe)
            )
            
            response_time = time.time() - start_time
            
            # Convert result to dict
            analysis_dict = result.to_dict()
            
            # Get LLM judge scores
            llm_scores = await self.llm_judge.evaluate_analysis(
                query, analysis_dict, market_data
            )
            
            # Evaluate individual agents
            macro_score = self.agent_evaluator.evaluate_agent_output(
                "macro", analysis_dict.get('macro_analysis', {})
            )
            technical_score = self.agent_evaluator.evaluate_agent_output(
                "technical", analysis_dict.get('technical_analysis', {})
            )
            sentiment_score = self.agent_evaluator.evaluate_agent_output(
                "sentiment", analysis_dict.get('sentiment_analysis', {})
            )
            
            # Evaluate cross-agent consistency
            consistency_score = self.agent_evaluator.evaluate_cross_agent_consistency(
                analysis_dict.get('macro_analysis', {}),
                analysis_dict.get('technical_analysis', {}),
                analysis_dict.get('sentiment_analysis', {})
            )
            
            # Calculate synthesis quality
            synthesis_score = self._evaluate_synthesis_quality(analysis_dict)
            
            # Count data sources
            data_sources = self._count_data_sources(analysis_dict)
            
            # Create evaluation metrics
            metrics = EvaluationMetrics(
                coherence_score=llm_scores.get('coherence_score', 50.0),
                factual_accuracy_score=llm_scores.get('factual_accuracy_score', 50.0),
                reasoning_quality_score=llm_scores.get('reasoning_quality_score', 50.0),
                actionability_score=llm_scores.get('actionability_score', 50.0),
                risk_assessment_score=llm_scores.get('risk_assessment_score', 50.0),
                overall_quality_score=llm_scores.get('overall_quality_score', 50.0),
                response_time_seconds=response_time,
                data_sources_used=data_sources,
                confidence_score=analysis_dict.get('overall_confidence', 0.0),
                macro_agent_score=macro_score,
                technical_agent_score=technical_score,
                sentiment_agent_score=sentiment_score,
                synthesis_quality_score=synthesis_score,
                internal_consistency_score=consistency_score,
                cross_agent_agreement_score=consistency_score,
                asset_symbol=asset_symbol,
                query=query,
                timestamp=datetime.now().isoformat(),
                evaluation_model=self.llm_judge.model
            )
            
            logger.info(f"Evaluation complete. Overall score: {metrics.get_overall_score():.2f}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            raise
    
    def _evaluate_synthesis_quality(self, analysis: Dict) -> float:
        """Evaluate synthesis agent quality"""
        score = 0.0
        
        # Check executive summary
        if analysis.get('executive_summary') and len(analysis['executive_summary']) > 100:
            score += 25
        
        # Check investment thesis
        if analysis.get('investment_thesis') and len(analysis['investment_thesis']) > 100:
            score += 25
        
        # Check trading action
        if analysis.get('trading_action') in ['buy', 'sell', 'hold']:
            score += 15
        
        # Check position sizing
        if analysis.get('position_sizing'):
            score += 10
        
        # Check risk factors
        if analysis.get('key_risks') and len(analysis['key_risks']) >= 3:
            score += 15
        
        # Check mitigations
        if analysis.get('risk_mitigations') and len(analysis['risk_mitigations']) >= 2:
            score += 10
        
        return min(score, 100.0)
    
    def _count_data_sources(self, analysis: Dict) -> int:
        """Count data sources used"""
        sources = set()
        
        # Check each agent's data sources
        for agent_key in ['macro_analysis', 'technical_analysis', 'sentiment_analysis']:
            agent_data = analysis.get(agent_key, {})
            if isinstance(agent_data, dict):
                detailed = agent_data.get('detailed_analysis', {})
                if isinstance(detailed, dict) and 'data_sources' in detailed:
                    sources.update(detailed['data_sources'])
        
        return len(sources) if sources else 5  # Default estimate


class BenchmarkSuite:
    """Benchmark suite for systematic evaluation"""
    
    def __init__(self):
        self.evaluator = SystemEvaluator()
        self.results = []
    
    async def run_benchmark(
        self,
        test_queries: List[Dict[str, str]],
        save_results: bool = True
    ) -> pd.DataFrame:
        """
        Run benchmark on multiple test queries
        
        Args:
            test_queries: List of dicts with 'query', 'asset', 'timeframe'
            save_results: Whether to save results to file
        
        Returns:
            DataFrame with all evaluation metrics
        """
        logger.info(f"Running benchmark on {len(test_queries)} queries")
        
        for i, test in enumerate(test_queries, 1):
            logger.info(f"Test {i}/{len(test_queries)}: {test['query']}")
            
            try:
                metrics = await self.evaluator.evaluate_single_query(
                    query=test['query'],
                    asset_symbol=test['asset'],
                    timeframe=test.get('timeframe', 'medium')
                )
                
                self.results.append(metrics.to_dict())
                
            except Exception as e:
                logger.error(f"Test {i} failed: {e}")
                continue
        
        # Convert to DataFrame
        df = pd.DataFrame(self.results)
        
        if save_results:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"benchmark_results_{timestamp}.csv"
            df.to_csv(filename, index=False)
            logger.info(f"Results saved to {filename}")
        
        # Print summary
        self._print_summary(df)
        
        return df
    
    def _print_summary(self, df: pd.DataFrame):
        """Print benchmark summary"""
        print("\n" + "="*80)
        print("BENCHMARK SUMMARY")
        print("="*80)
        
        print(f"\nTotal Queries Evaluated: {len(df)}")
        print(f"Average Response Time: {df['response_time_seconds'].mean():.2f}s")
        print(f"Average Data Sources Used: {df['data_sources_used'].mean():.1f}")
        
        print("\n--- LLM Judge Scores (0-100) ---")
        print(f"Coherence: {df['coherence_score'].mean():.1f} ± {df['coherence_score'].std():.1f}")
        print(f"Factual Accuracy: {df['factual_accuracy_score'].mean():.1f} ± {df['factual_accuracy_score'].std():.1f}")
        print(f"Reasoning Quality: {df['reasoning_quality_score'].mean():.1f} ± {df['reasoning_quality_score'].std():.1f}")
        print(f"Actionability: {df['actionability_score'].mean():.1f} ± {df['actionability_score'].std():.1f}")
        print(f"Risk Assessment: {df['risk_assessment_score'].mean():.1f} ± {df['risk_assessment_score'].std():.1f}")
        print(f"Overall Quality: {df['overall_quality_score'].mean():.1f} ± {df['overall_quality_score'].std():.1f}")
        
        print("\n--- Agent Performance (0-100) ---")
        print(f"Macro Agent: {df['macro_agent_score'].mean():.1f}")
        print(f"Technical Agent: {df['technical_agent_score'].mean():.1f}")
        print(f"Sentiment Agent: {df['sentiment_agent_score'].mean():.1f}")
        print(f"Synthesis Quality: {df['synthesis_quality_score'].mean():.1f}")
        
        print("\n--- Consistency Metrics (0-100) ---")
        print(f"Internal Consistency: {df['internal_consistency_score'].mean():.1f}")
        print(f"Cross-Agent Agreement: {df['cross_agent_agreement_score'].mean():.1f}")
        
        print("\n" + "="*80)


# Predefined test queries for benchmarking
BENCHMARK_QUERIES = [
    {
        "query": "Should I buy Bitcoin now for a short-term trade?",
        "asset": "BTC",
        "timeframe": "short"
    },
    {
        "query": "Is Ethereum a good long-term investment?",
        "asset": "ETH",
        "timeframe": "long"
    },
    {
        "query": "What are the main risks of investing in Bitcoin right now?",
        "asset": "BTC",
        "timeframe": "medium"
    },
    {
        "query": "Should I hold or sell my Ethereum position?",
        "asset": "ETH",
        "timeframe": "medium"
    },
    {
        "query": "Analyze Bitcoin's current market conditions",
        "asset": "BTC",
        "timeframe": "medium"
    }
]


async def main():
    """Run evaluation"""
    
    # Single query evaluation
    print("=== Single Query Evaluation ===\n")
    evaluator = SystemEvaluator()
    
    metrics = await evaluator.evaluate_single_query(
        query="Should I buy Bitcoin now?",
        asset_symbol="BTC",
        timeframe="medium"
    )
    
    print(f"Overall Score: {metrics.get_overall_score():.2f}/100")
    print(f"Response Time: {metrics.response_time_seconds:.2f}s")
    print(f"LLM Judge Quality Score: {metrics.overall_quality_score:.1f}/100")
    print(f"Reasoning Quality: {metrics.reasoning_quality_score:.1f}/100")
    print(f"Actionability: {metrics.actionability_score:.1f}/100")
    
    # Full benchmark
    print("\n\n=== Running Full Benchmark ===\n")
    benchmark = BenchmarkSuite()
    results_df = await benchmark.run_benchmark(BENCHMARK_QUERIES)
    
    print("\nBenchmark complete!")


if __name__ == "__main__":
    asyncio.run(main())
