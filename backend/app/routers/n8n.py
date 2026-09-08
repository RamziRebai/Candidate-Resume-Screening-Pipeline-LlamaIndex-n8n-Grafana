import logging
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter()
@router.get("/api/n8n/test-connection")
async def test_n8n_connection():
    """Test connection to n8n webhook endpoint"""
    try:
        from workflow_components import n8n_webhook_client
        
        logger.info("Testing n8n webhook connection...")
        result = await n8n_webhook_client.test_connection()
        
        return {
            "status": "success" if result.get("success") else "failed",
            "connection_test": result,
            "webhook_url": n8n_webhook_client.webhook_url,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"n8n connection test failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )

@router.post("/api/n8n/send-test-report")
async def send_test_report():
    """Send a test report to n8n webhook for debugging"""
    try:
        from workflow_components import n8n_webhook_client
        
        # Create a sample test report
        test_report = {
            'enhanced_monitoring_summary': {
                'total_execution_time': 45.2,
                'success_rate': 0.95,
                'total_steps': 10,
                'successful_steps': 9,
                'errors_count': 1,
                'step_times': {
                    'initialization_step': 2.1,
                    'form_parsing_step': 8.5,
                    'question_generation_step': 5.3,
                    'query_processing_step': 25.8,
                    'response_aggregation_step': 2.1,
                    'finalization_step': 1.4
                },
                'runtime_configuration': {
                    'LLM_MODEL': 'gpt-5.4-mini',
                    'EMBEDDING_MODEL': 'text-embedding-3-small',
                    'CHUNK_SIZE': 200,
                    'SIMILARITY_TOP_K': 7,
                    'LLM_TEMPERATURE': 0.0
                },
                'field_processing': {
                    'total_fields_count': 5,
                    'processed_fields_list': ['Name', 'Email', 'Experience', 'Skills', 'Education']
                },
                'user_feedback_analysis': {
                    'total_feedback_requests': 1,
                    'total_fields_modified': 2,
                    'feedback_iterations': [
                        {
                            'iteration_number': 1,
                            'fields_modified': ['Experience', 'Skills'],
                            'field_count': 2
                        }
                    ]
                }
            },
            'field_confidence_details': {
                'Name': [0.95, 0.92, 0.94],
                'Email': [0.98, 0.96, 0.97],
                'Experience': [0.75, 0.73, 0.78],
                'Skills': [0.82, 0.85, 0.80],
                'Education': [0.68, 0.72, 0.70]
            },
            'report_metadata': {
                'report_version': '2.0_enhanced_test',
                'generated_by': 'Test API Endpoint',
                'generation_timestamp': datetime.now().isoformat(),
                'is_test_report': True
            }
        }
        
        logger.info("Sending test report to n8n webhook...")
        result = await n8n_webhook_client.send_report(test_report, "test-session-123")
        
        return {
            "status": "success" if result.get("success") else "failed",
            "webhook_result": result,
            "test_report_sent": True,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to send test report: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )

@router.get("/api/n8n/webhook-info")
async def get_webhook_info():
    """Get information about the configured n8n webhook"""
    try:
        from workflow_components import n8n_webhook_client
        
        return {
            "webhook_url": n8n_webhook_client.webhook_url,
            "timeout": n8n_webhook_client.timeout,
            "max_retries": n8n_webhook_client.max_retries,
            "integration_status": "configured",
            "expected_n8n_workflow": "rag-report-processor",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )

# ================================================================================
# MAIN EXECUTION
# ================================================================================

