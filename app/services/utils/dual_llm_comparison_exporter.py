import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils.dataframe import dataframe_to_rows
from typing import List, Dict, Any, Optional
import json
import os
from datetime import datetime

from app.models.screening_models import Article


class DualLLMComparisonExporter:
    """
    Exports dual-LLM screening results to color-coded Excel spreadsheets for comparison analysis.
    """
    
    def __init__(self):
        self.openai_fill = PatternFill(start_color="ADD8E6", end_color="ADD8E6", fill_type="solid")  # Light Blue
        self.anthropic_fill = PatternFill(start_color="FFB6C1", end_color="FFB6C1", fill_type="solid")  # Light Pink
        self.agreement_fill = PatternFill(start_color="90EE90", end_color="90EE90", fill_type="solid")  # Light Green
        self.disagreement_fill = PatternFill(start_color="FFFFE0", end_color="FFFFE0", fill_type="solid")  # Light Yellow
        
        self.header_font = Font(bold=True)
        self.center_alignment = Alignment(horizontal="center", vertical="center")
    
    def extract_first_author_year(self, article: Article) -> str:
        """Extract first author and year for study identification."""
        authors = article.authors or ""
        first_author = authors.split(',')[0].strip() if authors else "Unknown"
        year = str(article.year) if article.year else "Unknown"
        return f"{first_author}, {year}"
    
    def extract_pico_elements(self, result: Dict[str, Any]) -> Dict[str, str]:
        """Extract PICO-TT elements with exact quotes."""
        pico = result.get('picott_extraction', {})
        return {
            'Population': ', '.join(pico.get('population', [])) if pico.get('population') else 'Not found',
            'Intervention': ', '.join(pico.get('intervention', [])) if pico.get('intervention') else 'Not found',
            'Comparison': ', '.join(pico.get('comparison', [])) if pico.get('comparison') else 'Not found',
            'Outcomes': ', '.join(pico.get('outcomes', [])) if pico.get('outcomes') else 'Not found',
            'Time': pico.get('time_frame', 'Not found'),
            'Study_Type': pico.get('study_type', 'Not found')
        }
    
    def parse_decision_reasoning(self, decision_reasoning: str) -> Dict[str, Any]:
        """Parse the JSON decision_reasoning field to extract dual-LLM results."""
        try:
            data = json.loads(decision_reasoning)
            return data
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def extract_llm_results(self, decision_data: Dict[str, Any]) -> tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Extract OpenAI and Anthropic results from decision data."""
        openai_result = decision_data.get('openai_result')
        anthropic_result = decision_data.get('anthropic_result')
        
        return openai_result, anthropic_result
    
    def determine_agreement_status(self, openai_result: Optional[Dict[str, Any]], 
                                 anthropic_result: Optional[Dict[str, Any]]) -> str:
        """Determine if the two LLMs agree on the screening decision."""
        if not openai_result or not anthropic_result:
            return "Incomplete"
        
        openai_decision = openai_result.get('screening_decision', {}).get('final_decision')
        anthropic_decision = anthropic_result.get('screening_decision', {}).get('final_decision')
        
        if openai_decision == anthropic_decision:
            return "Agreement"
        else:
            return "Disagreement"
    
    def generate_comparison_spreadsheet(self, articles: List[Article], project_name: str) -> str:
        """Generate Excel spreadsheet with dual-LLM comparison."""
        
        comparison_data = []
        
        for article in articles:
            if not article.decision_reasoning:
                continue
            
            decision_data = self.parse_decision_reasoning(article.decision_reasoning)
            if not decision_data:
                continue
            
            openai_result, anthropic_result = self.extract_llm_results(decision_data)
            
            if not openai_result or not anthropic_result:
                continue
            
            study_id = self.extract_first_author_year(article)
            agreement_status = self.determine_agreement_status(openai_result, anthropic_result)
            
            openai_pico = self.extract_pico_elements(openai_result)
            anthropic_pico = self.extract_pico_elements(anthropic_result)
            
            row_data = {
                'Study_ID': study_id,
                'Title': article.title or 'Unknown',
                
                'Population_OpenAI': openai_pico['Population'],
                'Population_Anthropic': anthropic_pico['Population'],
                'Intervention_OpenAI': openai_pico['Intervention'],
                'Intervention_Anthropic': anthropic_pico['Intervention'],
                'Comparison_OpenAI': openai_pico['Comparison'],
                'Comparison_Anthropic': anthropic_pico['Comparison'],
                'Outcomes_OpenAI': openai_pico['Outcomes'],
                'Outcomes_Anthropic': anthropic_pico['Outcomes'],
                'Time_OpenAI': openai_pico['Time'],
                'Time_Anthropic': anthropic_pico['Time'],
                'Study_Type_OpenAI': openai_pico['Study_Type'],
                'Study_Type_Anthropic': anthropic_pico['Study_Type'],
                
                'Inclusion_Criteria_OpenAI': 'Yes' if openai_result.get('criteria_evaluation', {}).get('meets_inclusion_criteria') else 'No',
                'Inclusion_Criteria_Anthropic': 'Yes' if anthropic_result.get('criteria_evaluation', {}).get('meets_inclusion_criteria') else 'No',
                'Inclusion_Reasoning_OpenAI': openai_result.get('criteria_evaluation', {}).get('inclusion_reasoning', 'Not provided'),
                'Inclusion_Reasoning_Anthropic': anthropic_result.get('criteria_evaluation', {}).get('inclusion_reasoning', 'Not provided'),
                
                'Exclusion_Criteria_OpenAI': 'Yes' if openai_result.get('criteria_evaluation', {}).get('violates_exclusion_criteria') else 'No',
                'Exclusion_Criteria_Anthropic': 'Yes' if anthropic_result.get('criteria_evaluation', {}).get('violates_exclusion_criteria') else 'No',
                'Exclusion_Reasoning_OpenAI': openai_result.get('criteria_evaluation', {}).get('exclusion_reasoning', 'Not provided'),
                'Exclusion_Reasoning_Anthropic': anthropic_result.get('criteria_evaluation', {}).get('exclusion_reasoning', 'Not provided'),
                
                'Final_Decision_OpenAI': openai_result.get('screening_decision', {}).get('final_decision', 'Unknown'),
                'Final_Decision_Anthropic': anthropic_result.get('screening_decision', {}).get('final_decision', 'Unknown'),
                'Confidence_OpenAI': f"{openai_result.get('screening_decision', {}).get('confidence_score', 0):.2f}",
                'Confidence_Anthropic': f"{anthropic_result.get('screening_decision', {}).get('confidence_score', 0):.2f}",
                'Reasoning_OpenAI': openai_result.get('screening_decision', {}).get('detailed_reasoning', 'Not provided'),
                'Reasoning_Anthropic': anthropic_result.get('screening_decision', {}).get('detailed_reasoning', 'Not provided'),
                
                'Agreement_Status': agreement_status
            }
            
            comparison_data.append(row_data)
        
        if not comparison_data:
            raise ValueError("No dual-LLM screening results found to export")
        
        df = pd.DataFrame(comparison_data)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{project_name}_dual_llm_comparison_{timestamp}.xlsx"
        filepath = os.path.join('/tmp', filename)
        
        self._create_formatted_excel(df, filepath)
        
        return filepath
    
    def _create_formatted_excel(self, df: pd.DataFrame, filepath: str):
        """Create Excel file with color-coded formatting."""
        wb = Workbook()
        ws = wb.active
        ws.title = "Dual-LLM Comparison"
        
        for r in dataframe_to_rows(df, index=False, header=True):
            ws.append(r)
        
        for cell in ws[1]:
            cell.font = self.header_font
            cell.alignment = self.center_alignment
        
        for row_idx, row in enumerate(ws.iter_rows(min_row=2), start=2):
            for col_idx, cell in enumerate(row, start=1):
                column_name = ws.cell(row=1, column=col_idx).value
                
                if column_name and '_OpenAI' in column_name:
                    cell.fill = self.openai_fill
                elif column_name and '_Anthropic' in column_name:
                    cell.fill = self.anthropic_fill
                elif column_name == 'Agreement_Status':
                    if cell.value == 'Agreement':
                        cell.fill = self.agreement_fill
                    elif cell.value == 'Disagreement':
                        cell.fill = self.disagreement_fill
        
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
        
        wb.save(filepath)
