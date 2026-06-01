import asyncio
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import traceback
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Union, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from workflow_components import (
    EnhancedWorkflowConfig,
    WorkflowMonitor,
    IntelligentResumeMatchingWorkflow,
    InputRequiredEvent,
    HumanResponseEvent,
    LogEvent,
)

from app.models import WorkflowConfigRequest, UserFeedback
from app.session import session_manager, WebSocketLogHandler
from app.core.lifespan import PLAYWRIGHT_AVAILABLE

logger = logging.getLogger(__name__)


async def execute_workflow(session_id: str):
    """Execute the workflow in background."""
    session = session_manager.get_session(session_id)
    if not session:
        return

    try:
        session_logger = logging.getLogger(f"session_{session_id}")
        ws_handler = WebSocketLogHandler(session_id)
        session_logger.addHandler(ws_handler)
        session_logger.setLevel(logging.INFO)

        session_manager.add_log(session_id, "info", "Initializing workflow components...")

        config = create_enhanced_config(session["config"])
        monitor = WorkflowMonitor()
        workflow = IntelligentResumeMatchingWorkflow(
            config=config,
            monitor=monitor,
            timeout=config.TIMEOUT,
        )

        session["workflow"] = workflow
        session["monitor"] = monitor

        session_manager.add_log(session_id, "info", "Starting workflow execution...")
        workflow_handler = workflow.run(
            resume_file=session["resume_file"],
            application_form=session["application_form"],
        )
        session["workflow_handler"] = workflow_handler

        session_manager.add_log(session_id, "info", "Processing workflow events...")

        found_input_event = False
        async for ev in workflow_handler.stream_events():
            logger.info(f"Workflow event received: {type(ev).__name__}")

            if isinstance(ev, LogEvent):
                session_manager.add_log(session_id, "info", ev.log)
            elif isinstance(ev, InputRequiredEvent):
                found_input_event = True
                parsed_fields = parse_workflow_results(ev.result)
                session["results"] = {
                    "session_id": session_id,
                    "status": "awaiting_review",
                    "fields": parsed_fields,
                }
                session_manager.update_session_status(session_id, "awaiting_review")
                session_manager.add_log(session_id, "info", "Waiting for human feedback")

        if not found_input_event:
            session_manager.add_log(session_id, "info", "No human input required, completing workflow...")
            result = await workflow_handler

            if isinstance(result, str):
                fields = parse_workflow_results(result)
            elif isinstance(result, list):
                fields = parse_workflow_results(result)
            else:
                fields = []

            session["results"] = {
                "session_id": session_id,
                "status": "completed",
                "fields": fields,
            }
            session_manager.update_session_status(session_id, "completed")
            session_manager.add_log(session_id, "info", "Workflow completed successfully")

            try:
                await generate_and_upload_pdf(session_id, fields)
            except Exception as pdf_err:
                session_manager.add_log(session_id, "warning", f"PDF generation skipped: {pdf_err}")

            try:
                await workflow.finalize_workflow(session_id)
            except Exception as finalize_err:
                session_manager.add_log(session_id, "warning", f"Finalize workflow warning: {finalize_err}")

    except Exception as e:
        logger.error(f"Workflow execution failed for session {session_id}: {e}")
        session_manager.add_log(session_id, "error", f"Workflow execution failed: {str(e)}")
        session_manager.update_session_status(session_id, "failed")


