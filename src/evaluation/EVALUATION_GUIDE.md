# MarketSenseAI Evaluation Guide

## Overview

This evaluation framework provides comprehensive assessment of MarketSenseAI's analysis quality using multiple methodologies:

1. **LLM-as-a-Judge**: Uses Groq's LLaMA 3.3 70B to objectively evaluate analysis quality
2. **Quantitative Metrics**: Response time, data sources, confidence calibration
3. **Agent Performance**: Individual agent quality assessment
4. **Consistency Checks**: Cross-agent agreement and internal consistency

## Quick Start

### Run Single Query Evaluation

```bash
python -m src.evaluation.run_evaluation
```

### Run Full Benchmark Suite

```python
from src.evaluation import BenchmarkSuite
import asyncio

async def run_benchmark():
    benchmark = BenchmarkSuite()
    results = await benchmark.run_benchmark(BENCHMARK_QUERIES)
    print(results)

asyncio.run(run_benchmark())
```

## Evaluation Dimensions

### 1. LLM Judge Scores (0-100)

- **Coherence**: Logical structure and clarity
- **Factual Accuracy**: Correctness of data and facts
- **Reasoning Quality**: Soundness of conclusions
- **Actionability**: Practical usefulness of recommendations
- **Risk Assessment**: Quality of risk identification and mitigation
- **Overall Quality**: Holistic assessment

### 2. Agent Performance (0-100)

- **Macro Agent**: Completeness and relevance of macroeconomic analysis
- **Technical Agent**: Quality of technical indicators and chart analysis
- **Sentiment Agent**: Accuracy of sentiment aggregation
- **Synthesis Agent**: Quality of final recommendations

### 3. Consistency Metrics (0-100)

- **Internal Consistency**: Logical consistency within analysis
- **Cross-Agent Agreement**: Agreement between specialist agents

### 4. Performance Metrics

- **Response Time**: Seconds to complete analysis
- **Data Sources Used**: Number of external data sources queried
- **Confidence Score**: System's confidence in recommendations

## Scoring Interpretation

| Score Range | Interpretation |
|-------------|----------------|
| 90-100 | Exceptional - Institutional grade analysis |
| 80-89 | Excellent - High-quality professional analysis |
| 70-79 | Good - Solid analysis with minor improvements needed |
| 60-69 | Acceptable - Usable but needs improvement |
| Below 60 | Poor - Significant issues need addressing |

## Custom Evaluation

### Evaluate Your Own Queries

```python
from src.evaluation import SystemEvaluator
import asyncio

async def evaluate_custom():
    evaluator = SystemEvaluator()
    
    metrics = await evaluator.evaluate_single_query(
        query="Your custom query here",
        asset_symbol="BTC",
        timeframe="medium"
    )
    
    print(f"Overall Score: {metrics.get_overall_score():.2f}/100")
    print(f"Quality: {metrics.overall_quality_score:.1f}/100")
    print(f"Actionability: {metrics.actionability_score:.1f}/100")

asyncio.run(evaluate_custom())
```

### Create Custom Benchmark

```python
custom_queries = [
    {
        "query": "Your question 1",
        "asset": "BTC",
        "timeframe": "short"
    },
    {
        "query": "Your question 2",
        "asset": "ETH",
        "timeframe": "long"
    }
]

benchmark = BenchmarkSuite()
results = await benchmark.run_benchmark(custom_queries)
```

## Output Files

Benchmark results are saved as CSV files:
- `benchmark_results_YYYYMMDD_HHMMSS.csv`

Columns include all evaluation metrics for analysis and comparison.

## Best Practices

### 1. Regular Evaluation
- Run benchmarks weekly to track quality over time
- Compare results across different market conditions

### 2. Diverse Test Queries
- Include different query types (buy/sell, risk, analysis)
- Test across multiple assets and timeframes
- Include edge cases and complex scenarios

### 3. Continuous Improvement
- Identify low-scoring dimensions
- Focus improvements on weakest areas
- Track score trends over time

### 4. A/B Testing
- Compare different agent configurations
- Test prompt variations
- Evaluate model upgrades

## Advanced Usage

### Historical Accuracy Tracking

```python
# Track predictions vs actual outcomes
# (Requires manual outcome recording)

from src.evaluation import SystemEvaluator

evaluator = SystemEvaluator()

# Make prediction
metrics = await evaluator.evaluate_single_query(
    query="Will Bitcoin go up?",
    asset_symbol="BTC"
)

# Record prediction
prediction_id = save_prediction(metrics)

# Later, record actual outcome
record_outcome(prediction_id, actual_outcome="up")

# Calculate accuracy
accuracy = calculate_prediction_accuracy()
```

### Comparative Evaluation

```python
# Compare MarketSenseAI vs other systems

results_marketsense = await evaluate_system("MarketSenseAI", queries)
results_competitor = await evaluate_system("Competitor", queries)

comparison = compare_results(results_marketsense, results_competitor)
print(comparison)
```

## Troubleshooting

**Issue**: Low coherence scores
**Solution**: Review synthesis agent prompts, ensure logical flow

**Issue**: Low factual accuracy
**Solution**: Verify data source reliability, check API connections

**Issue**: Low actionability
**Solution**: Enhance recommendation specificity, add concrete steps

**Issue**: Poor cross-agent agreement
**Solution**: Review agent prompts for consistency, check data sources

## Competitive Edge

This evaluation framework gives you an edge by:

1. **Objective Quality Assessment**: LLM judge provides unbiased evaluation
2. **Continuous Improvement**: Track metrics over time
3. **Benchmarking**: Compare against industry standards
4. **Transparency**: Detailed breakdown of strengths/weaknesses
5. **Reproducibility**: Consistent evaluation methodology

## Contributing

To add new evaluation dimensions:

1. Update `EvaluationMetrics` dataclass
2. Add evaluation logic to appropriate evaluator class
3. Update LLM judge prompt if needed
4. Add tests for new metrics

---

**Built for Excellence** 🎯
