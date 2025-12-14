import json
from typing import Dict, List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from app.config import settings
from app.utils.logger import logger
from app.models.schemas import HealthReportData, VulnerabilityItem, TechDebtItem, ModernizationSuggestion
from datetime import datetime


class LLMService:
    """Service for LLM operations with Gemini and round-robin API key rotation"""
    
    def __init__(self):
        """Initialize Gemini LLM with API key rotation"""
        self.api_keys = settings.GOOGLE_API_KEYS
        self.current_key_index = 0
        
        if not self.api_keys:
            raise ValueError("No Google API keys configured")
        
        logger.info(f"LLMService initialized with {len(self.api_keys)} API keys")
    
    def _get_next_api_key(self) -> str:
        """
        Get next API key using round-robin rotation
        
        Returns:
            API key
        """
        key = self.api_keys[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        return key
    
    def _create_llm(self) -> ChatGoogleGenerativeAI:
        """
        Create a new LLM instance with current API key
        
        Returns:
            ChatGoogleGenerativeAI instance
        """
        api_key = self._get_next_api_key()
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=api_key,
            temperature=0.3,
            max_output_tokens=4096
        )
    
    def _create_analysis_prompt(self) -> ChatPromptTemplate:
        """
        Create prompt template for code health analysis
        
        Returns:
            ChatPromptTemplate
        """
        template = """You are an expert code analyst and security auditor. Analyze the following codebase and provide a comprehensive health report.

Repository Information:
- Languages: {languages}
- Dependencies: {dependencies}
- Total Files: {total_files}
- Code Samples Provided: {num_samples}

=== ACTUAL CODE SAMPLES FROM THE REPOSITORY ===
The following are REAL code samples extracted from the codebase. Analyze these specific code patterns, structure, and implementations:

{code_samples}

=== END OF CODE SAMPLES ===

IMPORTANT: You have been provided with {num_samples} actual code samples above. Use these to identify:
- Specific code patterns and practices used
- Actual implementations and architectural decisions
- Concrete code quality issues (not generic assumptions)
- Real security vulnerabilities in the code
- Specific technical debt items based on what you see

Your task is to analyze this codebase and provide a detailed health report in JSON format with the following structure:

{{
  "code_quality_score": <float between 0-100>,
  "vulnerabilities": [
    {{
      "severity": "<critical|high|medium|low>",
      "description": "<detailed description>",
      "affected_component": "<optional component name>",
      "recommendation": "<how to fix>"
    }}
  ],
  "tech_debt_items": [
    {{
      "category": "<code_smell|duplication|complexity|outdated_patterns|etc>",
      "description": "<detailed description>",
      "file_path": "<optional file path>",
      "priority": "<high|medium|low>"
    }}
  ],
  "modernization_suggestions": [
    {{
      "type": "<dependency_upgrade|refactoring|containerization|ci_cd|security|etc>",
      "description": "<detailed description>",
      "rationale": "<why this is important>",
      "effort_estimate": "<low|medium|high>"
    }}
  ],
  "overall_summary": "<comprehensive summary of the codebase health>"
}}

Focus on:
1. Security vulnerabilities (outdated dependencies, insecure patterns)
2. Code quality issues (complexity, maintainability, best practices)
3. Technical debt (deprecated APIs, code smells)
4. Modernization opportunities (containerization, CI/CD, cloud-readiness)

Provide actionable, specific recommendations. Return ONLY valid JSON, no additional text."""

        return ChatPromptTemplate.from_template(template)
    
    def _format_code_samples(self, samples: List[Dict]) -> str:
        """
        Format code samples for prompt with better context
        
        Args:
            samples: List of code sample dicts
            
        Returns:
            Formatted string
        """
        formatted = []
        for idx, sample in enumerate(samples[:20], 1):  # Increased to 20 samples
            metadata = sample.get("metadata", {})
            content = sample.get("content", "")
            file_path = metadata.get("file_path", "unknown")
            language = metadata.get("language", "unknown")
            chunk_index = metadata.get("chunk_index", 0)
            
            # Larger sample size for better context
            truncated_content = content[:1200]
            if len(content) > 1200:
                truncated_content += "\n... (truncated)"
            
            formatted.append(f"""
━━━ Sample {idx}: {file_path} (chunk {chunk_index}) ━━━
Language: {language}
```
{truncated_content}
```
""")
        
        return "\n".join(formatted)
    
    def generate_health_report(
        self,
        languages: Dict[str, int],
        dependencies: Dict[str, List[str]],
        total_files: int,
        code_samples: List[Dict]
    ) -> HealthReportData:
        """
        Generate health report using Gemini
        
        Args:
            languages: Dictionary of detected languages
            dependencies: Dictionary of dependencies by ecosystem
            total_files: Total number of files analyzed
            code_samples: Representative code samples
            
        Returns:
            HealthReportData object
        """
        logger.info(f"Generating health report with Gemini ({len(code_samples)} code samples)")
        
        # Log sample info for debugging
        if code_samples:
            logger.info(f"Sample files: {[s.get('metadata', {}).get('file_path', 'unknown') for s in code_samples[:5]]}...")
        else:
            logger.warning("No code samples provided to LLM!")
        
        # Create LLM instance
        llm = self._create_llm()
        
        # Create prompt
        prompt = self._create_analysis_prompt()
        
        # Format inputs
        languages_str = json.dumps(languages, indent=2)
        dependencies_str = json.dumps(dependencies, indent=2)
        code_samples_str = self._format_code_samples(code_samples)
        
        logger.info(f"Formatted code samples length: {len(code_samples_str)} characters")
        
        # Create chain
        chain = prompt | llm
        
        try:
            # Invoke LLM
            response = chain.invoke({
                "languages": languages_str,
                "dependencies": dependencies_str,
                "total_files": total_files,
                "code_samples": code_samples_str,
                "num_samples": len(code_samples)
            })
            
            # Parse JSON response
            content = response.content
            
            # Extract JSON from markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            report_dict = json.loads(content)
            
            # Convert to Pydantic models
            vulnerabilities = [
                VulnerabilityItem(**vuln) for vuln in report_dict.get("vulnerabilities", [])
            ]
            
            tech_debt = [
                TechDebtItem(**debt) for debt in report_dict.get("tech_debt_items", [])
            ]
            
            modernization = [
                ModernizationSuggestion(**mod) for mod in report_dict.get("modernization_suggestions", [])
            ]
            
            health_report = HealthReportData(
                code_quality_score=report_dict.get("code_quality_score", 50.0),
                vulnerabilities=vulnerabilities,
                tech_debt_items=tech_debt,
                modernization_suggestions=modernization,
                overall_summary=report_dict.get("overall_summary", "Analysis completed"),
                languages_detected=languages,
                dependencies_found=dependencies,
                total_files_analyzed=total_files,
                analysis_timestamp=datetime.utcnow()
            )
            
            logger.info("Successfully generated health report")
            return health_report
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response content: {content}")
            
            # Return fallback report
            return HealthReportData(
                code_quality_score=50.0,
                vulnerabilities=[],
                tech_debt_items=[],
                modernization_suggestions=[],
                overall_summary=f"Analysis failed: Could not parse LLM response. Error: {str(e)}",
                languages_detected=languages,
                dependencies_found=dependencies,
                total_files_analyzed=total_files,
                analysis_timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Failed to generate health report: {e}")
            raise
    
    def query_code_context(self, query: str, code_samples: List[Dict]) -> str:
        """
        Query code context using RAG samples
        
        Args:
            query: Query string
            code_samples: Code samples from RAG
            
        Returns:
            LLM response
        """
        llm = self._create_llm()
        
        code_context = self._format_code_samples(code_samples)
        
        prompt = ChatPromptTemplate.from_template(
            """Based on the following code samples, answer the question:

Question: {query}

Code Context:
{code_context}

Provide a clear, concise answer."""
        )
        
        chain = prompt | llm
        
        try:
            response = chain.invoke({
                "query": query,
                "code_context": code_context
            })
            return response.content
        except Exception as e:
            logger.error(f"Failed to query code context: {e}")
            return f"Error: {str(e)}"
