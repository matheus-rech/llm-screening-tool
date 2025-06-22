import os
import json
import requests
from typing import Dict, List, Any, Tuple
import re
from datetime import datetime

class RealDualLLMEvaluator:
    """
    Real Dual-LLM Evaluation System for Systematic Review Screening
    Uses actual OpenAI GPT-4 and Anthropic Claude APIs for biomedical paper evaluation
    """
    
    def __init__(self, openai_api_key: str, anthropic_api_key: str):
        self.openai_api_key = openai_api_key
        self.anthropic_api_key = anthropic_api_key
        self.evaluation_results = []
        
        # Chiari Malformation PICOTT Criteria
        self.picott_criteria = {
            "population": "Chiari malformation type I patients",
            "intervention": "Posterior fossa decompression with tonsils reduction (tonsillectomy via surgical resection or bipolar coagulation)",
            "comparator": "Posterior fossa decompression with duraplasty",
            "outcomes": ["favorable CCOS (Chicago Chiari Outcome Scale)", "syrinx resolution", "postoperative complications"],
            "study_types": ["observational studies", "RCTs"],
            "inclusion_criteria": [
                "Comparative studies (RCTs, cohort studies, case-control studies)",
                "Chiari malformation type I patients",
                "Presence of comparison groups: decompression alone vs decompression + duraplasty, decompression alone vs decompression + tonsils reduction/resection, decompression + duraplasty vs decompression + tonsils reduction/resection",
                "English language publications",
                "Complete patient data records"
            ],
            "exclusion_criteria": [
                "Non-English literature",
                "Single intervention of decompression with cerebellar tonsillectomy without control group",
                "Incomplete patient data records",
                "Case reports, editorials, letters, conference abstracts"
            ]
        }
    
    def evaluate_with_gpt4(self, citation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate citation using OpenAI GPT-4
        """
        prompt = f"""
        You are a neurosurgical expert evaluating papers for a systematic review on Chiari Malformation Type I treatments.

        PICOTT Criteria:
        - Population: {self.picott_criteria['population']}
        - Intervention: {self.picott_criteria['intervention']}
        - Comparator: {self.picott_criteria['comparator']}
        - Outcomes: {', '.join(self.picott_criteria['outcomes'])}
        - Study Types: {', '.join(self.picott_criteria['study_types'])}

        Inclusion Criteria:
        {chr(10).join(f"- {criteria}" for criteria in self.picott_criteria['inclusion_criteria'])}

        Exclusion Criteria:
        {chr(10).join(f"- {criteria}" for criteria in self.picott_criteria['exclusion_criteria'])}

        Citation to Evaluate:
        Title: {citation.get('title', 'N/A')}
        Abstract: {citation.get('abstract', 'N/A')}
        Authors: {citation.get('authors', 'N/A')}
        Journal: {citation.get('journal', 'N/A')}
        Year: {citation.get('year', 'N/A')}

        Please evaluate this citation and provide:
        1. DECISION: INCLUDE or EXCLUDE
        2. CONFIDENCE: 0-100%
        3. REASONING: Detailed explanation
        4. PICO_ANALYSIS: Extract Population, Intervention, Comparator, Outcomes if present
        5. STUDY_DESIGN: Identify study type
        6. QUALITY_ASSESSMENT: Rate study quality (High/Medium/Low)

        Respond in JSON format.
        """
        
        try:
            headers = {
                'Authorization': f'Bearer {self.openai_api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': 'gpt-4',
                'messages': [
                    {'role': 'system', 'content': 'You are a neurosurgical expert conducting systematic review screening.'},
                    {'role': 'user', 'content': prompt}
                ],
                'max_tokens': 1000,
                'temperature': 0.1
            }
            
            response = requests.post('https://api.openai.com/v1/chat/completions', 
                                   headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # Try to parse JSON response
                try:
                    evaluation = json.loads(content)
                except json.JSONDecodeError:
                    # Fallback parsing if JSON is malformed
                    evaluation = self._parse_llm_response(content)
                
                evaluation['evaluator'] = 'GPT-4'
                evaluation['api_response_time'] = response.elapsed.total_seconds()
                return evaluation
            else:
                return {
                    'decision': 'ERROR',
                    'confidence': 0,
                    'reasoning': f'API Error: {response.status_code}',
                    'evaluator': 'GPT-4',
                    'error': True
                }
                
        except Exception as e:
            return {
                'decision': 'ERROR',
                'confidence': 0,
                'reasoning': f'Exception: {str(e)}',
                'evaluator': 'GPT-4',
                'error': True
            }
    
    def evaluate_with_claude(self, citation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate citation using Anthropic Claude
        """
        prompt = f"""
        You are a systematic review methodologist evaluating papers for a Chiari Malformation Type I meta-analysis.

        Research Question: Posterior Fossa Decompression with Cerebellar Tonsil Reduction vs Duraplasty for Chiari Malformation Type I

        PICOTT Framework:
        - Population: {self.picott_criteria['population']}
        - Intervention: {self.picott_criteria['intervention']}
        - Comparator: {self.picott_criteria['comparator']}
        - Outcomes: {', '.join(self.picott_criteria['outcomes'])}
        - Study Types: {', '.join(self.picott_criteria['study_types'])}

        Strict Inclusion Criteria:
        {chr(10).join(f"✓ {criteria}" for criteria in self.picott_criteria['inclusion_criteria'])}

        Strict Exclusion Criteria:
        {chr(10).join(f"✗ {criteria}" for criteria in self.picott_criteria['exclusion_criteria'])}

        Citation for Review:
        Title: {citation.get('title', 'N/A')}
        Abstract: {citation.get('abstract', 'N/A')}
        Authors: {citation.get('authors', 'N/A')}
        Journal: {citation.get('journal', 'N/A')}
        Publication Year: {citation.get('year', 'N/A')}

        Provide systematic evaluation with:
        1. DECISION: INCLUDE/EXCLUDE (strict adherence to criteria)
        2. CONFIDENCE: Percentage (0-100%)
        3. REASONING: Methodological justification
        4. BIAS_ASSESSMENT: Potential biases identified
        5. STUDY_QUALITY: Quality rating with justification
        6. RELEVANCE_SCORE: 0-100% relevance to research question

        Format response as JSON.
        """
        
        try:
            headers = {
                'x-api-key': self.anthropic_api_key,
                'Content-Type': 'application/json',
                'anthropic-version': '2023-06-01'
            }
            
            data = {
                'model': 'claude-3-sonnet-20240229',
                'max_tokens': 1000,
                'messages': [
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.1
            }
            
            response = requests.post('https://api.anthropic.com/v1/messages',
                                   headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                content = result['content'][0]['text']
                
                # Try to parse JSON response
                try:
                    evaluation = json.loads(content)
                except json.JSONDecodeError:
                    # Fallback parsing if JSON is malformed
                    evaluation = self._parse_llm_response(content)
                
                evaluation['evaluator'] = 'Claude'
                evaluation['api_response_time'] = response.elapsed.total_seconds()
                return evaluation
            else:
                return {
                    'decision': 'ERROR',
                    'confidence': 0,
                    'reasoning': f'API Error: {response.status_code}',
                    'evaluator': 'Claude',
                    'error': True
                }
                
        except Exception as e:
            return {
                'decision': 'ERROR',
                'confidence': 0,
                'reasoning': f'Exception: {str(e)}',
                'evaluator': 'Claude',
                'error': True
            }
    
    def _parse_llm_response(self, content: str) -> Dict[str, Any]:
        """
        Fallback parser for non-JSON LLM responses
        """
        evaluation = {
            'decision': 'UNCERTAIN',
            'confidence': 50,
            'reasoning': content,
            'pico_analysis': {},
            'study_design': 'Unknown',
            'quality_assessment': 'Unknown'
        }
        
        # Extract decision
        if 'INCLUDE' in content.upper():
            evaluation['decision'] = 'INCLUDE'
        elif 'EXCLUDE' in content.upper():
            evaluation['decision'] = 'EXCLUDE'
        
        # Extract confidence
        confidence_match = re.search(r'(\d+)%', content)
        if confidence_match:
            evaluation['confidence'] = int(confidence_match.group(1))
        
        return evaluation
    
    def dual_evaluate(self, citation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform dual evaluation with both LLMs
        """
        print(f"Evaluating: {citation.get('title', 'Unknown Title')[:80]}...")
        
        # Get evaluations from both LLMs
        gpt4_eval = self.evaluate_with_gpt4(citation)
        claude_eval = self.evaluate_with_claude(citation)
        
        # Calculate agreement and conflict detection
        agreement = self._calculate_agreement(gpt4_eval, claude_eval)
        
        # Determine final decision
        final_decision = self._resolve_decision(gpt4_eval, claude_eval, agreement)
        
        # Compile comprehensive evaluation
        evaluation_result = {
            'citation_id': citation.get('id', f"citation_{len(self.evaluation_results) + 1}"),
            'citation': citation,
            'gpt4_evaluation': gpt4_eval,
            'claude_evaluation': claude_eval,
            'agreement': agreement,
            'final_decision': final_decision,
            'evaluation_timestamp': datetime.now().isoformat(),
            'requires_human_review': agreement['conflict_detected'] or agreement['low_confidence']
        }
        
        self.evaluation_results.append(evaluation_result)
        return evaluation_result
    
    def _calculate_agreement(self, gpt4_eval: Dict, claude_eval: Dict) -> Dict[str, Any]:
        """
        Calculate agreement between LLM evaluations
        """
        # Check for API errors
        if gpt4_eval.get('error') or claude_eval.get('error'):
            return {
                'decision_agreement': False,
                'confidence_delta': 100,
                'conflict_detected': True,
                'low_confidence': True,
                'agreement_score': 0.0,
                'notes': 'API error detected'
            }
        
        # Decision agreement
        decision_agreement = gpt4_eval.get('decision') == claude_eval.get('decision')
        
        # Confidence delta
        gpt4_conf = gpt4_eval.get('confidence', 0)
        claude_conf = claude_eval.get('confidence', 0)
        confidence_delta = abs(gpt4_conf - claude_conf)
        
        # Conflict detection
        conflict_detected = not decision_agreement or confidence_delta > 20
        
        # Low confidence detection
        low_confidence = min(gpt4_conf, claude_conf) < 70
        
        # Overall agreement score
        if decision_agreement:
            agreement_score = 1.0 - (confidence_delta / 100)
        else:
            agreement_score = 0.0
        
        return {
            'decision_agreement': decision_agreement,
            'confidence_delta': confidence_delta,
            'conflict_detected': conflict_detected,
            'low_confidence': low_confidence,
            'agreement_score': agreement_score,
            'gpt4_confidence': gpt4_conf,
            'claude_confidence': claude_conf
        }
    
    def _resolve_decision(self, gpt4_eval: Dict, claude_eval: Dict, agreement: Dict) -> Dict[str, Any]:
        """
        Resolve final decision based on LLM evaluations
        """
        if agreement['conflict_detected']:
            return {
                'decision': 'CONFLICT',
                'confidence': min(gpt4_eval.get('confidence', 0), claude_eval.get('confidence', 0)),
                'reasoning': 'LLM disagreement detected - requires human review',
                'resolution_method': 'human_review_required'
            }
        
        # If agreement, use higher confidence evaluation
        if gpt4_eval.get('confidence', 0) >= claude_eval.get('confidence', 0):
            primary_eval = gpt4_eval
            secondary_eval = claude_eval
        else:
            primary_eval = claude_eval
            secondary_eval = gpt4_eval
        
        return {
            'decision': primary_eval.get('decision', 'UNCERTAIN'),
            'confidence': (primary_eval.get('confidence', 0) + secondary_eval.get('confidence', 0)) / 2,
            'reasoning': f"Agreement reached. Primary: {primary_eval.get('reasoning', 'N/A')[:200]}...",
            'resolution_method': 'llm_consensus'
        }
    
    def get_evaluation_summary(self) -> Dict[str, Any]:
        """
        Generate comprehensive evaluation summary
        """
        if not self.evaluation_results:
            return {'error': 'No evaluations completed'}
        
        total_evaluations = len(self.evaluation_results)
        conflicts = sum(1 for eval in self.evaluation_results if eval['agreement']['conflict_detected'])
        human_reviews = sum(1 for eval in self.evaluation_results if eval['requires_human_review'])
        
        # Decision distribution
        decisions = [eval['final_decision']['decision'] for eval in self.evaluation_results]
        include_count = decisions.count('INCLUDE')
        exclude_count = decisions.count('EXCLUDE')
        conflict_count = decisions.count('CONFLICT')
        
        # Confidence statistics
        confidences = [eval['agreement']['gpt4_confidence'] for eval in self.evaluation_results if not eval['gpt4_evaluation'].get('error')]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        # Agreement statistics
        agreement_scores = [eval['agreement']['agreement_score'] for eval in self.evaluation_results]
        avg_agreement = sum(agreement_scores) / len(agreement_scores) if agreement_scores else 0
        
        return {
            'total_evaluations': total_evaluations,
            'decision_distribution': {
                'include': include_count,
                'exclude': exclude_count,
                'conflicts': conflict_count
            },
            'quality_metrics': {
                'conflict_rate': conflicts / total_evaluations * 100,
                'human_review_rate': human_reviews / total_evaluations * 100,
                'average_confidence': avg_confidence,
                'average_agreement': avg_agreement * 100
            },
            'api_performance': {
                'gpt4_errors': sum(1 for eval in self.evaluation_results if eval['gpt4_evaluation'].get('error')),
                'claude_errors': sum(1 for eval in self.evaluation_results if eval['claude_evaluation'].get('error'))
            }
        }
    
    def export_results(self, filename: str) -> str:
        """
        Export evaluation results to JSON file
        """
        export_data = {
            'evaluation_summary': self.get_evaluation_summary(),
            'picott_criteria': self.picott_criteria,
            'evaluation_results': self.evaluation_results,
            'export_timestamp': datetime.now().isoformat()
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        return filename

# Example usage and testing
if __name__ == "__main__":
    # API Keys (load from environment variables)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    
    # Initialize evaluator
    evaluator = RealDualLLMEvaluator(OPENAI_API_KEY, ANTHROPIC_API_KEY)
    
    # Test citation from the datasets
    test_citation = {
        'id': 'test_001',
        'title': 'Surgical Treatment of Basilar Invagination without Evident Atlantoaxial Instability (Type B) - A Systematic Review',
        'abstract': 'Chiari 1 malformation (CM1) and Basilar Invagination (BI) are the most common congenital bone and neural disorders of the craniovertebral junction. This systematic review aims to evaluate the treatment options for symptomatic type B BI especially concerning the need for craniocervical fusion. Posterior fossa decompression (PFD) with or without duroplasty was employed in three studies, C1-2 fusion in one, and C1-2 distraction and fusion in two studies. All reported patients improvement post-surgery regardless of the technique used.',
        'authors': 'Joaquim AF, Neto ER, Pinheiro LCP',
        'journal': 'Neurology India',
        'year': '2025'
    }
    
    print("Testing Real Dual-LLM Evaluation System...")
    print("=" * 60)
    
    # Perform evaluation
    result = evaluator.dual_evaluate(test_citation)
    
    # Display results
    print(f"Citation: {result['citation']['title'][:80]}...")
    print(f"GPT-4 Decision: {result['gpt4_evaluation'].get('decision', 'ERROR')}")
    print(f"Claude Decision: {result['claude_evaluation'].get('decision', 'ERROR')}")
    print(f"Final Decision: {result['final_decision']['decision']}")
    print(f"Requires Human Review: {result['requires_human_review']}")
    print(f"Agreement Score: {result['agreement']['agreement_score']:.2f}")
    
    # Export results
    export_file = evaluator.export_results('/home/ubuntu/systematic_review_app/real_evaluation_test.json')
    print(f"Results exported to: {export_file}")

