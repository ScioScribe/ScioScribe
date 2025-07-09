"""
Enhanced Intent Classification System for Conversational Data Cleaning

This module provides sophisticated natural language understanding for data operations,
including intent classification, parameter extraction, and confidence scoring.
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .state_schema import Intent, FileFormat

logger = logging.getLogger(__name__)


@dataclass
class IntentClassificationResult:
    """Result of intent classification with confidence and parameters."""
    intent: Intent
    confidence: float
    extracted_parameters: Dict[str, Any]
    alternative_intents: List[Tuple[Intent, float]]
    reasoning: str


@dataclass
class ParameterExtractionResult:
    """Result of parameter extraction from user message."""
    parameters: Dict[str, Any]
    confidence: float
    extracted_entities: List[Dict[str, Any]]


class IntentPattern:
    """Pattern matching for intent classification."""
    
    def __init__(self, intent: Intent, patterns: List[str], keywords: List[str], 
                 weight: float = 1.0, requires_data: bool = False):
        self.intent = intent
        self.patterns = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
        self.keywords = [kw.lower() for kw in keywords]
        self.weight = weight
        self.requires_data = requires_data


class EnhancedIntentClassifier:
    """
    Enhanced intent classification system with NLU capabilities.
    
    This classifier provides:
    - Pattern-based intent recognition
    - Parameter extraction from natural language
    - Confidence scoring
    - CSV/Excel specific intent handling
    - Fallback and alternative suggestions
    """
    
    def __init__(self):
        """Initialize the enhanced intent classifier."""
        self.intent_patterns = self._initialize_intent_patterns()
        self.parameter_extractors = self._initialize_parameter_extractors()
        self.fallback_threshold = 0.3
        
        logger.info("Initialized enhanced intent classifier")
    
    def _initialize_intent_patterns(self) -> List[IntentPattern]:
        """Initialize intent patterns for classification."""
        return [
            # Data Exploration Intents
            IntentPattern(
                Intent.SHOW_DATA,
                patterns=[
                    r"show\s+me.*?(?:first|top|head)?\s*(\d+)?\s*(?:rows?|records?|entries?)",
                    r"display.*?(?:first|top|head)?\s*(\d+)?\s*(?:rows?|records?)",
                    r"view.*?(?:first|top|head)?\s*(\d+)?\s*(?:rows?|records?)",
                    r"(?:first|top|head)\s*(\d+)?\s*(?:rows?|records?)",
                    r"preview.*?data",
                    r"sample.*?data"
                ],
                keywords=["show", "display", "view", "preview", "sample", "head", "first", "top"],
                weight=1.0,
                requires_data=True
            ),
            
            IntentPattern(
                Intent.DESCRIBE,
                patterns=[
                    r"describe.*?(?:data|dataset|structure|columns?)",
                    r"(?:what\s+is|tell\s+me\s+about).*?(?:data|dataset|structure)",
                    r"(?:data|dataset)\s+(?:info|information|summary|overview)",
                    r"(?:columns?|fields?)\s+(?:info|information|list)",
                    r"schema.*?(?:data|dataset)",
                    r"structure.*?(?:data|dataset)"
                ],
                keywords=["describe", "info", "information", "summary", "overview", "structure", "schema"],
                weight=1.0,
                requires_data=True
            ),
            
            IntentPattern(
                Intent.ANALYZE,
                patterns=[
                    r"analy[sz]e.*?(?:data|quality|issues?)",
                    r"(?:data|quality)\s+analy[sz]is",
                    r"check.*?(?:quality|issues?|problems?)",
                    r"find.*?(?:issues?|problems?|errors?)",
                    r"(?:quality|health)\s+(?:check|report|assessment)",
                    r"(?:what|any)\s+(?:issues?|problems?|errors?)",
                    r"statistics?.*?(?:data|dataset)",
                    r"profil(?:e|ing).*?data"
                ],
                keywords=["analyze", "analysis", "quality", "check", "issues", "problems", "statistics", "profile"],
                weight=1.0,
                requires_data=True
            ),
            
            # Data Cleaning Intents
            IntentPattern(
                Intent.CLEAN,
                patterns=[
                    r"clean.*?(?:data|dataset|columns?|field)",
                    r"fix.*?(?:data|issues?|problems?|errors?)",
                    r"correct.*?(?:data|values?|entries?)",
                    r"standardize.*?(?:data|format|values?)",
                    r"normalize.*?(?:data|values?)",
                    r"sanitize.*?(?:data|input)"
                ],
                keywords=["clean", "fix", "correct", "standardize", "normalize", "sanitize"],
                weight=1.0,
                requires_data=True
            ),
            
            IntentPattern(
                Intent.REMOVE,
                patterns=[
                    r"remove.*?(?:duplicates?|rows?|columns?|outliers?)",
                    r"delete.*?(?:rows?|columns?|entries?|records?)",
                    r"drop.*?(?:rows?|columns?|duplicates?)",
                    r"eliminate.*?(?:duplicates?|outliers?)",
                    r"filter\s+out.*?(?:rows?|values?)"
                ],
                keywords=["remove", "delete", "drop", "eliminate", "filter out"],
                weight=1.0,
                requires_data=True
            ),
            
            # Data Transformation Intents
            IntentPattern(
                Intent.CONVERT,
                patterns=[
                    r"convert.*?(?:to|into|format|type)",
                    r"change.*?(?:type|format|encoding)",
                    r"transform.*?(?:data|values?|format)",
                    r"cast.*?(?:to|as)\s+\w+",
                    r"format.*?(?:as|to)\s+\w+"
                ],
                keywords=["convert", "change", "transform", "cast", "format"],
                weight=1.0,
                requires_data=True
            ),
            
            # File-Specific Intents (CSV/Excel)
            IntentPattern(
                Intent.SELECT_SHEET,
                patterns=[
                    r"(?:select|choose|switch\s+to|use)\s+sheet\s*(\w+|\d+)",
                    r"sheet\s*(\w+|\d+)",
                    r"(?:which|what)\s+sheets?\s+(?:are\s+)?available",
                    r"list\s+sheets?",
                    r"show\s+(?:me\s+)?(?:all\s+)?sheets?"
                ],
                keywords=["sheet", "sheets", "tab", "tabs", "select", "switch", "choose"],
                weight=1.2
            ),
            
            IntentPattern(
                Intent.DETECT_DELIMITER,
                patterns=[
                    r"(?:what|which)\s+(?:is\s+the\s+)?delimiter",
                    r"detect.*?delimiter",
                    r"find.*?separator",
                    r"(?:comma|semicolon|tab|pipe)\s+separated",
                    r"csv\s+format",
                    r"change\s+delimiter"
                ],
                keywords=["delimiter", "separator", "comma", "semicolon", "tab", "pipe", "csv"],
                weight=1.2
            ),
            
            IntentPattern(
                Intent.ENCODING_ISSUE,
                patterns=[
                    r"encoding\s+(?:issues?|problems?|errors?)",
                    r"character\s+encoding",
                    r"utf-?8|ascii|latin-?1",
                    r"special\s+characters?.*?(?:not\s+displaying|broken|wrong)"
                ],
                keywords=["encoding", "utf8", "ascii", "characters", "charset"],
                weight=1.1
            ),
            
            # Session Management Intents
            IntentPattern(
                Intent.UNDO,
                patterns=[
                    r"undo.*?(?:last|previous|that)",
                    r"revert.*?(?:changes?|last|previous)",
                    r"go\s+back",
                    r"cancel.*?(?:last|previous|that)"
                ],
                keywords=["undo", "revert", "back", "cancel", "rollback"],
                weight=1.0
            ),
            
            IntentPattern(
                Intent.SAVE,
                patterns=[
                    r"save.*?(?:data|changes?|file|results?)",
                    r"export.*?(?:data|to|as)",
                    r"download.*?(?:data|file|results?)",
                    r"write.*?(?:to\s+)?file"
                ],
                keywords=["save", "export", "download", "write", "output"],
                weight=1.0
            )
        ]
    
    def _initialize_parameter_extractors(self) -> Dict[str, Any]:
        """Initialize parameter extraction patterns."""
        return {
            "numbers": re.compile(r"\b(\d+)\b"),
            "column_names": re.compile(r"column\s+['\"]?(\w+)['\"]?|['\"]?(\w+)['\"]?\s+column", re.IGNORECASE),
            "file_formats": re.compile(r"\b(csv|excel|xlsx?|json|parquet)\b", re.IGNORECASE),
            "sheet_names": re.compile(r"sheet\s+['\"]?(\w+|\d+)['\"]?", re.IGNORECASE),
            "delimiters": re.compile(r"\b(comma|semicolon|tab|pipe|,|;|\t|\|)\b", re.IGNORECASE),
            "encodings": re.compile(r"\b(utf-?8|ascii|latin-?1|iso-\d+)\b", re.IGNORECASE),
            "operations": re.compile(r"\b(first|last|top|bottom|head|tail)\s+(\d+)", re.IGNORECASE),
            "data_types": re.compile(r"\b(string|int|integer|float|date|datetime|boolean|bool)\b", re.IGNORECASE),
            "aggregations": re.compile(r"\b(sum|count|average|mean|median|max|min|std|var)\b", re.IGNORECASE)
        }
    
    async def classify_intent(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> IntentClassificationResult:
        """
        Classify user intent with confidence scoring and parameter extraction.
        
        Args:
            message: User's natural language message
            context: Optional conversation context
            
        Returns:
            IntentClassificationResult with intent, confidence, and parameters
        """
        try:
            # Normalize message
            normalized_message = message.strip().lower()
            
            # Calculate scores for all intents
            intent_scores = []
            
            for pattern in self.intent_patterns:
                score = await self._calculate_intent_score(normalized_message, pattern, context)
                if score > 0:
                    intent_scores.append((pattern.intent, score))
            
            # Sort by score
            intent_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Determine primary intent
            if intent_scores and intent_scores[0][1] >= self.fallback_threshold:
                primary_intent = intent_scores[0][0]
                confidence = intent_scores[0][1]
                alternatives = intent_scores[1:4]  # Top 3 alternatives
            else:
                primary_intent = Intent.UNKNOWN
                confidence = 0.0
                alternatives = intent_scores[:3]
            
            # Extract parameters
            parameters = await self._extract_parameters(message, primary_intent, context)
            
            # Generate reasoning
            reasoning = await self._generate_reasoning(message, primary_intent, confidence, parameters)
            
            result = IntentClassificationResult(
                intent=primary_intent,
                confidence=confidence,
                extracted_parameters=parameters,
                alternative_intents=alternatives,
                reasoning=reasoning
            )
            
            logger.info(f"Classified intent: {primary_intent.value} (confidence: {confidence:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"Error in intent classification: {str(e)}")
            return IntentClassificationResult(
                intent=Intent.UNKNOWN,
                confidence=0.0,
                extracted_parameters={},
                alternative_intents=[],
                reasoning=f"Classification failed: {str(e)}"
            )
    
    async def _calculate_intent_score(
        self,
        message: str,
        pattern: IntentPattern,
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate score for a specific intent pattern."""
        score = 0.0
        
        # Pattern matching
        pattern_matches = 0
        for regex_pattern in pattern.patterns:
            if regex_pattern.search(message):
                pattern_matches += 1
        
        # Keyword matching
        keyword_matches = 0
        for keyword in pattern.keywords:
            if keyword in message:
                keyword_matches += 1
        
        # Calculate base score
        if pattern_matches > 0:
            score += 0.7 * pattern.weight
        
        if keyword_matches > 0:
            keyword_score = min(keyword_matches / len(pattern.keywords), 1.0) * 0.5
            score += keyword_score * pattern.weight
        
        # Context-based adjustments
        if context:
            # Data availability check
            if pattern.requires_data:
                has_data = context.get("data_context") is not None
                if not has_data:
                    score *= 0.7  # Reduce score if data is required but not available
            
            # File format specific adjustments
            file_format = context.get("file_format")
            if pattern.intent in [Intent.SELECT_SHEET] and file_format != FileFormat.EXCEL:
                score *= 0.3  # Reduce sheet selection score for non-Excel files
            elif pattern.intent in [Intent.DETECT_DELIMITER] and file_format != FileFormat.CSV:
                score *= 0.3  # Reduce delimiter detection score for non-CSV files
        
        return min(score, 1.0)
    
    async def _extract_parameters(
        self,
        message: str,
        intent: Intent,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extract parameters from the user message based on intent."""
        parameters = {}
        
        try:
            # Extract numbers
            numbers = self.parameter_extractors["numbers"].findall(message)
            if numbers:
                parameters["numbers"] = [int(n) for n in numbers]
            
            # Intent-specific parameter extraction
            if intent == Intent.SHOW_DATA:
                # Extract number of rows
                operations = self.parameter_extractors["operations"].findall(message)
                if operations:
                    parameters["operation"] = operations[0][0].lower()
                    parameters["n_rows"] = int(operations[0][1])
                elif numbers:
                    parameters["n_rows"] = int(numbers[0])
                else:
                    parameters["n_rows"] = 10  # Default
            
            elif intent == Intent.SELECT_SHEET:
                # Extract sheet name or number
                sheet_matches = self.parameter_extractors["sheet_names"].findall(message)
                if sheet_matches:
                    for match in sheet_matches:
                        sheet_name = match[0] if match[0] else match[1]
                        if sheet_name:
                            parameters["sheet_name"] = sheet_name
                            break
            
            elif intent == Intent.DETECT_DELIMITER:
                # Extract specific delimiter mentions
                delimiter_matches = self.parameter_extractors["delimiters"].findall(message)
                if delimiter_matches:
                    delimiter_map = {
                        "comma": ",", ",": ",",
                        "semicolon": ";", ";": ";",
                        "tab": "\t", "\t": "\t",
                        "pipe": "|", "|": "|"
                    }
                    delimiter = delimiter_matches[0].lower()
                    parameters["preferred_delimiter"] = delimiter_map.get(delimiter, delimiter)
            
            elif intent == Intent.ENCODING_ISSUE:
                # Extract encoding mentions
                encoding_matches = self.parameter_extractors["encodings"].findall(message)
                if encoding_matches:
                    parameters["encoding"] = encoding_matches[0].lower().replace("-", "")
            
            elif intent in [Intent.CLEAN, Intent.REMOVE, Intent.CONVERT]:
                # Extract column names
                column_matches = self.parameter_extractors["column_names"].findall(message)
                if column_matches:
                    columns = []
                    for match in column_matches:
                        column_name = match[0] if match[0] else match[1]
                        if column_name:
                            columns.append(column_name)
                    if columns:
                        parameters["columns"] = columns
                
                # Extract data types for conversion
                if intent == Intent.CONVERT:
                    type_matches = self.parameter_extractors["data_types"].findall(message)
                    if type_matches:
                        parameters["target_type"] = type_matches[0].lower()
            
            elif intent == Intent.ANALYZE:
                # Extract aggregation functions
                agg_matches = self.parameter_extractors["aggregations"].findall(message)
                if agg_matches:
                    parameters["aggregations"] = [agg.lower() for agg in agg_matches]
            
            # Extract file format mentions
            format_matches = self.parameter_extractors["file_formats"].findall(message)
            if format_matches:
                parameters["file_format"] = format_matches[0].lower()
            
            logger.debug(f"Extracted parameters for {intent.value}: {parameters}")
            return parameters
            
        except Exception as e:
            logger.error(f"Error extracting parameters: {str(e)}")
            return {}
    
    async def _generate_reasoning(
        self,
        message: str,
        intent: Intent,
        confidence: float,
        parameters: Dict[str, Any]
    ) -> str:
        """Generate reasoning for the classification decision."""
        if intent == Intent.UNKNOWN:
            return f"Could not classify message '{message}' with sufficient confidence (threshold: {self.fallback_threshold})"
        
        reasoning_parts = [
            f"Classified as '{intent.value}' with {confidence:.1%} confidence"
        ]
        
        if parameters:
            param_descriptions = []
            for key, value in parameters.items():
                if isinstance(value, list):
                    param_descriptions.append(f"{key}: {', '.join(map(str, value))}")
                else:
                    param_descriptions.append(f"{key}: {value}")
            
            if param_descriptions:
                reasoning_parts.append(f"Extracted parameters: {'; '.join(param_descriptions)}")
        
        return ". ".join(reasoning_parts)
    
    async def get_intent_suggestions(self, partial_message: str) -> List[Dict[str, Any]]:
        """Get intent suggestions for partial user input."""
        suggestions = []
        
        try:
            # Simple prefix matching for suggestions
            partial_lower = partial_message.lower()
            
            suggestion_templates = {
                Intent.SHOW_DATA: [
                    "show me the first 10 rows",
                    "display data sample",
                    "view first 5 records"
                ],
                Intent.ANALYZE: [
                    "analyze data quality",
                    "check for issues",
                    "find problems in data"
                ],
                Intent.DESCRIBE: [
                    "describe my data",
                    "show data structure",
                    "what columns do I have"
                ],
                Intent.CLEAN: [
                    "clean my data",
                    "fix data issues",
                    "standardize values"
                ],
                Intent.SELECT_SHEET: [
                    "switch to sheet 2",
                    "select Sheet1",
                    "which sheets are available"
                ],
                Intent.DETECT_DELIMITER: [
                    "what delimiter is used",
                    "detect CSV separator",
                    "change delimiter"
                ]
            }
            
            for intent, templates in suggestion_templates.items():
                for template in templates:
                    if template.startswith(partial_lower) or any(word in template for word in partial_lower.split()):
                        suggestions.append({
                            "intent": intent.value,
                            "template": template,
                            "completion": template[len(partial_lower):] if template.startswith(partial_lower) else template
                        })
                        
                        if len(suggestions) >= 5:  # Limit suggestions
                            break
                
                if len(suggestions) >= 5:
                    break
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error generating intent suggestions: {str(e)}")
            return [] 