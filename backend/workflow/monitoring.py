import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, List

from workflow.n8n import n8n_webhook_client
class WorkflowMonitor:
    """Advanced monitoring and analytics for workflow execution"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.step_times: Dict[str, float] = {}
        self.step_start_times: Dict[str, float] = {}
        self.errors: List[Dict[str, Any]] = []
        self.events_processed: List[Dict[str, Any]] = []
        self.success_count = 0
        self.total_count = 0
        
        # Enhanced tracking attributes
        self.runtime_config: Dict[str, Any] = {}
        self.processed_fields: List[str] = []
        self.field_confidence_scores: Dict[str, List[float]] = {}
        self.resume_file: str = ""
        self.application_form: str = ""
        self.user_feedback_requests: int = 0
        self.fields_modified_count: int = 0
        self.modified_fields: List[str] = []
        self.feedback_iterations: List[Dict[str, Any]] = []
        
        self.logger = logging.getLogger(f"{__name__}.WorkflowMonitor")
    
    def set_runtime_config(self, config):
        """Set the runtime configuration for tracking"""
        self.runtime_config = {
            "LLM_MODEL": getattr(config, 'LLM_MODEL', 'Unknown'),
            "EMBEDDING_MODEL": getattr(config, 'EMBEDDING_MODEL', 'Unknown'),
            "CHUNK_SIZE": getattr(config, 'CHUNK_SIZE', 0),
            "CHUNK_OVERLAP": getattr(config, 'CHUNK_OVERLAP', 0),
            "SIMILARITY_TOP_K": getattr(config, 'SIMILARITY_TOP_K', 0),
            "LLM_TEMPERATURE": getattr(config, 'LLM_TEMPERATURE', 0.0),
            "MIN_CONFIDENCE_THRESHOLD": getattr(config, 'MIN_CONFIDENCE_THRESHOLD', 0.0),
            "EMBEDDING_DIMENSION": getattr(config, 'EMBEDDING_DIMENSION', 0),
            # "PINECONE_INDEX_NAME": getattr(config, 'PINECONE_INDEX_NAME', 'Unknown'),
            "QDRANT_INDEX_NAME": getattr(config, 'QDRANT_INDEX_NAME', 'Unknown'),
            "MAX_RETRIES": getattr(config, 'MAX_RETRIES', 0),
            "TIMEOUT": getattr(config, 'TIMEOUT', None)
        }
        self.logger.info("Runtime configuration captured for monitoring")
    
    def set_input_files(self, resume_file: str, application_form: str):
        """Set the input files being processed"""
        self.resume_file = resume_file
        self.application_form = application_form
        self.logger.info(f"Input files tracked: Resume={resume_file}, Form={application_form}")
    
    def set_processed_fields(self, fields: List[str]):
        """Set the list of fields being processed"""
        self.processed_fields = fields.copy()
        self.logger.info(f"Tracking {len(fields)} fields for processing")
    
    def record_field_confidence(self, field: str, confidence_scores: List[float]):
        """Record confidence scores for a specific field"""
        self.field_confidence_scores[field] = confidence_scores.copy()
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        self.logger.debug(f"Recorded confidence for {field}: avg={avg_confidence:.3f}")
    
    def record_user_feedback_request(self, feedback_fields: List[str], feedback_details: List[Dict[str, Any]] = None):
        """Record when user requests field modifications"""
        self.user_feedback_requests += 1
        self.fields_modified_count += len(feedback_fields)
        self.modified_fields.extend(feedback_fields)
        
        # Track this feedback iteration
        feedback_iteration = {
            "iteration_number": self.user_feedback_requests,
            "timestamp": time.time(),
            "fields_modified": feedback_fields.copy(),
            "field_count": len(feedback_fields),
            "feedback_details": feedback_details or []
        }
        self.feedback_iterations.append(feedback_iteration)
        
        self.logger.info(f"User feedback recorded: iteration {self.user_feedback_requests}, {len(feedback_fields)} fields modified")
    
    def start_monitoring(self):
        """Start workflow monitoring"""
        self.start_time = time.time()
        self.logger.info("Enhanced workflow monitoring started")
    
    def stop_monitoring(self):
        """Stop workflow monitoring"""
        self.end_time = time.time()
        self.logger.info("Enhanced workflow monitoring stopped")
    
    def start_step(self, step_name: str):
        """Record the start of a workflow step"""
        self.step_start_times[step_name] = time.time()
        self.logger.debug(f"Step started: {step_name}")
    
    def end_step(self, step_name: str, success: bool = True):
        """Record the end of a workflow step"""
        if step_name in self.step_start_times:
            duration = time.time() - self.step_start_times[step_name]
            self.step_times[step_name] = duration
            
            self.total_count += 1
            if success:
                self.success_count += 1
            
            self.logger.debug(f"Step completed: {step_name} ({duration:.2f}s)")
    
    def log_error(self, step_name: str, error: Exception, context: Dict[str, Any] = None):
        """Log an error that occurred during workflow execution"""
        error_info = {
            'step': step_name,
            'error': str(error),
            'error_type': type(error).__name__,
            'timestamp': time.time(),
            'context': context or {}
        }
        self.errors.append(error_info)
        self.logger.error(f"Error in {step_name}: {str(error)}")
    
    def log_event(self, event_type: str, event_data: Dict[str, Any]):
        """Log a workflow event"""
        event_info = {
            'type': event_type,
            'data': event_data,
            'timestamp': time.time()
        }
        self.events_processed.append(event_info)
        self.logger.debug(f"Event logged: {event_type}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a comprehensive summary of workflow execution"""
        total_time = (self.end_time or time.time()) - (self.start_time or time.time())
        success_rate = self.success_count / self.total_count if self.total_count > 0 else 0
        
        # Calculate confidence metrics from field confidence scores
        confidence_metrics = self._calculate_confidence_summary()
        
        return {
            'total_execution_time': total_time,
            'success_rate': success_rate,
            'total_steps': self.total_count,
            'successful_steps': self.success_count,
            'errors_count': len(self.errors),
            'events_processed': len(self.events_processed),
            'step_times': self.step_times.copy(),
            'runtime_configuration': self.runtime_config.copy(),
            'input_files': {
                'resume_file': self.resume_file,
                'application_form': self.application_form
            },
            'field_processing': {
                'total_fields_count': len(self.processed_fields),
                'processed_fields_list': self.processed_fields.copy()
            },
            'user_feedback_analysis': {
                'total_feedback_requests': self.user_feedback_requests,
                'total_fields_modified': self.fields_modified_count,
                'feedback_iterations': self.feedback_iterations,
                'modified_fields': self.modified_fields.copy()
            },
            'confidence_analysis': confidence_metrics
        }
    
    def _calculate_confidence_summary(self) -> Dict[str, Any]:
        """Calculate confidence summary metrics from field confidence scores"""
        if not self.field_confidence_scores:
            return {
                'overall_average': 0.0,
                'total_fields_processed': 0,
                'field_averages': {},
                'highest_confidence_field': {'field': 'unknown', 'score': 0.0},
                'lowest_confidence_field': {'field': 'unknown', 'score': 0.0},
                'scores_distribution': {
                    'excellent': 0, 'good': 0, 'moderate': 0, 'poor': 0
                }
            }
        
        # Calculate field averages and collect all scores
        field_averages = {}
        all_scores = []
        for field, scores in self.field_confidence_scores.items():
            if scores and isinstance(scores, list) and len(scores) > 0:
                avg_score = sum(scores) / len(scores)
                field_averages[field] = {
                    "average": avg_score,
                    "min": min(scores),
                    "max": max(scores),
                    "count": len(scores)
                }
                all_scores.extend(scores)
        
        # Calculate overall metrics
        overall_average = sum(all_scores) / len(all_scores) if all_scores else 0.0
        # Find highest and lowest confidence fields
        highest_confidence_field = {"field": "unknown", "score": 0.0}
        lowest_confidence_field = {"field": "unknown", "score": 1.0}
        
        for field, stats in field_averages.items():
            if stats["average"] > highest_confidence_field["score"]:
                highest_confidence_field = {"field": field, "score": stats["average"]}
            if stats["average"] < lowest_confidence_field["score"]:
                lowest_confidence_field = {"field": field, "score": stats["average"]}
        
        # Calculate score distribution
        scores_distribution = {
            'excellent': len([s for s in all_scores if s >= 0.8]),
            'good': len([s for s in all_scores if 0.6 <= s < 0.8]),
            'moderate': len([s for s in all_scores if 0.4 <= s < 0.6]),
            'poor': len([s for s in all_scores if s < 0.4])
        }
        
        return {
            'overall_average': overall_average,
            'total_fields_processed': len(self.field_confidence_scores),
            'field_averages': field_averages,
            'highest_confidence_field': highest_confidence_field,
            'lowest_confidence_field': lowest_confidence_field,
            'scores_distribution': scores_distribution
        }

    def export_report(self, filepath: str = None) -> str:
        """Export comprehensive monitoring report to file or send to n8n webhook"""
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"./n8n_workflows/enhanced_workflow_report_{timestamp}.json"

        report_data = {
            'enhanced_monitoring_summary': self.get_summary(),
            'detailed_step_analysis': self.step_times,
            'error_log': self.errors,
            'event_log': self.events_processed,
            'configuration_used': self.runtime_config,
            'field_confidence_details': self.field_confidence_scores,
            'feedback_iterations': self.feedback_iterations,
            'report_metadata': {
                'report_version': '2.0_enhanced',
                'generated_by': 'Enhanced WorkflowMonitor',
                'generation_timestamp': datetime.now().isoformat(),
                'total_data_points': len(self.events_processed) + len(self.errors) + len(self.step_times)
            }
        }
        try:
            # Always save a local backup copy
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)
            self.logger.info(f"📊 Local backup report saved to: {filepath}")
            
            return filepath
        except Exception as e:
            self.logger.error(f"Failed to save local backup report: {str(e)}")
            return ""

    async def send_report_to_n8n(self, session_id: str = None) -> Dict[str, Any]:
        """Send comprehensive monitoring report to n8n webhook"""

        # Get the basic summary
        summary = self.get_summary()
        
        # Create comprehensive report with all tracked data
        report_data = {
            'enhanced_monitoring_summary': summary,
            'detailed_step_analysis': self.step_times,
            'error_log': self.errors,
            'event_log': self.events_processed,
            'configuration_used': self.runtime_config,
            'field_confidence_details': self.field_confidence_scores,
            'feedback_iterations': self.feedback_iterations,
            'report_metadata': {
                'report_version': '2.0_enhanced',
                'generated_by': 'Enhanced WorkflowMonitor',
                'generation_timestamp': datetime.now().isoformat(),
                'total_data_points': len(self.events_processed) + len(self.errors) + len(self.step_times)
            }
        }

        # Add debug information about the data being sent
        self.logger.info(f"📊 Report data summary:")
        self.logger.info(f"  - Fields processed: {len(self.processed_fields)}")
        self.logger.info(f"  - Field confidence entries: {len(self.field_confidence_scores)}")
        self.logger.info(f"  - Step times recorded: {len(self.step_times)}")
        self.logger.info(f"  - Events logged: {len(self.events_processed)}")
        self.logger.info(f"  - Feedback iterations: {len(self.feedback_iterations)}")
        self.logger.info(f"  - Execution time: {summary.get('total_execution_time', 0):.2f}s")
        
        # Log field confidence details for debugging
        if self.field_confidence_scores:
            self.logger.info(f"📈 Field confidence scores:")
            for field, scores in self.field_confidence_scores.items():
                avg_score = sum(scores) / len(scores) if scores else 0.0
                self.logger.info(f"    {field}: {avg_score:.3f} (samples: {len(scores)})")
        else:
            self.logger.warning("⚠️  No field confidence scores recorded!")
            
        # Log processed fields for debugging
        if self.processed_fields:
            self.logger.info(f"📝 Processed fields: {', '.join(self.processed_fields)}")
        else:
            self.logger.warning("⚠️  No processed fields recorded!")

        try:
            self.logger.info("📤 Sending workflow report to n8n webhook...")
            
            # Send to n8n webhook
            webhook_result = await n8n_webhook_client.send_report(report_data, session_id)
            
            if webhook_result.get("success"):
                self.logger.info("✅ Report successfully sent to n8n webhook")
                self.logger.info(f"🔗 n8n Response Status: {webhook_result.get('status_code')}")
                
                # Also save local backup
                local_filepath = self.export_report()
                
                return {
                    "success": True,
                    "webhook_result": webhook_result,
                    "local_backup": local_filepath,
                    "message": "Report sent to n8n webhook successfully",
                    "debug_info": {
                        "fields_tracked": len(self.processed_fields),
                        "confidence_entries": len(self.field_confidence_scores),
                        "step_times": len(self.step_times)
                    }
                }
            else:
                self.logger.error("❌ Failed to send report to n8n webhook")
                self.logger.error(f"Error: {webhook_result.get('error')}")
                
                # Save local backup as fallback
                local_filepath = self.export_report()
                
                return {
                    "success": False,
                    "webhook_result": webhook_result,
                    "local_backup": local_filepath,
                    "message": f"n8n webhook failed: {webhook_result.get('error')}"
                }
                
        except Exception as e:
            self.logger.error(f"💥 Exception while sending report to n8n: {str(e)}")
            
            # Save local backup as fallback
            local_filepath = self.export_report()
            
            return {
                "success": False,
                "error": str(e),
                "local_backup": local_filepath,
                "message": f"Exception occurred: {str(e)}"
            }


