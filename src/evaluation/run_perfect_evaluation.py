"""
Perfect Evaluation Suite for MarketSenseAI
Comprehensive testing across all dimensions with detailed reporting
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from src.evaluation import SystemEvaluator, BenchmarkSuite, EvaluationMetrics

# Comprehensive test queries covering all use cases
PERFECT_BENCHMARK_QUERIES = [
    # Investment Decision Queries
    {
        "query": "Should I invest in Bitcoin right now? I'm looking for a medium-term investment.",
        "asset": "BTC",
        "timeframe": "medium",
        "category": "Investment Decision"
    },
    {
        "query": "Is Ethereum a good long-term investment compared to Bitcoin?",
        "asset": "ETH",
        "timeframe": "long",
        "category": "Comparative Analysis"
    },
    
    # Market Sentiment Queries
    {
        "query": "What's the current market sentiment for Solana?",
        "asset": "SOL",
        "timeframe": "short",
        "category": "Sentiment Analysis"
    },
    {
        "query": "How is the crypto community feeling about Cardano lately?",
        "asset": "ADA",
        "timeframe": "medium",
        "category": "Sentiment Analysis"
    },
    
    # Risk Assessment Queries
    {
        "query": "What are the main risks of investing in Dogecoin?",
        "asset": "DOGE",
        "timeframe": "short",
        "category": "Risk Assessment"
    },
    {
        "query": "Analyze the volatility and risks associated with BNB",
        "asset": "BNB",
        "timeframe": "medium",
        "category": "Risk Assessment"
    },
    
    # Technical Analysis Queries
    {
        "query": "What do the technical indicators say about XRP's price movement?",
        "asset": "XRP",
        "timeframe": "short",
        "category": "Technical Analysis"
    },
    {
        "query": "Analyze Polkadot's chart patterns and support/resistance levels",
        "asset": "DOT",
        "timeframe": "medium",
        "category": "Technical Analysis"
    },
    
    # Price Prediction Queries
    {
        "query": "Where do you see Avalanche price heading in the next month?",
        "asset": "AVAX",
        "timeframe": "short",
        "category": "Price Prediction"
    },
    {
        "query": "What's your price prediction for Polygon over the next 6 months?",
        "asset": "MATIC",
        "timeframe": "long",
        "category": "Price Prediction"
    },
    
    # Market Conditions Queries
    {
        "query": "How are macroeconomic factors affecting Bitcoin right now?",
        "asset": "BTC",
        "timeframe": "medium",
        "category": "Macro Analysis"
    },
    {
        "query": "What impact will upcoming regulations have on Ethereum?",
        "asset": "ETH",
        "timeframe": "long",
        "category": "Regulatory Impact"
    },
]


async def run_perfect_evaluation():
    """Run comprehensive evaluation with detailed reporting"""
    
    print("=" * 80)
    print("MarketSenseAI - Perfect Evaluation Suite")
    print("=" * 80)
    print(f"\nStarting evaluation at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total test queries: {len(PERFECT_BENCHMARK_QUERIES)}\n")
    
    # Initialize evaluators
    evaluator = SystemEvaluator()
    benchmark = BenchmarkSuite()
    
    # Storage for results
    all_results = []
    category_scores = {}
    
    # Run benchmark
    print("Running comprehensive benchmark...")
    print("-" * 80)
    
    for idx, test_case in enumerate(PERFECT_BENCHMARK_QUERIES, 1):
        print(f"\n[{idx}/{len(PERFECT_BENCHMARK_QUERIES)}] Testing: {test_case['category']}")
        print(f"Query: {test_case['query'][:60]}...")
        print(f"Asset: {test_case['asset']} | Timeframe: {test_case['timeframe']}")
        
        try:
            # Run evaluation
            metrics = await evaluator.evaluate_single_query(
                query=test_case['query'],
                asset_symbol=test_case['asset'],
                timeframe=test_case['timeframe']
            )
            
            # Calculate overall score
            overall_score = metrics.get_overall_score()
            
            # Store results
            result = {
                "test_number": idx,
                "category": test_case['category'],
                "query": test_case['query'],
                "asset": test_case['asset'],
                "timeframe": test_case['timeframe'],
                "overall_score": overall_score,
                "coherence": metrics.coherence_score,
                "accuracy": metrics.factual_accuracy_score,
                "reasoning": metrics.reasoning_quality_score,
                "actionability": metrics.actionability_score,
                "risk_assessment": metrics.risk_assessment_score,
                "quality": metrics.overall_quality_score,
                "response_time": metrics.response_time_seconds,
                "data_sources": metrics.data_sources_used,
                "confidence": metrics.confidence_score,
            }
            all_results.append(result)
            
            # Track category scores
            if test_case['category'] not in category_scores:
                category_scores[test_case['category']] = []
            category_scores[test_case['category']].append(overall_score)
            
            # Display immediate results
            print(f"✓ Overall Score: {overall_score:.1f}/100")
            print(f"  Quality: {metrics.overall_quality_score:.1f} | "
                  f"Actionability: {metrics.actionability_score:.1f} | "
                  f"Response Time: {metrics.response_time_seconds:.2f}s")
            
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            all_results.append({
                "test_number": idx,
                "category": test_case['category'],
                "query": test_case['query'],
                "error": str(e)
            })
    
    # Generate comprehensive report
    print("\n" + "=" * 80)
    print("EVALUATION RESULTS SUMMARY")
    print("=" * 80)
    
    # Overall statistics
    valid_results = [r for r in all_results if 'overall_score' in r]
    if valid_results:
        avg_overall = sum(r['overall_score'] for r in valid_results) / len(valid_results)
        avg_quality = sum(r['quality'] for r in valid_results) / len(valid_results)
        avg_actionability = sum(r['actionability'] for r in valid_results) / len(valid_results)
        avg_response_time = sum(r['response_time'] for r in valid_results) / len(valid_results)
        
        print(f"\n📊 Overall Performance:")
        print(f"   Average Overall Score: {avg_overall:.1f}/100")
        print(f"   Average Quality Score: {avg_quality:.1f}/100")
        print(f"   Average Actionability: {avg_actionability:.1f}/100")
        print(f"   Average Response Time: {avg_response_time:.2f}s")
        print(f"   Success Rate: {len(valid_results)}/{len(PERFECT_BENCHMARK_QUERIES)} ({len(valid_results)/len(PERFECT_BENCHMARK_QUERIES)*100:.1f}%)")
        
        # Performance rating
        print(f"\n🎯 Performance Rating:")
        if avg_overall >= 90:
            rating = "EXCEPTIONAL ⭐⭐⭐⭐⭐"
        elif avg_overall >= 80:
            rating = "EXCELLENT ⭐⭐⭐⭐"
        elif avg_overall >= 70:
            rating = "GOOD ⭐⭐⭐"
        elif avg_overall >= 60:
            rating = "ACCEPTABLE ⭐⭐"
        else:
            rating = "NEEDS IMPROVEMENT ⭐"
        print(f"   {rating}")
    
    # Category breakdown
    print(f"\n📋 Performance by Category:")
    for category, scores in category_scores.items():
        avg_score = sum(scores) / len(scores)
        print(f"   {category:.<40} {avg_score:.1f}/100")
    
    # Dimension breakdown
    if valid_results:
        print(f"\n📈 Performance by Dimension:")
        dimensions = {
            "Coherence": sum(r['coherence'] for r in valid_results) / len(valid_results),
            "Factual Accuracy": sum(r['accuracy'] for r in valid_results) / len(valid_results),
            "Reasoning Quality": sum(r['reasoning'] for r in valid_results) / len(valid_results),
            "Actionability": sum(r['actionability'] for r in valid_results) / len(valid_results),
            "Risk Assessment": sum(r['risk_assessment'] for r in valid_results) / len(valid_results),
        }
        for dim, score in dimensions.items():
            print(f"   {dim:.<40} {score:.1f}/100")
    
    # Top and bottom performers
    if valid_results:
        sorted_results = sorted(valid_results, key=lambda x: x['overall_score'], reverse=True)
        
        print(f"\n🏆 Top 3 Performing Queries:")
        for i, result in enumerate(sorted_results[:3], 1):
            print(f"   {i}. [{result['category']}] Score: {result['overall_score']:.1f}/100")
            print(f"      {result['query'][:70]}...")
        
        print(f"\n⚠️  Bottom 3 Performing Queries:")
        for i, result in enumerate(sorted_results[-3:], 1):
            print(f"   {i}. [{result['category']}] Score: {result['overall_score']:.1f}/100")
            print(f"      {result['query'][:70]}...")
    
    # Save detailed results
    output_dir = Path("evaluation_results")
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"perfect_evaluation_{timestamp}.json"
    
    with open(output_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_queries": len(PERFECT_BENCHMARK_QUERIES),
            "successful_queries": len(valid_results),
            "summary": {
                "average_overall_score": avg_overall if valid_results else 0,
                "average_quality_score": avg_quality if valid_results else 0,
                "average_actionability": avg_actionability if valid_results else 0,
                "average_response_time": avg_response_time if valid_results else 0,
            },
            "category_scores": {k: sum(v)/len(v) for k, v in category_scores.items()},
            "detailed_results": all_results
        }, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {output_file}")
    
    # Recommendations
    print(f"\n💡 Recommendations:")
    if valid_results:
        if avg_overall < 70:
            print("   • Focus on improving agent prompts and data quality")
            print("   • Review low-scoring queries for common issues")
        if avg_response_time > 10:
            print("   • Consider optimizing API calls and caching strategies")
        if avg_actionability < 75:
            print("   • Enhance synthesis agent to provide more specific recommendations")
        if len(valid_results) < len(PERFECT_BENCHMARK_QUERIES):
            print("   • Investigate and fix errors in failed queries")
    
    print("\n" + "=" * 80)
    print("Evaluation Complete!")
    print("=" * 80)
    
    return all_results


if __name__ == "__main__":
    print("\n🚀 Starting Perfect Evaluation for MarketSenseAI\n")
    results = asyncio.run(run_perfect_evaluation())
    print("\n✅ All evaluations completed successfully!\n")
