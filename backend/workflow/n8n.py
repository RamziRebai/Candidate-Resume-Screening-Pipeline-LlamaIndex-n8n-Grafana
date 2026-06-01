import os
import logging
from datetime import datetime
from typing import Dict, Any, List
import asyncio
import httpx

logger = logging.getLogger(__name__)
class N8nWebhookClient:
    """Client for sending reports to n8n webhook endpoints"""
    
    def __init__(self, webhook_url: str = None):
        # Load from environment variables if not provided
        self.webhook_url = webhook_url or os.getenv(
            "N8N_WEBHOOK_URL", 
            "http://localhost:5678/webhook/rag-report-processor"
        )
        
        self.timeout = float(os.getenv("N8N_WEBHOOK_TIMEOUT", "30.0"))
        self.max_retries = int(os.getenv("N8N_WEBHOOK_MAX_RETRIES", "3"))
        self.enabled = os.getenv("N8N_WEBHOOK_ENABLED", "true").lower() == "true"
        
        self.logger = logging.getLogger(f"{__name__}.N8nWebhookClient")
        
        self.logger.info(f"N8n webhook client initialized:")
        self.logger.info(f"  URL: {self.webhook_url}")
        self.logger.info(f"  Timeout: {self.timeout}s")
        self.logger.info(f"  Max retries: {self.max_retries}")
        self.logger.info(f"  Enabled: {self.enabled}")
        
    async def send_report(self, report_data: Dict[str, Any], session_id: str = None) -> Dict[str, Any]:
        """
        Send workflow report to n8n webhook endpoint
        
        Args:
            report_data: The complete workflow report data
            session_id: Optional session identifier for tracking
            
        Returns:
            Dict containing success status and response data
        """
        # Check if webhook is enabled
        if not self.enabled:
            self.logger.info("N8n webhook is disabled - skipping report transmission")
            return {
                "success": False,
                "error": "N8n webhook is disabled",
                "webhook_url": self.webhook_url,
                "skipped": True,
                "timestamp": datetime.now().isoformat()
            }
        
        attempt = 0
        last_error = None
        
        # Add metadata to report
        enriched_report = self._enrich_report_data(report_data, session_id)
        
        while attempt < self.max_retries:
            try:
                attempt += 1
                self.logger.info(f"Sending report to n8n webhook (attempt {attempt}/{self.max_retries})")
                
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        self.webhook_url,
                        json=enriched_report,
                        headers={
                            "Content-Type": "application/json",
                            "User-Agent": "LlamaIndex-ResumeMatcherv2.0",
                            "X-Source": "resume-matcher-workflow",
                            "X-Session-ID": session_id or "unknown",
                            "X-Timestamp": datetime.now().isoformat()
                        }
                    )
                    
                    # Check if request was successful
                    response.raise_for_status()
                    
                    # Parse response
                    response_data = response.json() if response.content else {}
                    
                    self.logger.info(f"✅ Report successfully sent to n8n webhook (HTTP {response.status_code})")
                    self.logger.debug(f"Response from n8n: {response_data}")
                    
                    return {
                        "success": True,
                        "status_code": response.status_code,
                        "response": response_data,
                        "webhook_url": self.webhook_url,
                        "attempt": attempt,
                        "timestamp": datetime.now().isoformat()
                    }
                    
            except httpx.TimeoutException as e:
                last_error = f"Timeout after {self.timeout}s: {str(e)}"
                self.logger.warning(f"⏰ Timeout on attempt {attempt}: {last_error}")
                
            except httpx.HTTPStatusError as e:
                last_error = f"HTTP {e.response.status_code}: {e.response.text}"
                self.logger.error(f"❌ HTTP error on attempt {attempt}: {last_error}")
                
                # Don't retry on 4xx errors (client errors)
                if 400 <= e.response.status_code < 500:
                    break
                    
            except httpx.ConnectError as e:
                last_error = f"Connection failed: {str(e)}"
                self.logger.warning(f"🔌 Connection error on attempt {attempt}: {last_error}")
                
            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                self.logger.error(f"💥 Unexpected error on attempt {attempt}: {last_error}")
                
            # Wait before retry (exponential backoff)
            if attempt < self.max_retries:
                wait_time = 2 ** attempt  # 2, 4, 8 seconds
                self.logger.info(f"⏳ Waiting {wait_time}s before retry...")
                await asyncio.sleep(wait_time)
        
        # All attempts failed
        self.logger.error(f"❌ Failed to send report to n8n after {self.max_retries} attempts. Last error: {last_error}")
        
        return {
            "success": False,
            "error": last_error,
            "webhook_url": self.webhook_url,
            "attempts": self.max_retries,
            "timestamp": datetime.now().isoformat()
        }
    
    def _enrich_report_data(self, report_data: Dict[str, Any], session_id: str = None) -> Dict[str, Any]:
        """Enrich report data with additional metadata for n8n processing"""
        
        # Calculate enhanced analytics
        enhanced_analytics = self._calculate_enhanced_analytics(report_data)
        
        enriched = {
            **report_data,  # Original report data
            "n8n_integration": {
                "version": "2.0",
                "source": "llamaindex-resume-matcher",
                "webhook_url": self.webhook_url,
                "session_id": session_id,
                "integration_timestamp": datetime.now().isoformat(),
                "client_info": {
                    "name": "N8nWebhookClient",
                    "timeout": self.timeout,
                    "max_retries": self.max_retries
                }
            },
            "enhanced_analytics": enhanced_analytics
        }
        
        return enriched
    
    def _calculate_enhanced_analytics(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate enhanced analytics from the report data"""
        try:
            summary = report_data.get('enhanced_monitoring_summary', {})
            field_confidence = report_data.get('field_confidence_details', {})
            
            # Confidence analysis
            confidence_scores = []
            field_averages = {}
            for field, scores in field_confidence.items():
                if scores and isinstance(scores, list):
                    avg_score = sum(scores) / len(scores)
                    field_averages[field] = {
                        "average": avg_score,
                        "min": min(scores),
                        "max": max(scores),
                        "count": len(scores)
                    }
                    confidence_scores.extend(scores)
            
            overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
            
            # User feedback analysis
            feedback_data = summary.get('user_feedback_analysis', {})
            total_feedback_requests = feedback_data.get('total_feedback_requests', 0)
            total_fields_modified = feedback_data.get('total_fields_modified', 0)
            total_fields = len(field_confidence)
            
            modification_rate = total_fields_modified / total_fields if total_fields > 0 else 0.0
            feedback_efficiency = 1.0 - modification_rate if modification_rate <= 1.0 else 0.0
            
            # Find highest and lowest confidence fields
            highest_confidence_field = {"field": "unknown", "score": 0.0}
            lowest_confidence_field = {"field": "unknown", "score": 1.0}
            
            for field, stats in field_averages.items():
                if stats["average"] > highest_confidence_field["score"]:
                    highest_confidence_field = {"field": field, "score": stats["average"]}
                if stats["average"] < lowest_confidence_field["score"]:
                    lowest_confidence_field = {"field": field, "score": stats["average"]}
            
            return {
                "confidence_analysis": {
                    "overall_average": overall_confidence,
                    "total_fields_processed": len(field_confidence),
                    "field_averages": field_averages,
                    "highest_confidence_field": highest_confidence_field,
                    "lowest_confidence_field": lowest_confidence_field,
                    "scores_distribution": {
                        "excellent": len([s for s in confidence_scores if s >= 0.8]),
                        "good": len([s for s in confidence_scores if 0.6 <= s < 0.8]),
                        "moderate": len([s for s in confidence_scores if 0.4 <= s < 0.6]),
                        "poor": len([s for s in confidence_scores if s < 0.4])
                    }
                },
                "user_feedback_analysis": {
                    "total_feedback_requests": total_feedback_requests,
                    "total_fields_modified": total_fields_modified,
                    "modification_rate": modification_rate,
                    "feedback_efficiency": feedback_efficiency,
                    "unique_fields_modified": len(set(feedback_data.get('modified_fields', []))),
                    "average_fields_per_feedback": total_fields_modified / total_feedback_requests if total_feedback_requests > 0 else 0,
                    "most_modified_fields": self._get_most_modified_fields(feedback_data.get('modified_fields', []))
                },
                "efficiency_metrics": {
                    "fields_processed_per_second": total_fields / summary.get('total_execution_time', 1),
                    "feedback_efficiency": feedback_efficiency,
                    "modification_rate": modification_rate,
                    "average_step_time": summary.get('total_execution_time', 0) / len(summary.get('step_times', {})) if summary.get('step_times') else 0
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating enhanced analytics: {str(e)}")
            return {
                "error": f"Analytics calculation failed: {str(e)}",
                "confidence_analysis": {},
                "user_feedback_analysis": {},
                "efficiency_metrics": {}
            }
    
    def _get_most_modified_fields(self, modified_fields: List[str]) -> List[tuple]:
        """Get the most frequently modified fields"""
        from collections import Counter
        if not modified_fields:
            return []
        
        field_counts = Counter(modified_fields)
        return field_counts.most_common(5)  # Top 5 most modified fields
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test the webhook connection"""
        test_payload = {
            "test": True,
            "timestamp": datetime.now().isoformat(),
            "source": "N8nWebhookClient",
            "message": "Connection test"
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.webhook_url,
                    json=test_payload,
                    headers={"Content-Type": "application/json"}
                )
                
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "webhook_url": self.webhook_url,
                    "response_time": "< 10s"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "webhook_url": self.webhook_url
            }

# Global N8n webhook client instance
n8n_webhook_client = N8nWebhookClient()