async def process_feedback(session_id: str, feedbacks: List[UserFeedback]):
    """Process user feedback and continue workflow."""
    session = session_manager.get_session(session_id)
    if not session:
        session_manager.add_log(session_id, "error", "Session not found during feedback processing")
        return

    workflow_handler = session.get("workflow_handler")
    if workflow_handler is None:
        session_manager.add_log(session_id, "error", "No workflow handler found - workflow may not be waiting for feedback")
        return

    try:
        if not feedbacks:
            feedback_text = "approved"
        else:
            feedback_lines = [f"- {f.field}: {f.feedback}" for f in feedbacks]
            feedback_text = "Please update the following fields:\n" + "\n".join(feedback_lines)

        workflow_handler.ctx.send_event(HumanResponseEvent(response=feedback_text))
        session_manager.add_log(session_id, "info", "Feedback sent to workflow")

        found_input_event = False
        async for ev in workflow_handler.stream_events():
            if isinstance(ev, LogEvent):
                session_manager.add_log(session_id, "info", ev.log)
            elif isinstance(ev, InputRequiredEvent):
                found_input_event = True
                parsed_fields = parse_workflow_results(ev.result)
                session["results"] = {
                    "session_id": session_id,
                    "status": "awaiting_review",
                    "fields": parsed_fields,
                }
                session_manager.update_session_status(session_id, "awaiting_review")
                break

        if not found_input_event:
            final_result = await workflow_handler
            fields = parse_workflow_results(final_result)
            session["results"] = {
                "session_id": session_id,
                "status": "completed",
                "fields": fields,
            }
            session_manager.update_session_status(session_id, "completed")
            session_manager.add_log(session_id, "info", "Feedback processing completed successfully")

            try:
                await generate_and_upload_pdf(session_id, fields)
            except Exception as pdf_err:
                session_manager.add_log(session_id, "warning", f"PDF generation skipped: {pdf_err}")

            if "workflow" in session and session["workflow"]:
                try:
                    await session["workflow"].finalize_workflow(session_id)
                except Exception as finalize_err:
                    session_manager.add_log(session_id, "warning", f"Finalize workflow warning: {finalize_err}")

    except Exception as e:
        logger.error(f"Feedback processing failed: {e}")
        session_manager.add_log(session_id, "error", f"Feedback processing failed: {str(e)}")
        session_manager.update_session_status(session_id, "failed")


def create_enhanced_config(config_request: WorkflowConfigRequest) -> EnhancedWorkflowConfig:
    """Create enhanced configuration from user request with dynamic parameters"""
    # Create config with all user-specified parameters
    config = EnhancedWorkflowConfig(
        LLM_MODEL=config_request.llm_model,
        EMBEDDING_MODEL=config_request.embedding_model,
        QDRANT_INDEX_NAME=config_request.qdrant_index_name,
        CHUNK_SIZE=config_request.chunk_size,
        CHUNK_OVERLAP=config_request.chunk_overlap,
        SIMILARITY_TOP_K=config_request.similarity_top_k,
        MIN_CONFIDENCE_THRESHOLD=config_request.min_confidence_threshold,
        LLM_TEMPERATURE=config_request.llm_temperature
    )
    
    logger.info(f"📋 Configuration created with LLM: {config.LLM_MODEL}, Embedding: {config.EMBEDDING_MODEL}")
    logger.info(f"📋 Params - Chunk Size: {config.CHUNK_SIZE}, Top K: {config.SIMILARITY_TOP_K}, Temp: {config.LLM_TEMPERATURE}")
    
    return config

