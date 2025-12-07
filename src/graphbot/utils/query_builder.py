"""Query validation and sanitization for Cypher queries."""
import re
from typing import Optional


class QueryBuilder:
    """Validates and sanitizes Cypher queries."""
    
    # Dangerous operations that should be confirmed
    DANGEROUS_PATTERNS = [
        r'\bDROP\s+DATABASE\b',
        r'\bDROP\s+INDEX\b',
        r'\bDROP\s+CONSTRAINT\b',
        r'\bDETACH\s+DELETE\s+\w+\s*$',  # DETACH DELETE without WHERE
        # r'MATCH\s*\([^\)]+\)\s*,\s*\([^\)]+\)', # Cartesian product detection (moved to specific check)
    ]
    
    @staticmethod
    def validate_query(query: str) -> tuple[bool, Optional[str]]:
        """
        Validate a Cypher query for basic syntax and safety.
        
        Args:
            query: Cypher query string
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not query or not query.strip():
            return False, "Query is empty"
        
        query_upper = query.upper().strip()
        
        # Check for dangerous patterns
        for pattern in QueryBuilder.DANGEROUS_PATTERNS:
            if re.search(pattern, query_upper, re.IGNORECASE):
                return False, f"Potentially dangerous operation detected: {pattern}"
        
        # Check for Cartesian products (unconnected components)
        # Matches: MATCH (a), (b)
        # But avoids: MATCH (a)-[:REL]->(b)
        # This is a heuristic and might flag valid implicit joins, but we want to encourage explicit relationships
        if re.search(r'MATCH\s*\([^\)]+\)\s*,\s*\([^\)]+\)', query_upper):
             return False, "Cartesian product detected (disconnected patterns in MATCH). Use explicit relationships (e.g. (a)-[:REL]->(b)) instead of commas."

        # Basic syntax checks
        if not any(keyword in query_upper for keyword in ['MATCH', 'CREATE', 'MERGE', 'DELETE', 'SET', 'REMOVE', 'RETURN', 'CALL']):
            return False, "Query must contain at least one Cypher keyword (MATCH, CREATE, etc.)"
        
        return True, None
    
    @staticmethod
    def sanitize_query(query: str) -> str:
        """
        Sanitize query by removing extra whitespace and comments.
        Also enforces result limits for safety.

        Args:
            query: Raw query string

        Returns:
            Sanitized query string
        """
        if query is None:
            return ""

        # Remove single-line comments
        lines = query.split('\n')
        cleaned_lines = []
        for line in lines:
            # Remove comments (// style)
            if '//' in line:
                line = line[:line.index('//')]
            cleaned_lines.append(line.strip())
        
        # Join and clean up multiple spaces
        cleaned = ' '.join(cleaned_lines)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = cleaned.strip()
        
        # Auto-inject LIMIT if not present in RETURN queries
        # We check if it's a read query (has RETURN) and doesn't have LIMIT
        query_upper = cleaned.upper()
        aggregations = ['COUNT(', 'SUM(', 'AVG(', 'COLLECT(', 'MIN(', 'MAX(']
        has_aggregation = any(agg in query_upper for agg in aggregations)
        
        if 'RETURN' in query_upper and 'LIMIT' not in query_upper and not has_aggregation:
            # Don't add limit to count queries if that's the only thing
            # Simple heuristic: if it looks like a list query
            cleaned += " LIMIT 100"
        
        return cleaned
    
    @staticmethod
    def is_read_only(query: str) -> bool:
        """
        Check if query is read-only (doesn't modify data).
        
        Args:
            query: Cypher query string
            
        Returns:
            True if query is read-only
        """
        query_upper = query.upper()
        write_keywords = ['CREATE', 'MERGE', 'DELETE', 'DETACH', 'SET', 'REMOVE', 'FOREACH']
        
        for keyword in write_keywords:
            if keyword in query_upper:
                return False
        
        return True
    
    @staticmethod
    def format_query_for_display(query: str) -> str:
        """
        Format query for better readability in console.

        Args:
            query: Cypher query string

        Returns:
            Formatted query string
        """
        if query is None:
            return ""

        # Add line breaks after major clauses
        formatted = re.sub(r'\b(MATCH|CREATE|MERGE|DELETE|SET|RETURN|WHERE|WITH|UNWIND)\b', r'\n\1', query, flags=re.IGNORECASE)
        formatted = re.sub(r'\s+', ' ', formatted)
        formatted = formatted.strip()

        return formatted