class WorkflowPerformanceTracker:
    """Track and analyze workflow performance metrics"""
    
    def __init__(self):
        self.metrics = {
            'step_durations': {},
            'memory_usage': {},
            'api_calls': {},
            'cache_hits': 0,
            'cache_misses': 0
        }
        self.start_time = None
        self.checkpoints = []
    
    def start_tracking(self):
        """Start performance tracking"""
        self.start_time = time.time()
    
    def checkpoint(self, name: str, metadata: Dict[str, Any] = None):
        """Add a performance checkpoint"""
        checkpoint_time = time.time()
        duration_from_start = checkpoint_time - (self.start_time or checkpoint_time)
        
        checkpoint_data = {
            'name': name,
            'timestamp': checkpoint_time,
            'duration_from_start': duration_from_start,
            'metadata': metadata or {}
        }
        
        self.checkpoints.append(checkpoint_data)
    
    def record_api_call(self, service: str, duration: float, success: bool = True):
        """Record API call metrics"""
        if service not in self.metrics['api_calls']:
            self.metrics['api_calls'][service] = {
                'total_calls': 0,
                'successful_calls': 0,
                'total_duration': 0,
                'average_duration': 0
            }
        
        metrics = self.metrics['api_calls'][service]
        metrics['total_calls'] += 1
        metrics['total_duration'] += duration
        
        if success:
            metrics['successful_calls'] += 1
        
        metrics['average_duration'] = metrics['total_duration'] / metrics['total_calls']
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        total_duration = time.time() - (self.start_time or time.time())
        
        # Calculate step durations
        step_durations = {}
        for i, checkpoint in enumerate(self.checkpoints):
            if i == 0:
                step_durations[checkpoint['name']] = checkpoint['duration_from_start']
            else:
                duration = checkpoint['duration_from_start'] - self.checkpoints[i-1]['duration_from_start']
                step_durations[checkpoint['name']] = duration
        
        # Identify bottlenecks
        bottlenecks = []
        if step_durations:
            avg_duration = sum(step_durations.values()) / len(step_durations)
            for step, duration in step_durations.items():
                if duration > avg_duration * 2:
                    bottlenecks.append({'step': step, 'duration': duration, 'severity': 'high'})
                elif duration > avg_duration * 1.5:
                    bottlenecks.append({'step': step, 'duration': duration, 'severity': 'medium'})
        
        return {
            'total_execution_time': total_duration,
            'step_durations': step_durations,
            'bottlenecks': bottlenecks,
            'api_performance': self.metrics['api_calls'],
            'cache_performance': {
                'hit_rate': self.metrics['cache_hits'] / (self.metrics['cache_hits'] + self.metrics['cache_misses'])
                if (self.metrics['cache_hits'] + self.metrics['cache_misses']) > 0 else 0,
                'total_hits': self.metrics['cache_hits'],
                'total_misses': self.metrics['cache_misses']
            }
        }

#</workflow_components.py>