def parse_workflow_results(raw_result: Union[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Parse workflow results into structured format"""
    fields = []
    
    # If raw_result is already a list of structured dicts (new format), return as is
    if isinstance(raw_result, list) and all(isinstance(item, dict) for item in raw_result):
        logger.info(f"Received structured format with {len(raw_result)} fields")
        # Convert the structured format to the expected frontend format
        for item in raw_result:
            # Determine confidence level from indicator
            confidence_indicator = item.get('confidence_indicator', '⚠️')
            if confidence_indicator == ' ✅':
                confidence = 'high'
            elif confidence_indicator == ' ⚠️':
                confidence = 'medium'
            elif confidence_indicator == ' ❌':
                confidence = 'low'
            else:
                confidence = 'medium'
            
            fields.append({
                'name': item.get('field', ''),
                'response': item.get('response_text', ''),
                'confidence': confidence,
                'confidence_score': float(item.get('confidence_score', '0.65')),
                'generated_query': item.get('generated_query', ''),
                'confidence_indicator': confidence_indicator.strip()
            })
        return fields
    
    # If raw_result is empty or None, return empty list
    if not raw_result or not isinstance(raw_result, str):
        logger.warning("Empty or invalid raw_result received")
        return fields
    
    # string parsing for backward compatibility
    lines = raw_result.split('\n')
    current_field = None
    current_response = []
    current_confidence = 'medium'
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Match field headers with various patterns
        # Pattern 1: **1. Field Name**✅ (confidence: 0.85)
        field_match = re.match(r'^\*\*\d+\.\s*(.+?)\*\*([✅⚠️❌❓]?)\s*(?:\(confidence:\s*([\d.]+)\))?', line)
        
        if field_match:
            # Save previous field
            if current_field:
                fields.append({
                    'name': current_field,
                    'response': '\n'.join(current_response).strip(),
                    'confidence': current_confidence,
                    'confidence_score': get_confidence_score(current_confidence),
                    'generated_query': '',
                    'confidence_indicator': '⚠️'  # Default 
                })
            
            # Start new field
            current_field = field_match.group(1).strip()
            current_response = []
            
            # Determine confidence from icon or score
            icon = field_match.group(2) if field_match.group(2) else ''
            score = field_match.group(3)
            
            if score:
                score_val = float(score)
                current_confidence = 'high' if score_val >= 0.8 else 'medium' if score_val >= 0.6 else 'low'
            elif icon == '✅':
                current_confidence = 'high'
            elif icon == '⚠️':
                current_confidence = 'medium'
            elif icon == '❌':
                current_confidence = 'low'
            else:
                current_confidence = 'medium'
                
        # Pattern 2: Simple **Field Name** without numbering
        elif line.startswith('**') and line.endswith('**') and current_field is None:
            current_field = line.strip('*').strip()
            current_response = []
            current_confidence = 'medium'
            
        # Add content to current response if we have a field
        elif current_field and not line.startswith('-') and not line.startswith('*'):
            current_response.append(line)
    
    # Save last field
    if current_field:
        fields.append({
            'name': current_field,
            'response': '\n'.join(current_response).strip(),
            'confidence': current_confidence,
            'confidence_score': get_confidence_score(current_confidence),
            'generated_query': '', 
            'confidence_indicator': '⚠️'  
        })
    
    logger.info(f"Parsed {len(fields)} fields from workflow results")

    print("Processed Fields:\n", fields)

    return fields

def get_confidence_score(confidence: str) -> float:
    """Convert confidence string to numeric score"""
    confidence_map = {
        'high': 0.85,
        'medium': 0.65,
        'low': 0.45
    }
    return confidence_map.get(confidence, 0.65)

# ================================================================================
# PDF GENERATION AND GOOGLE DRIVE UPLOAD FUNCTIONS
# ================================================================================

# Google Drive configuration
GOOGLE_DRIVE_SCOPES = ['https://www.googleapis.com/auth/drive.file']
GOOGLE_DRIVE_FOLDER_ID = os.getenv('GOOGLE_DRIVE_FOLDER_ID', None)  # Optional: Set in .env

GOOGLE_DRIVE_FOLDER_ID="1kBWvKYhsW54sQTaUKAY8AWyxPOJYapKL"
# HTML template for PDF
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Resume Matching Report</title>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Work+Sans:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        :root {
            --primary: #1a1a2e;
            --accent: #e94560;
            --secondary: #0f3460;
            --light: #f8f9fa;
            --text: #2d3436;
            --border: #dfe6e9;
        }

        body {
            font-family: 'Work Sans', sans-serif;
            color: var(--text);
            line-height: 1.6;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 40px 20px;
        }

        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }

        .header {
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            color: white;
            padding: 60px 50px;
            position: relative;
            overflow: hidden;
        }

        .header::before {
            content: '';
            position: absolute;
            top: -50%;
            right: -10%;
            width: 400px;
            height: 400px;
            background: radial-gradient(circle, rgba(233, 69, 96, 0.3) 0%, transparent 70%);
            border-radius: 50%;
        }

        .header::after {
            content: '';
            position: absolute;
            bottom: -30%;
            left: -5%;
            width: 300px;
            height: 300px;
            background: radial-gradient(circle, rgba(255, 255, 255, 0.1) 0%, transparent 70%);
            border-radius: 50%;
        }

        .header-content {
            position: relative;
            z-index: 2;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }

        h1 {
            font-family: 'Playfair Display', serif;
            font-size: 48px;
            font-weight: 900;
            margin-bottom: 10px;
            letter-spacing: -1px;
        }

        .subtitle {
            font-size: 16px;
            font-weight: 300;
            opacity: 0.9;
            letter-spacing: 2px;
            text-transform: uppercase;
        }

        .content {
            padding: 50px;
        }

        .candidate-name {
            text-align: center;
            margin-bottom: 50px;
            padding-bottom: 30px;
            border-bottom: 3px solid var(--accent);
        }

        .candidate-name h2 {
            font-family: 'Playfair Display', serif;
            font-size: 36px;
            color: var(--primary);
            margin-bottom: 8px;
        }

        .candidate-name .role {
            font-size: 18px;
            color: var(--accent);
            font-weight: 600;
        }

        .section {
            margin-bottom: 40px;
        }

        .section-title {
            font-family: 'Playfair Display', serif;
            font-size: 24px;
            color: var(--primary);
            margin-bottom: 20px;
            padding-left: 20px;
            border-left: 4px solid var(--accent);
        }

        .info-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 25px;
            margin-bottom: 30px;
        }

        .info-item {
            background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%);
            padding: 20px;
            border-radius: 8px;
            border-left: 3px solid var(--accent);
        }

        .info-label {
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--secondary);
            font-weight: 600;
            margin-bottom: 5px;
        }

        .info-value {
            font-size: 16px;
            color: var(--text);
            font-weight: 400;
        }

        .full-width {
            grid-column: 1 / -1;
        }

        .highlight-box {
            background: linear-gradient(135deg, var(--secondary) 0%, var(--primary) 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            margin: 30px 0;
        }

        .highlight-box .info-label {
            color: rgba(255, 255, 255, 0.8);
        }

        .highlight-box .info-value {
            color: white;
            font-size: 18px;
            line-height: 1.8;
        }

        .skills-list {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 10px;
        }

        .skill-tag {
            background: var(--accent);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 600;
        }

        .experience-badge {
            display: inline-block;
            background: var(--accent);
            color: white;
            padding: 10px 20px;
            border-radius: 25px;
            font-weight: 600;
            font-size: 14px;
            margin-top: 10px;
        }

        .footer {
            background: var(--light);
            padding: 30px 50px;
            text-align: center;
            font-size: 12px;
            color: var(--secondary);
            border-top: 1px solid var(--border);
        }

        @media print {
            body {
                padding: 0;
                background: white;
            }
            .container {
                box-shadow: none;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-content">
                <h1>Resume Match</h1>
                <div class="subtitle">Candidate Analysis Report</div>
            </div>
        </div>

        <div class="content">
            <div class="candidate-name">
                <h2>{{FIRST_NAME}} {{LAST_NAME}}</h2>
                <div class="role">{{CURRENT_JOB_TITLE}}</div>
            </div>

            <div class="section">
                <h3 class="section-title">Personal Information</h3>
                <div class="info-grid">
                    <div class="info-item">
                        <div class="info-label">First Name</div>
                        <div class="info-value">{{FIRST_NAME}}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Last Name</div>
                        <div class="info-value">{{LAST_NAME}}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Email</div>
                        <div class="info-value">{{EMAIL}}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Phone</div>
                        <div class="info-value">{{PHONE}}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">LinkedIn</div>
                        <div class="info-value">{{LINKEDIN}}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Graduation Date</div>
                        <div class="info-value">{{GRADUATION_DATE}}</div>
                    </div>
                </div>
            </div>

            <div class="section">
                <h3 class="section-title">Education & Experience</h3>
                <div class="info-grid">
                    <div class="info-item">
                        <div class="info-label">Degree</div>
                        <div class="info-value">{{DEGREE}}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Current Employer</div>
                        <div class="info-value">{{CURRENT_EMPLOYER}}</div>
                    </div>
                    <div class="info-item full-width">
                        <div class="info-label">5+ Years React Experience</div>
                        <div class="info-value">
                            {{REACT_EXPERIENCE}}
                            <span class="experience-badge">{{REACT_EXPERIENCE_BADGE}}</span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="section">
                <h3 class="section-title">Technical Skills</h3>
                <div class="skills-list">
                    {{TECHNICAL_SKILLS_TAGS}}
                </div>
            </div>

            <div class="section">
                <h3 class="section-title">Project Portfolio</h3>
                <div class="info-item full-width">
                    <div class="info-value">{{PROJECT_PORTFOLIO}}</div>
                </div>
            </div>

            <div class="highlight-box">
                <div class="info-label">Why I'm a Good Fit</div>
                <div class="info-value">{{GOOD_FIT_DESCRIPTION}}</div>
            </div>
        </div>

        <div class="footer">
            Generated on {{GENERATION_DATE}} | Confidential Resume Matching Report
        </div>
    </div>
</body>
</html>"""

def transform_resume_data(input_data: List[Dict[str, Any]]) -> Dict[str, str]:
    """Transform resume extraction data from list format to dictionary format."""
    lookup = {item['name']: item['response'] for item in input_data}
    
    def get_value(key: str, default: str = "Not Available") -> str:
        response = lookup.get(key, default)
        if "not available" in response.lower() or "this information is not available" in response.lower():
            return default
        return response
    
    output_data = {
        'FIRST_NAME': get_value('First Name', ''),
        'LAST_NAME': get_value('Last Name', ''),
        'CURRENT_JOB_TITLE': get_value('Current Job Title', ''),
        'EMAIL': get_value('Email', ''),
        'PHONE': get_value('Phone', ''),
        'LINKEDIN': get_value('Linkedin', ''),
        'GRADUATION_DATE': get_value('Graduation Date', ''),
        'DEGREE': get_value('Degree', ''),
        'CURRENT_EMPLOYER': get_value('Current Employer', ''),
        'GENERATION_DATE': datetime.now().strftime('%B %d, %Y')
    }
    
    react_exp = get_value('Do you have 5 years of experience in React?', '')
    output_data['REACT_EXPERIENCE'] = react_exp
    output_data['REACT_EXPERIENCE_BADGE'] = 'Qualified ✓' if react_exp and react_exp != "Not Available" else 'Not Qualified ✗'
    
    tech_skills = get_value('Technical Skills', '')
    if tech_skills and tech_skills != "Not Available":
        skills = [s.strip() for s in tech_skills.split(',')]
        skill_tags = ''.join([f'<span class="skill-tag">{skill}</span>' for skill in skills])
        output_data['TECHNICAL_SKILLS_TAGS'] = skill_tags
    else:
        output_data['TECHNICAL_SKILLS_TAGS'] = ''
    
    output_data['PROJECT_PORTFOLIO'] = get_value('Project Portfolio', '')
    output_data['GOOD_FIT_DESCRIPTION'] = get_value("Describe why you're a good fit for this position", '')
    
    return output_data

async def generate_pdf_from_data(data: List[Dict[str, Any]], output_path: str) -> str:
    """Generate a PDF from resume data.

    Strategy:
      1. Try Playwright (best quality, uses real Chromium).
      2. Fall back to xhtml2pdf if Playwright is unavailable.
    """

    transformed_data = transform_resume_data(data)
    processed_html = HTML_TEMPLATE

    for key, value in transformed_data.items():
        placeholder = f'{{{{{key}}}}}'
        processed_html = processed_html.replace(placeholder, str(value))

    # ---- Attempt 1: Playwright (high-fidelity) --------------------------
    if PLAYWRIGHT_AVAILABLE:
        try:
            return await _generate_pdf_playwright(processed_html, output_path)
        except Exception as pw_err:
            logger.warning(f"Playwright PDF failed, falling back to xhtml2pdf: {pw_err}")

    # ---- Attempt 2: xhtml2pdf (pure-Python fallback) --------------------


async def _generate_pdf_playwright(html: str, output_path: str) -> str:
    """Generate PDF via Playwright Chromium subprocess."""
    import subprocess
    import tempfile

    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
        html_path = f.name
        f.write(html)

    try:
        script = f'''
import sys
from playwright.sync_api import sync_playwright

html_path = r"{html_path}"
output_path = r"{output_path}"

with open(html_path, "r", encoding="utf-8") as f:
    html_content = f.read()

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.set_content(html_content, wait_until="networkidle")
    page.pdf(
        path=output_path,
        format="A4",
        print_background=True,
        margin={{"top": "0mm", "right": "0mm", "bottom": "0mm", "left": "0mm"}}
    )
    browser.close()
'''

        def _run():
            result = subprocess.run(
                [sys.executable, "-c", script],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Playwright subprocess failed: {result.stderr}")
            return result

        await asyncio.to_thread(_run)
    finally:
        try:
            os.unlink(html_path)
        except Exception:
            pass

    logger.info(f"✓ PDF generated (Playwright): {output_path} ({os.path.getsize(output_path) / 1024:.2f} KB)")
    return output_path


async def _generate_pdf_xhtml2pdf(html: str, output_path: str) -> str:
    """Fallback: generate PDF using xhtml2pdf (pure Python, no browser needed)."""
    def _run():
        try:
            from xhtml2pdf import pisa
        except ImportError:
            raise RuntimeError(
                "Neither Playwright nor xhtml2pdf is available. "
                "Install one of them:\n"
                "  playwright install chromium   (recommended)\n"
                "  pip install xhtml2pdf          (fallback)"
            )
        with open(output_path, "wb") as out_f:
            status = pisa.CreatePDF(html, dest=out_f)
            if status.err:
                raise RuntimeError(f"xhtml2pdf conversion had {status.err} errors")

    await asyncio.to_thread(_run)
    logger.info(f"✓ PDF generated (xhtml2pdf fallback): {output_path} ({os.path.getsize(output_path) / 1024:.2f} KB)")
    return output_path

def authenticate_google_drive():
    """Authenticate and return Google Drive service with improved error handling."""
    creds = None
    token_path = 'token.json'
    credentials_path = 'credentials.json'
    
    # Try to load existing token
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, GOOGLE_DRIVE_SCOPES)
        except Exception as e:
            logger.warning(f"Failed to load token.json: {e}. Will re-authenticate.")
            creds = None
    
    # Check if credentials are valid
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                # Try to refresh the token
                logger.info("Refreshing expired Google Drive credentials...")
                creds.refresh(Request())
                logger.info("✓ Credentials refreshed successfully")
            except Exception as refresh_error:
                # If refresh fails, delete token and re-authenticate
                logger.warning(f"Token refresh failed: {refresh_error}")
                logger.info("Deleting invalid token.json and re-authenticating...")
                
                try:
                    os.remove(token_path)
                except Exception:
                    pass
                
                creds = None  # Force re-authentication
        
        # If still no valid credentials, start OAuth flow
        if not creds or not creds.valid:
            if not os.path.exists(credentials_path):
                logger.warning("credentials.json not found. Skipping Google Drive upload.")
                return None
            
            try:
                logger.info("Starting OAuth flow for Google Drive authentication...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path, 
                    GOOGLE_DRIVE_SCOPES
                )
                creds = flow.run_local_server(port=0)
                logger.info("✓ Authentication successful")
            except Exception as auth_error:
                logger.error(f"OAuth authentication failed: {auth_error}")
                return None
        
        # Save the credentials for the next run
        try:
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
            logger.info(f"✓ Credentials saved to {token_path}")
        except Exception as save_error:
            logger.warning(f"Failed to save token: {save_error}")
    
    try:
        service = build('drive', 'v3', credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Failed to build Google Drive service: {e}")
        return None
    
def _upload_to_drive_sync(file_path: str, folder_id: str = None) -> Optional[Dict[str, str]]:
    """Synchronous Google Drive upload (runs in thread pool)."""
    try:
        service = authenticate_google_drive()
        if not service:
            logger.warning("Google Drive authentication failed. Skipping upload.")
            return None
        
        file_name = os.path.basename(file_path)
        file_metadata = {'name': file_name, 'mimeType': 'application/pdf'}
        
        if folder_id:
            file_metadata['parents'] = [folder_id]
        
        media = MediaFileUpload(file_path, mimetype='application/pdf', resumable=True)
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink'
        ).execute()
        
        logger.info(f"✓ File uploaded to Google Drive: {file.get('name')}")
        logger.info(f"  File ID: {file.get('id')}")
        logger.info(f"  View Link: {file.get('webViewLink')}")
        
        return {
            'file_id': file.get('id'),
            'file_name': file.get('name'),
            'web_view_link': file.get('webViewLink')
        }
    except HttpError as error:
        logger.error(f"✗ Google Drive upload failed: {error}")
        return None
    except FileNotFoundError:
        logger.error(f"✗ File not found: {file_path}")
        return None
    except Exception as e:
        logger.error(f"✗ Unexpected error during Google Drive upload: {e}")
        return None

async def upload_pdf_to_google_drive(file_path: str, folder_id: str = None) -> Optional[Dict[str, str]]:
    """Upload PDF to Google Drive (async wrapper)."""
    # Run blocking Google Drive API calls in thread pool
    return await asyncio.to_thread(_upload_to_drive_sync, file_path, folder_id)

async def generate_and_upload_pdf(session_id: str, fields_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate PDF from fields data and upload to Google Drive."""
    result = {
        'pdf_generated': False,
        'pdf_path': None,
        'uploaded_to_drive': False,
        'drive_info': None,
        'error': None
    }
    
    try:
        # Generate PDF filename with sanitization        
        # Sanitize names for filename - remove invalid characters and limit lengt        
        # first_name_clean = sanitize_filename_part(first_name, max_length=30)
        # last_name_clean = sanitize_filename_part(last_name, max_length=30)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_filename = f"resume_report_{timestamp}.pdf"
        pdf_path = Path(f"uploads/{session_id}") / pdf_filename
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate PDF
        session_manager.add_log(session_id, "info", f"📄 Generating PDF: {pdf_filename}")
        await generate_pdf_from_data(fields_data, str(pdf_path))
        result['pdf_generated'] = True
        result['pdf_path'] = str(pdf_path)
        session_manager.add_log(session_id, "info", f"✅ PDF generated successfully: {pdf_path.name}")
        
        # Upload to Google Drive
        session_manager.add_log(session_id, "info", "☁️  Uploading PDF to Google Drive...")
        drive_info = await upload_pdf_to_google_drive(str(pdf_path), GOOGLE_DRIVE_FOLDER_ID)
        
        if drive_info:
            result['uploaded_to_drive'] = True
            result['drive_info'] = drive_info
            session_manager.add_log(
                session_id, "info", 
                f"✅ PDF uploaded to Google Drive: {drive_info['web_view_link']}"
            )
        else:
            session_manager.add_log(
                session_id, "warning", 
                "⚠️  Google Drive upload skipped (credentials not configured)"
            )
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        error_message = str(e).strip() or e.__class__.__name__
        result['error'] = error_message
        detailed_message = f"❌ PDF generation/upload failed: {error_message}"
        session_manager.add_log(session_id, "error", detailed_message)
        session_manager.add_log(session_id, "debug", error_details)
        logger.error(f"PDF generation/upload failed for session {session_id}:")
        logger.error(f"Error: {error_message}")
        logger.error(f"Traceback:\n{error_details}")
    
    return result



