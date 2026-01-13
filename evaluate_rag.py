#!/usr/bin/env python3
"""
RAG System Evaluation using RAGAS Framework
Measures: Faithfulness, Answer Relevancy, Context Precision, Context Recall
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any
import logging

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)

from app.rag_backend import RAGBackend

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RAGEvaluator:
    """Evaluate RAG system using RAGAS metrics."""
    
    def __init__(self):
        """Initialize evaluator."""
        self.rag_backend = RAGBackend()
        self.results_dir = Path("evaluation_results")
        self.results_dir.mkdir(exist_ok=True)
        
    async def evaluate_test_cases(self, test_cases_file: str = "test_cases.json") -> Dict[str, Any]:
        """
        Evaluate RAG system on test cases.
        
        Args:
            test_cases_file: Path to test cases JSON
            
        Returns:
            Evaluation results
        """
        # Load test cases
        logger.info(f"📂 Loading test cases from {test_cases_file}")
        with open(test_cases_file, 'r') as f:
            test_cases = json.load(f)
        
        logger.info(f"✅ Loaded {len(test_cases)} test cases")
        
        # Generate answers
        logger.info("🔄 Generating answers...")
        questions = []
        answers = []
        contexts = []
        ground_truths = []
        
        for i, test_case in enumerate(test_cases, 1):
            question = test_case["question"]
            ground_truth = test_case.get("ground_truth", "")
            
            logger.info(f"  [{i}/{len(test_cases)}] Processing: {question[:50]}...")
            
            # Get answer from RAG system
            try:
                result = await self.rag_backend.answer(question, include_sources=True)
                
                questions.append(question)
                answers.append(result["answer"])
                
                # Extract contexts (source texts)
                context_list = [source["text"] for source in result["sources"]]
                contexts.append(context_list)
                
                ground_truths.append(ground_truth)
                
            except Exception as e:
                logger.error(f"  ❌ Error processing question: {e}")
                continue
        
        logger.info(f"✅ Generated {len(answers)} answers")
        
        # Prepare dataset for RAGAS
        logger.info("📊 Preparing evaluation dataset...")
        data = {
            "question": questions,
            "answer": answers,
            "contexts": contexts,
            "ground_truth": ground_truths
        }
        
        dataset = Dataset.from_dict(data)
        
        # Run evaluation
        logger.info("🔬 Running RAGAS evaluation...")
        logger.info("   This may take a few minutes...")
        
        try:
            result = evaluate(
                dataset,
                metrics=[
                    faithfulness,
                    answer_relevancy,
                    context_precision,
                    context_recall,
                ]
            )
            
            logger.info("✅ Evaluation complete!")
            
            return {
                "scores": result,
                "questions": questions,
                "answers": answers,
                "contexts": contexts,
                "ground_truths": ground_truths
            }
            
        except Exception as e:
            logger.error(f"❌ Evaluation failed: {e}")
            raise
    
    def save_results(self, results: Dict[str, Any], filename: str = "evaluation_results.json"):
        """Save evaluation results to file."""
        output_path = self.results_dir / filename
        
        # Convert results to JSON-serializable format
        results_json = {
            "scores": {
                "faithfulness": float(results["scores"]["faithfulness"]),
                "answer_relevancy": float(results["scores"]["answer_relevancy"]),
                "context_precision": float(results["scores"]["context_precision"]),
                "context_recall": float(results["scores"]["context_recall"]),
            },
            "num_test_cases": len(results["questions"]),
            "test_cases": [
                {
                    "question": q,
                    "answer": a,
                    "ground_truth": gt,
                    "num_contexts": len(c)
                }
                for q, a, gt, c in zip(
                    results["questions"],
                    results["answers"],
                    results["ground_truths"],
                    results["contexts"]
                )
            ]
        }
        
        with open(output_path, 'w') as f:
            json.dump(results_json, f, indent=2)
        
        logger.info(f"💾 Results saved to {output_path}")
        
    def print_results(self, results: Dict[str, Any]):
        """Print evaluation results in a readable format."""
        scores = results["scores"]
        
        print("\n" + "=" * 60)
        print("📊 RAGAS Evaluation Results")
        print("=" * 60)
        print(f"\n📈 Metrics:")
        print(f"   • Faithfulness:       {scores['faithfulness']:.3f} (how factual)")
        print(f"   • Answer Relevancy:   {scores['answer_relevancy']:.3f} (how relevant)")
        print(f"   • Context Precision:  {scores['context_precision']:.3f} (context quality)")
        print(f"   • Context Recall:     {scores['context_recall']:.3f} (context coverage)")
        
        # Overall score
        avg_score = sum([
            scores['faithfulness'],
            scores['answer_relevancy'],
            scores['context_precision'],
            scores['context_recall']
        ]) / 4
        
        print(f"\n🎯 Overall Score:      {avg_score:.3f}")
        
        # Interpretation
        print(f"\n💡 Interpretation:")
        if avg_score >= 0.8:
            print("   ✅ Excellent! Your RAG system is performing very well.")
        elif avg_score >= 0.7:
            print("   👍 Good! Some room for improvement.")
        elif avg_score >= 0.6:
            print("   ⚠️  Fair. Consider optimizations.")
        else:
            print("   ❌ Needs improvement. Review retrieval and prompts.")
        
        print("\n" + "=" * 60)
        print(f"📝 Tested on {len(results['questions'])} questions")
        print("=" * 60 + "\n")

async def main():
    """Main evaluation entry point."""
    print("=" * 60)
    print("🔬 RAG System Evaluation with RAGAS")
    print("=" * 60)
    print()
    
    # Check if test cases exist
    if not Path("test_cases.json").exists():
        logger.error("❌ test_cases.json not found!")
        logger.info("   Creating sample test cases...")
        
        # Create sample test cases
        sample_cases = [
            {
                "question": "What is the main topic of the document?",
                "ground_truth": "The document discusses various topics from the indexed corpus."
            },
            {
                "question": "Summarize the key points.",
                "ground_truth": "Key points include the main themes and important concepts covered."
            }
        ]
        
        with open("test_cases.json", 'w') as f:
            json.dump(sample_cases, f, indent=2)
        
        logger.info("✅ Created sample test_cases.json")
        logger.info("   Please edit it with your actual test questions!")
        return
    
    # Initialize evaluator
    evaluator = RAGEvaluator()
    
    try:
        # Run evaluation
        results = await evaluator.evaluate_test_cases()
        
        # Print results
        evaluator.print_results(results)
        
        # Save results
        evaluator.save_results(results)
        
        logger.info("✅ Evaluation complete!")
        logger.info("   Check evaluation_results/ directory for detailed results")
        
    except Exception as e:
        logger.error(f"❌ Evaluation failed: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
