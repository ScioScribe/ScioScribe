"""
Tavily API integration for web search functionality.

This module provides a comprehensive web search tool using the Tavily API,
enabling planning agents to search for research literature, laboratory protocols,
and current scientific information to enhance their recommendations.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Literal
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

try:
    import requests
except ImportError:
    requests = None

from ..debug import StateDebugger, performance_monitor, log_agent_interaction


class SearchType(str, Enum):
    """Types of searches that can be performed."""
    RESEARCH = "research"
    PROTOCOL = "protocol"
    SAFETY = "safety"
    GENERAL = "general"
    MATERIALS = "materials"
    STATISTICS = "statistics"


@dataclass
class SearchResult:
    """
    Individual search result from Tavily API.
    
    Attributes:
        title: Title of the search result
        url: URL of the source
        content: Main content/snippet from the source
        score: Relevance score (0.0 to 1.0)
        published_date: Publication date if available
        source_type: Type of source (academic, protocol, etc.)
    """
    title: str
    url: str
    content: str
    score: float
    published_date: Optional[str] = None
    source_type: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "title": self.title,
            "url": self.url,
            "content": self.content,
            "score": self.score,
            "published_date": self.published_date,
            "source_type": self.source_type
        }


@dataclass
class SearchResponse:
    """
    Complete search response from Tavily API.
    
    Attributes:
        query: Original search query
        results: List of search results
        search_type: Type of search performed
        total_results: Total number of results found
        search_time: Time taken for the search
        timestamp: When the search was performed
    """
    query: str
    results: List[SearchResult]
    search_type: SearchType
    total_results: int
    search_time: float
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "query": self.query,
            "results": [result.to_dict() for result in self.results],
            "search_type": self.search_type.value,
            "total_results": self.total_results,
            "search_time": self.search_time,
            "timestamp": self.timestamp.isoformat()
        }


class TavilySearchError(Exception):
    """Custom exception for Tavily search errors."""
    
    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(message)
        self.error_code = error_code


class TavilySearchTool:
    """
    Comprehensive Tavily API integration for web search functionality.
    
    This tool provides specialized search capabilities for research literature,
    laboratory protocols, safety information, and general scientific queries.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        debugger: Optional[StateDebugger] = None,
        log_level: str = "INFO"
    ):
        """
        Initialize the Tavily search tool.
        
        Args:
            api_key: Tavily API key (defaults to environment variable)
            debugger: Optional StateDebugger instance for logging
            log_level: Logging level for the tool
        """
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            raise TavilySearchError("Tavily API key not found. Set TAVILY_API_KEY environment variable.")
        
        self.debugger = debugger or StateDebugger(log_level)
        self.logger = logging.getLogger("planning.tools.tavily")
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        self.base_url = "https://api.tavily.com/search"
        self.session = requests.Session() if requests else None
        
        if not self.session:
            raise TavilySearchError("requests library not installed. Install with: pip install requests")
        
        self.logger.info("Tavily search tool initialized")
    
    @performance_monitor
    def search(
        self,
        query: str,
        search_type: SearchType = SearchType.GENERAL,
        max_results: int = 10,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        include_answer: bool = True,
        include_raw_content: bool = False,
        search_depth: Literal["basic", "advanced"] = "basic"
    ) -> SearchResponse:
        """
        Perform a web search using Tavily API.
        
        Args:
            query: Search query string
            search_type: Type of search to perform
            max_results: Maximum number of results to return
            include_domains: List of domains to include in search
            exclude_domains: List of domains to exclude from search
            include_answer: Whether to include AI-generated answer
            include_raw_content: Whether to include raw content
            search_depth: Search depth level
            
        Returns:
            SearchResponse with results and metadata
            
        Raises:
            TavilySearchError: If search fails
        """
        if not query or not query.strip():
            raise TavilySearchError("Search query cannot be empty")
        
        start_time = datetime.now()
        
        # Prepare search payload
        payload = {
            "api_key": self.api_key,
            "query": query.strip(),
            "search_depth": search_depth,
            "include_answer": include_answer,
            "include_raw_content": include_raw_content,
            "max_results": max_results
        }
        
        # Add domain filters if specified
        if include_domains:
            payload["include_domains"] = include_domains
        if exclude_domains:
            payload["exclude_domains"] = exclude_domains
        
        # Customize search based on type
        payload.update(self._get_search_type_config(search_type))
        
        try:
            self.logger.info(f"Performing {search_type.value} search: {query[:100]}...")
            
            response = self.session.post(
                self.base_url,
                json=payload,
                timeout=30,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "ScioScribe-Planning-Agent/1.0"
                }
            )
            
            if response.status_code != 200:
                error_msg = f"Tavily API returned status {response.status_code}"
                if response.text:
                    error_msg += f": {response.text}"
                raise TavilySearchError(error_msg, str(response.status_code))
            
            data = response.json()
            
            # Parse results
            results = []
            for item in data.get("results", []):
                result = SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    content=item.get("content", ""),
                    score=item.get("score", 0.0),
                    published_date=item.get("published_date"),
                    source_type=self._classify_source_type(item.get("url", ""))
                )
                results.append(result)
            
            search_time = (datetime.now() - start_time).total_seconds()
            
            search_response = SearchResponse(
                query=query,
                results=results,
                search_type=search_type,
                total_results=len(results),
                search_time=search_time,
                timestamp=start_time
            )
            
            self.logger.info(f"Search completed: {len(results)} results in {search_time:.2f}s")
            
            # Log search for debugging
            if self.debugger:
                log_agent_interaction(
                    self.debugger,
                    "tavily_search",
                    "search",
                    {"query": query, "search_type": search_type.value},
                    search_response.to_dict()
                )
            
            return search_response
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error during search: {str(e)}"
            self.logger.error(error_msg)
            raise TavilySearchError(error_msg, "network_error")
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON response from Tavily API: {str(e)}"
            self.logger.error(error_msg)
            raise TavilySearchError(error_msg, "json_error")
        except Exception as e:
            error_msg = f"Unexpected error during search: {str(e)}"
            self.logger.error(error_msg)
            raise TavilySearchError(error_msg, "unexpected_error")
    
    def search_research_literature(
        self,
        topic: str,
        max_results: int = 8,
        recent_only: bool = True
    ) -> SearchResponse:
        """
        Search for research literature and academic papers.
        
        Args:
            topic: Research topic to search for
            max_results: Maximum number of results
            recent_only: Whether to prioritize recent publications
            
        Returns:
            SearchResponse with research literature results
        """
        # Enhance query for academic sources
        query = f"{topic} research study academic paper"
        
        # Include academic domains
        include_domains = [
            "pubmed.ncbi.nlm.nih.gov",
            "scholar.google.com",
            "ncbi.nlm.nih.gov",
            "nature.com",
            "science.org",
            "cell.com",
            "plos.org",
            "springer.com",
            "wiley.com",
            "elsevier.com"
        ]
        
        return self.search(
            query=query,
            search_type=SearchType.RESEARCH,
            max_results=max_results,
            include_domains=include_domains,
            search_depth="advanced"
        )
    
    def search_protocols(
        self,
        technique: str,
        organism: Optional[str] = None,
        max_results: int = 6
    ) -> SearchResponse:
        """
        Search for laboratory protocols and procedures.
        
        Args:
            technique: Laboratory technique or procedure
            organism: Specific organism if relevant
            max_results: Maximum number of results
            
        Returns:
            SearchResponse with protocol results
        """
        # Enhance query for protocol sources
        query = f"{technique} protocol procedure method"
        if organism:
            query += f" {organism}"
        
        # Include protocol-specific domains
        include_domains = [
            "protocols.io",
            "nature.com/protocolexchange",
            "currentprotocols.com",
            "bio-protocol.org",
            "springerprotocols.com",
            "jove.com",
            "abcam.com",
            "thermofisher.com",
            "neb.com",
            "promega.com"
        ]
        
        return self.search(
            query=query,
            search_type=SearchType.PROTOCOL,
            max_results=max_results,
            include_domains=include_domains,
            search_depth="advanced"
        )
    
    def search_safety_information(
        self,
        chemical_or_procedure: str,
        max_results: int = 5
    ) -> SearchResponse:
        """
        Search for safety information and MSDS data.
        
        Args:
            chemical_or_procedure: Chemical name or procedure
            max_results: Maximum number of results
            
        Returns:
            SearchResponse with safety information
        """
        # Enhance query for safety sources
        query = f"{chemical_or_procedure} safety MSDS hazard precautions"
        
        # Include safety-specific domains
        include_domains = [
            "cdc.gov",
            "osha.gov",
            "nist.gov",
            "epa.gov",
            "sigmaaldrich.com",
            "fishersci.com",
            "vwr.com",
            "chemwatch.net",
            "pubchem.ncbi.nlm.nih.gov"
        ]
        
        return self.search(
            query=query,
            search_type=SearchType.SAFETY,
            max_results=max_results,
            include_domains=include_domains,
            search_depth="basic"
        )
    
    def search_materials_suppliers(
        self,
        material: str,
        max_results: int = 5
    ) -> SearchResponse:
        """
        Search for material suppliers and specifications.
        
        Args:
            material: Material or equipment name
            max_results: Maximum number of results
            
        Returns:
            SearchResponse with supplier information
        """
        # Enhance query for supplier sources
        query = f"{material} supplier specifications catalog"
        
        # Include supplier domains
        include_domains = [
            "sigmaaldrich.com",
            "thermofisher.com",
            "vwr.com",
            "fishersci.com",
            "neb.com",
            "promega.com",
            "abcam.com",
            "bio-rad.com",
            "qiagen.com",
            "invitrogen.com"
        ]
        
        return self.search(
            query=query,
            search_type=SearchType.MATERIALS,
            max_results=max_results,
            include_domains=include_domains,
            search_depth="basic"
        )
    
    def search_statistical_methods(
        self,
        analysis_type: str,
        max_results: int = 5
    ) -> SearchResponse:
        """
        Search for statistical analysis methods and guidelines.
        
        Args:
            analysis_type: Type of statistical analysis
            max_results: Maximum number of results
            
        Returns:
            SearchResponse with statistical method information
        """
        # Enhance query for statistical sources
        query = f"{analysis_type} statistical analysis method guidelines"
        
        # Include statistical domains
        include_domains = [
            "stat.berkeley.edu",
            "cran.r-project.org",
            "statsmodels.org",
            "scipy.org",
            "graphpad.com",
            "jmp.com",
            "ibm.com/spss",
            "sas.com",
            "stata.com"
        ]
        
        return self.search(
            query=query,
            search_type=SearchType.STATISTICS,
            max_results=max_results,
            include_domains=include_domains,
            search_depth="basic"
        )
    
    def _get_search_type_config(self, search_type: SearchType) -> Dict[str, Any]:
        """
        Get search configuration based on search type.
        
        Args:
            search_type: Type of search to configure
            
        Returns:
            Dictionary with search configuration
        """
        config = {}
        
        if search_type == SearchType.RESEARCH:
            config.update({
                "include_answer": True,
                "include_raw_content": False,
                "search_depth": "advanced"
            })
        elif search_type == SearchType.PROTOCOL:
            config.update({
                "include_answer": False,
                "include_raw_content": True,
                "search_depth": "advanced"
            })
        elif search_type == SearchType.SAFETY:
            config.update({
                "include_answer": True,
                "include_raw_content": False,
                "search_depth": "basic"
            })
        else:
            config.update({
                "include_answer": True,
                "include_raw_content": False,
                "search_depth": "basic"
            })
        
        return config
    
    def _classify_source_type(self, url: str) -> str:
        """
        Classify the source type based on URL.
        
        Args:
            url: URL to classify
            
        Returns:
            Source type classification
        """
        if not url:
            return "unknown"
        
        url_lower = url.lower()
        
        # Academic sources
        if any(domain in url_lower for domain in ["pubmed", "scholar", "ncbi", "nature", "science", "cell", "plos"]):
            return "academic"
        
        # Protocol sources
        if any(domain in url_lower for domain in ["protocols.io", "protocolexchange", "currentprotocols", "bio-protocol"]):
            return "protocol"
        
        # Safety sources
        if any(domain in url_lower for domain in ["cdc.gov", "osha.gov", "nist.gov", "epa.gov"]):
            return "safety"
        
        # Commercial sources
        if any(domain in url_lower for domain in ["sigma", "thermo", "fisher", "vwr", "neb", "promega"]):
            return "commercial"
        
        return "general"
    
    def get_search_history(self) -> List[Dict[str, Any]]:
        """
        Get search history from debugger logs.
        
        Returns:
            List of search history entries
        """
        if not self.debugger:
            return []
        
        # This would integrate with the debugger's history functionality
        # For now, return empty list
        return []
    
    def clear_search_history(self) -> None:
        """Clear search history."""
        if self.debugger:
            # This would integrate with the debugger's history clearing
            pass
        
        self.logger.info("Search history cleared")


# Convenience functions for common search patterns
def search_for_research(topic: str, api_key: Optional[str] = None) -> SearchResponse:
    """
    Convenience function for research literature search.
    
    Args:
        topic: Research topic
        api_key: Optional API key
        
    Returns:
        SearchResponse with research results
    """
    tool = TavilySearchTool(api_key=api_key)
    return tool.search_research_literature(topic)


def search_for_protocol(technique: str, organism: Optional[str] = None, api_key: Optional[str] = None) -> SearchResponse:
    """
    Convenience function for protocol search.
    
    Args:
        technique: Laboratory technique
        organism: Optional organism
        api_key: Optional API key
        
    Returns:
        SearchResponse with protocol results
    """
    tool = TavilySearchTool(api_key=api_key)
    return tool.search_protocols(technique, organism)


def search_for_safety(chemical: str, api_key: Optional[str] = None) -> SearchResponse:
    """
    Convenience function for safety information search.
    
    Args:
        chemical: Chemical name
        api_key: Optional API key
        
    Returns:
        SearchResponse with safety information
    """
    tool = TavilySearchTool(api_key=api_key)
    return tool.search_safety_information(chemical) 