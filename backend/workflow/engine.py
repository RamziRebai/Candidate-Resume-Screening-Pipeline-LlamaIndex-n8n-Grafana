#<engine.py>
import os
import logging
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
import asyncio

from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core import VectorStoreIndex, StorageContext, Document
from llama_index.core.prompts import PromptTemplate
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.vector_stores import MetadataFilters, MetadataFilter, FilterOperator
from llama_index.core.ingestion import IngestionPipeline
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core.query_engine import CustomQueryEngine
from llama_index.core.retrievers import BaseRetriever
from llama_cloud import AsyncLlamaCloud
from llama_index.core.workflow import (
    Workflow, step, StartEvent, StopEvent, Context,
    InputRequiredEvent, HumanResponseEvent
)
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding
from qdrant_client import AsyncQdrantClient
from qdrant_client import models as qdrant_models

from workflow.n8n import n8n_webhook_client
from workflow.config import EnhancedWorkflowConfig
from workflow.monitoring import WorkflowMonitor, WorkflowPerformanceTracker
from workflow.models_events import (
    ParseFormEvent,
    GenerateQuestionsEvent,
    QueryEvent,
    ResponseEvent,
    FeedbackEvent,
    FeedbackCollection,
    FormFields,
)
from workflow.models_events import LogEvent
from workflow.utils import group_resume_sections, ResumeTextProcessor
import workflow.utils as workflow_utils

logger = logging.getLogger(__name__)
class IntelligentResumeMatchingWorkflow(Workflow):
    """
    🚀 Advanced Resume-Application Form Matching Workflow
    """
    
    def __init__(self, config=None, monitor=None, **kwargs):
        super().__init__(**kwargs)
        
        # Use enhanced configuration
        self.config = config or EnhancedWorkflowConfig()
        
        # Initialize enhanced monitoring
        self.monitor = monitor or WorkflowMonitor()
        self.perf_tracker = WorkflowPerformanceTracker()
        
        # LOGGING POINT 1: Set runtime configuration in monitor
        self.monitor.set_runtime_config(self.config)
        
        # Start monitoring
        self.monitor.start_monitoring()
        self.perf_tracker.start_tracking()
        
        self.setup_components()

    async def _inspect_qdrant_payload(self):
        """Diagnostic: print the actual payload structure of stored points."""
        try:
            result = await self.qd.scroll(
                collection_name=self.config.QDRANT_INDEX_NAME,
                limit=1,
                with_payload=True,
                with_vectors=False,
            )
            points = result[0]
            if points:
                logger.info(f"🔍 DIAGNOSTIC — Qdrant payload keys: {list(points[0].payload.keys())}")
                logger.info(f"🔍 DIAGNOSTIC — Full payload sample: {points[0].payload}")
            else:
                logger.warning("🔍 DIAGNOSTIC — No points found in collection yet")
        except Exception as e:
            logger.error(f"🔍 DIAGNOSTIC — scroll failed: {e}")
    
    def setup_components(self):
        """Initialize LLM, embeddings, and other components with dynamic provider selection"""
        step_name = "setup_components"
        self.monitor.start_step(step_name)
        
        try:
            # Set environment variables
            os.environ["LLAMA_PARSE_API_KEY"] = self.config.LLAMA_PARSE_API_KEY
            # os.environ["PINECONE_API_KEY"] = self.config.PINECONE_API_KEY
            os.environ["QDRANT_API_KEY"] = self.config.QDRANT_API_KEY
            os.environ["QDRANT_CLUSTER_ENDPOINT"] = self.config.QDRANT_CLUSTER_ENDPOINT

            # Dynamically select LLM provider based on model name
            llm_model = self.config.LLM_MODEL.lower()
            embedding_model = self.config.EMBEDDING_MODEL.lower()
            
            logger.info(f"🔧 Initializing LLM: {self.config.LLM_MODEL} with temperature: {self.config.LLM_TEMPERATURE}")
            logger.info(f"🔧 Initializing Embedding: {self.config.EMBEDDING_MODEL}")
            
            # Initialize LLM based on model name
            if 'gemini' in llm_model or 'palm' in llm_model:
                # Google models
                os.environ["GOOGLE_API_KEY"] = self.config.GOOGLE_API_KEY
                self.llm = GoogleGenAI(
                    model=self.config.LLM_MODEL,
                    temperature=self.config.LLM_TEMPERATURE
                )
                logger.info("✅ Using Google Gemini LLM")
            elif 'gpt' in llm_model:
                    # Standard OpenAI
                self.llm = OpenAI(
                    model=self.config.LLM_MODEL,
                    temperature=self.config.LLM_TEMPERATURE
                )
                logger.info("✅ Using OpenAI LLM")
            # else:
            #     # OpenAI models (including GPT-4, GPT-3.5, o1, o3, o4 series)
            #     if hasattr(self.config, 'api_key') and hasattr(self.config, 'azure_endpoint'):
            #         # Azure OpenAI
            #         os.environ["api_key"] = self.config.api_key
            #         os.environ["azure_endpoint"] = self.config.azure_endpoint
                    
            #         # o1, o3, and o4 reasoning models don't support temperature parameter
            #         is_reasoning_model = any(x in llm_model for x in ['o1', 'o3', 'o4'])
                    
            #         if is_reasoning_model:
            #             self.llm = AzureOpenAI(
            #                 engine="model-router",
            #                 api_version="2024-12-01-preview",
            #                 model=self.config.LLM_MODEL,
            #                 api_key=self.config.api_key,
            #                 azure_endpoint=self.config.azure_endpoint
            #             )
            #         else:
            #             print(f"LLM Model:\n{self.config.LLM_MODEL} {self.config.azure_endpoint} {self.config.api_key}")
            #             self.llm = AzureOpenAI(
            #                 engine="model-router",
            #                 api_version="2025-01-01-preview",
            #                 model=self.config.LLM_MODEL,
            #                 temperature=self.config.LLM_TEMPERATURE,
            #                 api_key=self.config.api_key,
            #                 azure_endpoint=self.config.azure_endpoint
            #             )
            #         logger.info("✅ Using Azure OpenAI LLM")
            
            # Initialize Embedding model based on model name
            if 'gemini-embedding-001' in embedding_model:
                # Google embeddings
                os.environ["GOOGLE_API_KEY"] = self.config.GOOGLE_API_KEY
                self.embed_model = GoogleGenAIEmbedding(
                    model=self.config.EMBEDDING_MODEL
                )
                logger.info("✅ Using Google GenAI Embedding")
            elif 'text-embedding-3' in embedding_model or 'text-embedding-ada' in embedding_model:
                # OpenAI embeddings
                    # Standard OpenAI Embeddings
                self.embed_model = OpenAIEmbedding(
                    model=self.config.EMBEDDING_MODEL
                )
                logger.info("✅ Using OpenAI Embedding")
            # else:
            #     # Default to Azure OpenAI embeddings
            #     self.embed_model = AzureOpenAIEmbedding(
            #         api_version="2025-01-01-preview",
            #         model=self.config.EMBEDDING_MODEL,
            #         api_key=self.config.embed_api_key,
            #         azure_endpoint=self.config.embed_azure_endpoint
            #     )
            #     logger.info(f"✅ Using Azure OpenAI Embedding for model: {self.config.EMBEDDING_MODEL}")

            # self.pc = Pinecone()
            self.qd= AsyncQdrantClient(
                api_key=self.config.QDRANT_API_KEY,
                url=self.config.QDRANT_CLUSTER_ENDPOINT,
                timeout=30,  # was defaulting to a few seconds
            )
            
            self.monitor.end_step(step_name, success=True)
            logger.info(f"🔧 Workflow components initialized successfully with {self.config.LLM_MODEL}")
            
        except Exception as e:
            self.monitor.log_error(step_name, e)
            self.monitor.end_step(step_name, success=False)
            raise

    @step
    async def initialization_step(self, ev: StartEvent, ctx: Context) -> ParseFormEvent:
        """🏁 STEP 1: Initialize the workflow and validate inputs"""
        step_name = "initialization_step"
        self.monitor.start_step(step_name)
        self.perf_tracker.checkpoint("initialization_started")
        
        try:
            logger.info("🚀 Starting resume-application matching workflow...")
            ctx.write_event_to_stream(LogEvent(log="Starting resume-application matching workflow..."))
            # Input validation
            if not ev.resume_file:
                raise ValueError("❌ Resume file is required but not provided")
            if not ev.application_form:
                raise ValueError("❌ Application form is required but not provided")


            # LOGGING POINT 2: Track input files in monitor
            self.monitor.set_input_files(ev.resume_file, ev.application_form)
            
            logger.info(f"📄 Processing resume: {ev.resume_file}")
            logger.info(f"📋 Processing application form: {ev.application_form}")
            
            self.perf_tracker.checkpoint("validation_complete")
            
            # Setup vector store
            api_start = time.time()
            await self._setup_vector_store()
            self.perf_tracker.record_api_call("qdrant_setup", time.time() - api_start)
            
            # Process and index resume
            process_start = time.time()
            ctx.write_event_to_stream(LogEvent(log=f"Processing Resume File and Indexing in Qdrant"))
            await self._process_and_index_resume(ev.resume_file, ctx)
            self.perf_tracker.record_api_call("resume_processing", time.time() - process_start)
            
            self.perf_tracker.checkpoint("initialization_complete")
            self.monitor.end_step(step_name, success=True)
            
            return ParseFormEvent(
                application_form=ev.application_form,
                resume_file=ev.resume_file
            )
            
        except Exception as e:
            self.monitor.log_error(step_name, e, {
                "resume_file": ev.resume_file,
                "application_form": ev.application_form
            })
            self.monitor.end_step(step_name, success=False)
            raise

    async def _setup_vector_store(self):
        """Setup Qdrant vector store"""
            # if self.config.QDRANT_INDEX_NAME not in [index.name for index in self.qd.list_indexes()]:
            #     logger.info(f"🔧 Creating new Qdrant index: {self.config.QDRANT_INDEX_NAME}")
            #     print('self.config.EMBEDDING_DIMENSION', self.config.EMBEDDING_DIMENSION)
                # self.pc.create_index(
                #     name=self.config.PINECONE_INDEX_NAME,
                #     dimension=self.config.EMBEDDING_DIMENSION,
                #     metric="cosine",
                #     spec=ServerlessSpec(
                #         cloud=self.config.PINECONE_CLOUD,
                #         region=self.config.PINECONE_REGION
                #     )
                # )
            
            
            # self.pc_index = self.pc.Index(self.config.PINECONE_INDEX_NAME)
                # self.vector_store = PineconeVectorStore(pinecone_index=self.pc_index)
        try:
            collection_name = self.config.QDRANT_INDEX_NAME

            # 1. Ensure collection exists
            existing = await self.qd.get_collections()
            existing_names = [c.name for c in existing.collections]

            if collection_name not in existing_names:
                logger.info(f"Creating Qdrant collection '{collection_name}'...")
                await self.qd.create_collection(
                    collection_name=collection_name,
                    vectors_config=qdrant_models.VectorParams(
                        size=self.config.EMBEDDING_DIMENSION,
                        distance=qdrant_models.Distance.COSINE,
                    ),
                )
                logger.info(f"✅ Collection '{collection_name}' created")
            else:
                logger.info(f"✅ Collection '{collection_name}' already exists")

            # 2. Create payload index — explicitly handle each error case
            try:
                await self.qd.create_payload_index(
                    collection_name=collection_name,
                    field_name="resume_file",
                    field_schema=qdrant_models.PayloadSchemaType.KEYWORD,
                )
                logger.info("✅ Payload index created for 'metadata.resume_file'")
            except Exception as idx_err:
                err_str = str(idx_err).lower()
                if "already exists" in err_str or "conflict" in err_str:
                    logger.info("ℹ️  Payload index already exists — continuing")
                else:
                    # ← THIS is what was being silently swallowed before
                    logger.error(f"❌ Payload index creation FAILED with unexpected error: {idx_err}")
                    raise  # Re-raise so the real error surfaces in your logs

            # 3. Declare vector store wrapper
            self.vector_store = QdrantVectorStore(
                aclient=self.qd,
                collection_name=collection_name,
            )
            logger.info("✅ Vector store setup complete")

        except Exception as e:
            logger.error(f"❌ Vector store setup failed: {str(e)}")
            raise


    async def _ensure_payload_index(self):
        """
        Create payload index on metadata.resume_file AFTER the collection exists.
        Must be called after ingestion_pipeline.arun() so the collection is guaranteed
        to exist. Safe to call multiple times — silently ignores 'already exists' errors.
        """
        try:
            await self.qd.create_payload_index(
                collection_name=self.config.QDRANT_INDEX_NAME,
                field_name="metadata.resume_file",   # LlamaIndex nests metadata under this prefix
                field_schema=qdrant_models.PayloadSchemaType.KEYWORD,
            )
            logger.info("✅ Payload index created for 'metadata.resume_file'")
        except Exception as e:
            # Qdrant raises if the index already exists — that's fine
            logger.info(f"ℹ️  Payload index already exists (safe to ignore): {e}")



    async def _process_and_index_resume(self, resume_file: str, ctx: Context):
        """Process and index the resume"""
        try:
            workflow_utils.CURRENT_RESUME_FILE = resume_file
            llama_cloud= AsyncLlamaCloud(api_key= self.config.LLAMA_PARSE_API_KEY)
            file_obj= await llama_cloud.files.create(file= resume_file, purpose="parse")
            result= await llama_cloud.parsing.parse(
                file_id= file_obj.id,
                tier="agentic",
                version="latest",
                expand=["markdown"],
                # agentic_options= {
                #     "custom_prompt": "You must annotate and label each piece of information you have extracted. For example, if you extract a user full name from a resume, return your output like first_name: <user first name in resume>.\n last_name: <user first name in resume>, eduction: <user education in resume>...etc"
                # }
            )
            # print("Parsing result:\n", result.items.pages[0].items)
            list_nodes = [Document(text= t, ) for t in group_resume_sections(result.markdown.pages[0].markdown)]
            # parsed_doc= Document(text=" . ".join(list_nodes)) if list_nodes else None
            print("-------------------------" * 10)
            print("list_nodes:\n", list_nodes)
            print("-------------------------" * 10)
            
            # Create ingestion pipeline
            ingestion_pipeline = IngestionPipeline(
                name="resume_processing_pipeline",
                project_name="resume_matcher_v2",
                transformations=[
                    SentenceSplitter(
                        chunk_size=self.config.CHUNK_SIZE,
                        chunk_overlap=self.config.CHUNK_OVERLAP,
                        separator="\n",
                        paragraph_separator="\n",

                    ),
                    ResumeTextProcessor(),
                    self.embed_model
                ],
                vector_store=self.vector_store
            )
            # Process and store documents
            logger.info("🔄 Processing and indexing resume content...")
            await ingestion_pipeline.arun(documents=list_nodes, )
            await self._inspect_qdrant_payload()  # ← add this line temporarily

            
            await self._ensure_payload_index()

            # Setup query engine
            storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
            index = VectorStoreIndex.from_vector_store(
                vector_store=self.vector_store,
                storage_context=storage_context,
                embed_model=self.embed_model
            )


            class RAGStringQueryEngine(CustomQueryEngine):
                """RAG String Query Engine with proper feedback handling."""
                retriever: BaseRetriever
                llm: OpenAI
                ctx: Optional[Any] = None
                _human_feedbacks: List[Any] = []
                _current_responses: List[Any] = []

                def __init__(
                    self,
                    retriever: BaseRetriever,
                    llm: OpenAI,
                    ctx: Optional[Any] = None,
                    **kwargs
                ):
                    super().__init__(
                        retriever=retriever,
                        llm=llm,
                        ctx=ctx,
                        **kwargs
                    )
                    self._human_feedbacks = []
                    self._current_responses = []
                    self.ctx = ctx  

                async def load_feedback_data(self):
                    """Load human feedback and response data from context store."""
                    if self.ctx and hasattr(self.ctx, 'store'):
                        try:
                            self._human_feedbacks = await self.ctx.store.get("human_feedbacks", [])
                            logger.info(f"DEBUG: load_feedback_data loaded {len(self._human_feedbacks)} feedback items")
                            self._current_responses = await self.ctx.store.get("current_responses", [])
                            logger.info(f"✅ Loaded {len(self._human_feedbacks)} feedback items from context store")
                            
                            # Debug: Log the feedback data
                            if self._human_feedbacks:
                                for i, fb in enumerate(self._human_feedbacks):
                                    logger.info(f"  Feedback {i+1}: Field='{fb.get('field')}', Feedback='{fb.get('feedback', '')[:50]}...'")
                            else:
                                logger.info("  No feedback data found in context store")
                                
                        except Exception as e:
                            logger.error(f"❌ Failed to load feedback data: {e}")
                            self._human_feedbacks = []
                            self._current_responses = []
                    else:
                        logger.warning("⚠️ No context or store available for loading feedback data")
                        if not self.ctx:
                            logger.warning("  - ctx is None")
                        elif not hasattr(self.ctx, 'store'):
                            logger.warning("  - ctx has no 'store' attribute")

                def custom_query(self, query_str: str):
                    """Required synchronous implementation"""
                    try:
                        loop = asyncio.get_running_loop()
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(self._sync_query_wrapper, query_str)
                            return future.result()
                    except RuntimeError:
                        return asyncio.run(self._async_query_implementation(query_str))

                def _sync_query_wrapper(self, query_str: str):
                    """Wrapper to run async query in a new event loop"""
                    return asyncio.run(self._async_query_implementation(query_str))

                async def custom_query_async(self, query_str: str):
                    """Async version that loads feedback data before processing."""
                    # ALWAYS load fresh feedback data before processing
                    await self.load_feedback_data()
                    return await self._async_query_implementation(query_str)

                def custom_query_with_feedback(self, query_str: str, human_feedbacks=None, current_responses=None):
                    """Version that accepts feedback data as parameters"""
                    feedbacks_to_use = human_feedbacks or []
                    responses_to_use = current_responses or []
                    
                    # Log what feedback we're using
                    logger.info(f"🔄 custom_query_with_feedback called for '{query_str}' with {len(feedbacks_to_use)} feedbacks")
                    if feedbacks_to_use:
                        for fb in feedbacks_to_use:
                            logger.info(f"  - Feedback for '{fb.get('field')}': {fb.get('feedback', '')[:50]}...")
                    
                    return self._execute_query_sync(query_str, feedbacks_to_use, responses_to_use)

                async def _async_query_implementation(self, query_str: str):
                    """Core async query implementation with loaded feedback"""
                    return await self._execute_query_async(query_str, self._human_feedbacks, self._current_responses)

                def _execute_query_sync(self, query_str: str, human_feedbacks: List, current_responses: List):
                    """Synchronous query execution with feedback handling"""
                    try:
                        logger.info(f"🔍 _execute_query_sync for '{query_str}' with {len(human_feedbacks)} feedbacks")
                        
                        nodes = self.retriever.retrieve(query_str)
                        context_str = "\n\n".join([n.node.get_content() for n in nodes])
                        
                        if not context_str.strip():
                            logger.warning(f"⚠️ No context found for query: {query_str}")
                            return self._create_fallback_response(query_str)
                        
                        # Build prompt with feedback
                        prompt_text = self._build_prompt_with_feedback(query_str, context_str, human_feedbacks, current_responses)
                        
                        try:
                            response_text = self.llm.complete(prompt_text).text
                            logger.info(f"✅ Generated response for '{query_str}': {response_text[:100]}...")
                            
                            return type('Response', (), {
                                'response': response_text,
                                'source_nodes': nodes
                            })()
                            
                        except Exception as llm_error:
                            logger.error(f"❌ LLM call failed for {query_str}: {str(llm_error)}")
                            return self._create_fallback_response(query_str)
                            
                    except Exception as e:
                        logger.error(f"❌ Query execution failed for {query_str}: {str(e)}")
                        return self._create_fallback_response(query_str)
                _retrieval_semaphore = asyncio.Semaphore(5)

                async def _execute_query_async(self, query_str: str, human_feedbacks: List, current_responses: List):

                    """Async query execution with feedback handling"""
                    logger.info(f"🔍 _execute_query_async for '{query_str}' with {len(human_feedbacks)} feedbacks")
                    # print("self.retriever:\n", self.retriever)
                    try:
                        async with self._retrieval_semaphore:
                            nodes = await self.retriever.aretrieve(query_str)
                    except Exception as e:
                        logger.error(f"❌ Async query execution failed for {query_str}: {type(e).__name__}: {e!r}")
                        return self._create_fallback_response(query_str)
                    # print("nodes:\n", nodes)
                    context_str = "\n\n".join([n.node.get_content() for n in nodes])
                    list_of_nodes= [n.node.get_content() for n in nodes]
                    logger.info(f"Retrieved Nodes for query: {query_str} :\n {list_of_nodes} nodes")

                    if not context_str.strip():
                        logger.warning(f"⚠️ No context found for query: {query_str}")
                        return self._create_fallback_response(query_str)
                    
                    # Build prompt with feedback
                    prompt_text = self._build_prompt_with_feedback(query_str, context_str, human_feedbacks, current_responses)
                    
                    try:
                        response_result = await self.llm.acomplete(prompt_text)
                        response_text = response_result.text
                        logger.info(f"✅ Generated response for '{query_str}': {response_text[:100]}...")
                        
                        return type('Response', (), {
                            'response': response_text,
                            'source_nodes': nodes
                        })()
                        
                    except Exception as llm_error:
                        logger.error(f"❌ Async LLM call failed for {query_str}: {str(llm_error)}")
                        return self._create_fallback_response(query_str)
                        

                def _create_fallback_response(self, query_str: str):
                    """Create a fallback response"""
                    return type('Response', (), {
                        'response': "Based on the provided resume, this information is not available.",
                        'source_nodes': []
                    })()

                def _build_prompt_with_feedback(self, query_str: str, context_str: str, human_feedbacks: List, current_responses: List) -> str:
                    """Build prompt template with feedback integration"""
                    # Base template
                    logger.info(f"DEBUG: _build_prompt_with_feedback called with {len(human_feedbacks)} feedbacks for query: {query_str}")
                    for fb in human_feedbacks:
                        logger.info(f"DEBUG: Feedback - Field: {fb.get('field')}, Content: {fb.get('feedback', '')[:50]}...")

                    base_template = f"""
            <role>You are an expert HR assistant specializing in resume analysis and application form completion.</role>
            <task>
            Based on the provided resume context, answer the specific query about the candidate. 
            Your response should be accurate, professional, and directly address the question asked.
            </task>
            <context>
            {context_str}
            </context>
            <query>
            Based on the candidate's resume context provided above, synthesize a response for this application field: {query_str}
            </query>

            <instructions>
            1. ONLY use information explicitly present in the provided context
            2. If the context doesn't contain relevant information, clearly state: "Based on the provided resume, this information is not available."
            3. Be specific and provide concrete details when available
            4. Format your response professionally as it will be used in an application form
            5. If dates are mentioned, include them in your response
            6. For experience-related questions, prioritize the most recent and relevant information
            </instructions>

            <response_format>
            Provide a clear, concise response that directly addresses the query. Do not include explanatory text about your process.
            </response_format>
            """        
                    # Check for specific feedback for this field
                    logger.info(f"human_feedbacks _build_prompt_with_feedback: {human_feedbacks}")
                    field_feedback = None
                    if human_feedbacks:
                        logger.info(f"🔍 Checking {len(human_feedbacks)} feedbacks for field '{query_str}'")
                        for fb in human_feedbacks:
                            logger.info(f"  - Feedback field: '{fb.get('field')}' vs query: '{query_str}'")
                            if fb.get("field") == query_str:
                                field_feedback = fb
                                break
                    
                    if field_feedback:
                        feedback_text = field_feedback["feedback"]
                        logger.info(f"✅ Found feedback for '{query_str}': {feedback_text[:100]}...")
                        
                        # Find previous response
                        previous_response = "No previous response found."
                        if current_responses:
                            for resp in current_responses:
                                if hasattr(resp, 'field') and resp.field == query_str:
                                    previous_response = resp.response
                                    break
                        
                        # Add feedback section to template
                        feedback_section = f"""
            IMPORTANT: We have received user feedback about your previous response for this field.

            <user_feedback>
            Field: {query_str}
            Feedback: {feedback_text}
            </user_feedback>

            <previous_response>
            {previous_response}
            </previous_response>

            <enhancement_guidelines>
            - Address the specific concerns raised in the feedback
            - Improve upon your previous response based on the user's feedback
            - Provide more detailed or different information as requested
            - Maintain accuracy to the resume content
            - Improve the relevance and presentation of the information
            </enhancement_guidelines>

            Please provide an improved response for the field: {query_str}
            """
                        base_template += feedback_section
                    else:
                        logger.info(f"ℹ️ No specific feedback found for field: {query_str}")
                    
                    return base_template    

            self.query_engine= RAGStringQueryEngine(
                retriever=index.as_retriever(
                    filters=MetadataFilters(filters=[
                        MetadataFilter(
                            key="resume_file",
                            value=resume_file,
                            operator=FilterOperator.EQ
                        )
                    ]),
                    similarity_top_k= self.config.SIMILARITY_TOP_K
                ),
                llm=self.llm,
                ctx=ctx  # Pass context for feedback loading
            )

        except Exception as e:
            logger.error(f"❌ Resume processing failed: {str(e)}")
            raise

            
    @step
    async def form_parsing_step(self, ev: ParseFormEvent, ctx: Context) -> GenerateQuestionsEvent:
        """📋 STEP 2: Parse and extract fields from application form"""
        step_name = "form_parsing_step"
        self.monitor.start_step(step_name)
        self.perf_tracker.checkpoint("form_parsing_started")
        
        try:
            ctx.write_event_to_stream(LogEvent(log="Starting application form parsing..."))
            logger.info("📋 Starting application form parsing...")
            
            # Track LlamaParse API call
            parse_start = time.time()
            # llama_parse = LlamaParse(
            #     result_type="markdown",
            #     system_prompt="""
            #     Analyze this job application form and extract all fillable fields:
                
            #     1. IDENTIFY all input fields, checkboxes, dropdown options, and text areas
            #     2. EXTRACT field labels, descriptions, and any specific requirements
            #     3. CATEGORIZE fields by type (personal info, experience, education, skills, etc.)
            #     4. NOTE any mandatory vs optional field indicators
            #     5. PRESERVE the original field names and formatting
            #     6. LIST fields in the order they appear in the form
                
            #     Focus on fields that require candidate information input, not instructional text.
            #     Format output as a clean bulleted list with field names as the primary items.
            #     """,
            #     api_key=self.config.LLAMA_PARSE_API_KEY
            # )
            
            # logger.info(f"📖 Parsing application form: {ev.application_form}")
            # form_docs = await llama_parse.aload_data(ev.application_form)
            # parsed_form_content = form_docs[0].text

            llama_cloud= AsyncLlamaCloud(api_key= self.config.LLAMA_PARSE_API_KEY)
            file_obj= await llama_cloud.files.create(file= ev.application_form, purpose="parse")
            result= await llama_cloud.parsing.parse(
                file_id= file_obj.id,
                tier="agentic",
                version="latest",
                expand=["items"]
            )            
            parse_duration = time.time() - parse_start
            self.perf_tracker.record_api_call("llama_parse", parse_duration)
            text_res=[item.md for item in result.items.pages[0].items]
            parsed_form_content= " ".join(text_res)
            # Extract fields using structured output
            llm_start = time.time()
            extraction_prompt = PromptTemplate(
                template=f"""
                <role>You are an expert form analyst specializing in job application processing.</role>
                
                <task>
                Extract all fillable fields from the parsed application form content.
                Focus only on fields where a candidate would need to provide information.
                </task>
                
                <parsed_form>
                {parsed_form_content}
                </parsed_form>
                
                <instructions>
                1. Identify ALL fields that require candidate input (text boxes, dropdowns, checkboxes, etc.)
                2. Extract the EXACT field labels/names as they appear in the form
                3. Exclude instructional text, headings, or static content
                4. Include fields for: personal details, work experience, education, skills, references, etc.
                5. Maintain the original wording and terminology from the form
                6. List fields in logical groupings (personal info, experience, education, etc.)
                </instructions>
                
                Return only the structured list of field names.
                """
            )
            
            structured_output = await self.llm.astructured_predict(
                prompt=extraction_prompt,
                output_cls=FormFields
            )
            
            llm_duration = time.time() - llm_start
            self.perf_tracker.record_api_call("openai_field_extraction", llm_duration)
            
            fields = structured_output.fields
            logger.info(f"📝 Extracted {len(fields)} fields from application form:")
            for i, field in enumerate(fields, 1):
                logger.info(f"  {i}. {field}")
            
            # Store fields in context
            await ctx.store.set("application_fields", fields)
            await ctx.store.set("total_fields", len(fields))

            # LOGGING POINT 3: Track processed fields in monitor
            self.monitor.set_processed_fields(fields)

            # Log event
            self.monitor.log_event("fields_extracted", {
                "field_count": len(fields),
                "parse_duration": parse_duration,
                "extraction_duration": llm_duration
            })
            
            self.perf_tracker.checkpoint("form_parsing_complete")
            self.monitor.end_step(step_name, success=True)
            
            return GenerateQuestionsEvent()
            
        except Exception as e:
            self.monitor.log_error(step_name, e, {"application_form": ev.application_form})
            self.monitor.end_step(step_name, success=False)
            raise

    @step  
    async def question_generation_step(self, ev: GenerateQuestionsEvent | FeedbackEvent, ctx: Context) -> QueryEvent:
        """🤔 STEP 3: Generate intelligent queries for each form field"""
        step_name = "question_generation_step"
        self.monitor.start_step(step_name)

        fields = await ctx.store.get("application_fields")
        try: 
            # Handle feedback-driven regeneration
            if isinstance(ev, FeedbackEvent):
                logger.info(f"🔄 Processing feedback for {len(ev.feedbacks)} fields")
                ctx.write_event_to_stream(LogEvent(log=f"🔄 Regenerate intelligent queries for {len(ev.feedbacks)} requested fields"))
                await ctx.store.set("feedback_fields_count", len(ev.feedbacks))
                # Record user feedback in monitor
                feedback_fields = [fb["field"] for fb in ev.feedbacks]
                feedback_details = [{"field": fb["field"], "feedback": fb["feedback"]} for fb in ev.feedbacks]
                self.monitor.record_user_feedback_request(feedback_fields, feedback_details)

                for feedback_item in ev.feedbacks:
                    field_name = feedback_item["field"]
                    logger.info(f"🔄 Regenerating response for field: {field_name}")
                    ctx.write_event_to_stream(LogEvent(log=f"Regenerating response for field: {field_name}"))
                    ctx.send_event(QueryEvent(field=field_name, query=field_name))
                return
            
            # Initial query generation
            logger.info(f"❓ Generating queries for {len(fields)} application fields...")
            
            await ctx.store.set("total_fields", len(fields))
            await ctx.store.set("feedback_fields_count", 0)  # Initialize feedback count
            
            for field in fields:
                logger.info(f"📤 Sending query for field: {field}")
                ctx.send_event(QueryEvent(field=field, query=field))

            self.monitor.end_step(step_name, success= True)
            return
        except Exception as e:
            self.monitor.end_step(step_name, success=False)
            raise ValueError(f"error during question generation: {e}")



    @step(num_workers=10000)
    async def query_processing_step(self, ev: QueryEvent, ctx: Context) -> ResponseEvent:
        """🔍 STEP 4: Process queries against the resume data"""
        step_name = f"query_processing_{ev.field}"
        self.monitor.start_step(step_name)
        
        try:
            logger.info(f"🔍 Processing query for field: {ev.field}")
            ctx.write_event_to_stream(LogEvent(log=f"🔍 Processing query for field: {ev.field}"))
            
            # Track query execution time
            query_start = time.time()
            self.query_engine.ctx = ctx  # Ensure context is current
            # Use the async query method which will load fresh feedback data
            logger.info(f"ev.query: {ev.query}")
            response = await self.query_engine.custom_query_async(ev.query)
            
            logger.info(f"response of query engine: {response.response}")
            query_duration = time.time() - query_start
            
            # Record API call performance
            self.perf_tracker.record_api_call("query_engine", query_duration)
            
            # Extract confidence scores
            confidence_scores = [s.score for s in response.source_nodes] if hasattr(response, 'source_nodes') and response.source_nodes else [0.5]
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
            
            # Record confidence scores in monitor
            self.monitor.record_field_confidence(ev.field, confidence_scores)
            
            # Log low confidence responses
            if avg_confidence < self.config.MIN_CONFIDENCE_THRESHOLD:
                self.monitor.log_event("low_confidence_response", {
                    "field": ev.field,
                    "average_confidence": avg_confidence,
                    "all_confidence_score": confidence_scores,
                    "threshold": self.config.MIN_CONFIDENCE_THRESHOLD
                })
            
            logger.info(f"✅ Generated response for field '{ev.field}' (confidence: {confidence_scores})")
            
            self.monitor.end_step(step_name, success=True)
            
            return ResponseEvent(
                field=ev.field,
                response=response.response,
                confidence_scores=confidence_scores,
            )
            
        except Exception as e:
            self.monitor.log_error(step_name, e, {"field": ev.field, "query": ev.query})
            self.monitor.end_step(step_name, success=False)
            
            # Return fallback response
            return ResponseEvent(
                field=ev.field,
                response="Information not available in the provided resume.",
                confidence_scores=[0.0],
            )

    @step
    async def response_aggregation_step(self, ev: ResponseEvent, ctx: Context) -> InputRequiredEvent:
        """📊 STEP 5: Aggregate responses and prepare for human review"""
        step_name = "response_aggregation_step"
        self.monitor.start_step(step_name)

        try:
            total_fields = await ctx.store.get("total_fields")
            feedback_count = await ctx.store.get("feedback_fields_count", 0)
            
            target_count = feedback_count if feedback_count > 0 else total_fields
            # Collect all responses for this batch
            all_responses = ctx.collect_events(ev, [ResponseEvent] * target_count)
            if all_responses is None:
                return None

            ctx.write_event_to_stream(LogEvent(log=f"📊 Aggregating {len(all_responses)} responses"))
            logger.info(f"📊 Aggregating {len(all_responses)} responses")
            
            # Handle feedback updates
            if feedback_count > 0:
                # Update existing responses with new feedback-driven ones
                existing_responses = await ctx.store.get("current_responses", [])
                
                # Create a mapping for easy updates
                response_map = {r.field: r for r in existing_responses}
                for new_response in all_responses:
                    response_map[new_response.field] = new_response
                
                final_responses = list(response_map.values())
            else:
                final_responses = all_responses
            
            # Store current responses
            await ctx.store.set("current_responses", final_responses)
            
            # Format results for presentation
            formatted_results = self._format_results_for_review(final_responses)
            
            logger.info("✨ Response aggregation completed. Requesting human review...")
            ctx.write_event_to_stream(LogEvent(log="✨ Response aggregation completed. Requesting human review..."))

            self.monitor.end_step(step_name, success=True)


            return InputRequiredEvent(
                prefix="📋 **Application Form Completion Results**\n\nPlease review the generated responses below. You can provide feedback for any fields that need improvement, or approve the results to finish.\n\n**Instructions:**\n- To suggest improvements: specify the field name and your feedback\n- To approve all: simply type 'approved' or 'looks good'\n\n",
                result=formatted_results
            )

        except Exception as e:
            self.monitor.end_step(step_name, success=False)
            raise ValueError(f'Value error during aggregation results: {e}')

    def _format_results_for_review(self, responses: List[ResponseEvent]) -> str:
        """Format responses for human review"""
        formatted_sections = []
        
        for i, response in enumerate(responses):
            confidence_indicator = " ❓"  # Default indicator
            mean_confidence_scores = 0.0  # Default score

            if response.confidence_scores and len(response.confidence_scores) > 0:
                print("response.confidence_scores:\n", response.confidence_scores)
                mean_confidence_scores = (sum(response.confidence_scores) / len(response.confidence_scores))
                if mean_confidence_scores >= 0.8:
                    confidence_indicator = " ✅"
                elif mean_confidence_scores >= 0.6:
                    confidence_indicator = " ⚠️"
                else:
                    confidence_indicator = " ❌"
            
#             section = f"""
# **{i + 1}. {response.field}**{confidence_indicator} (confidence: {mean_confidence_scores:.2f})
# {response.response}
# {"-" * 50}"""
#             formatted_sections.append(section)
            section = {
                "field": response.field,
                "confidence_indicator": confidence_indicator,
                "confidence_score": f"{mean_confidence_scores:.2f}",
                "response_text": response.response
            }
            formatted_sections.append(section)
        
        return formatted_sections

    @step
    async def human_feedback_processing_step(self, ev: HumanResponseEvent, ctx: Context) -> FeedbackEvent | StopEvent:
        """👤 STEP 6: Process human feedback and determine next actions"""
        step_name = "human_feedback_processing_step"
        self.monitor.start_step(step_name)

        logger.info("👤 Processing human feedback...")
        ctx.write_event_to_stream(LogEvent(log="👤 Processing human feedback..."))
        
        try:
            fields = await ctx.store.get("application_fields")
            
            # Enhanced feedback analysis prompt
            feedback_analysis_prompt = PromptTemplate(
                template=f"""
                <role>You are an expert feedback analyzer for application form processing.</role>
                
                <task>
                Analyze the human feedback and extract specific field improvement requests.
                </task>
                
                <context>
                Available application fields: {fields}
                Human feedback: {ev.response}
                </context>
                
                <instructions>
                1. IDENTIFY which specific fields (if any) the human wants to improve
                2. EXTRACT the specific feedback/improvement request for each field
                3. DETERMINE if the human is expressing satisfaction (words like: "approved", "good", "fine", "okay", "accept")
                4. If NO specific improvements are mentioned, return an empty list
                5. Match field names EXACTLY as they appear in the available fields list
                6. Focus on actionable feedback that can improve the responses
                </instructions>
                
                <response_requirements>
                - Return specific field names and their corresponding feedback
                - If human approves/accepts, return empty feedback list
                - Ensure field names match exactly with provided list
                </response_requirements>
                """
            )
            
            feedback_response = await self.llm.astructured_predict(
                prompt=feedback_analysis_prompt,
                output_cls=FeedbackCollection
            )
            
            if feedback_response.feedbacks and len(feedback_response.feedbacks) > 0:
                logger.info(f"🔄 Processing improvement requests for {len(feedback_response.feedbacks)} fields")
                ctx.write_event_to_stream(LogEvent(log=f"🔄 Processing improvement requests for {len(feedback_response.feedbacks)} fields"))
                for fb in feedback_response.feedbacks:
                    logger.info(f"  - {fb['field']}: {fb['feedback'][:100]}...")
                
                logger.info(f"human_feedbacks: {feedback_response.feedbacks}")
                await ctx.store.set("human_feedbacks", feedback_response.feedbacks)
                self.monitor.end_step(step_name, success= True)
                return FeedbackEvent(feedbacks=feedback_response.feedbacks)
            else:
                logger.info("✅ Human feedback indicates approval. Finalizing results...")
                ctx.write_event_to_stream(LogEvent(log="✅ Human feedback indicates approval. Finalizing results..."))
                
                # Get final results
                final_responses = await ctx.store.get("current_responses", [])
                final_result = self._format_final_results(final_responses)
                self.monitor.end_step(step_name, success= True)
                return StopEvent(result=final_result)
                
        except Exception as e:
            logger.error(f"❌ Feedback processing failed: {str(e)}")
            # Default to stopping with current results
            final_responses = await ctx.store.get("current_responses", [])
            final_result = self._format_final_results(final_responses)
            self.monitor.end_step(step_name, success= False)

            return StopEvent(result=final_result)

    def _format_final_results(self, responses: List[ResponseEvent]) -> str:
        """Format final results for output"""
        result_sections = []
        
        header = """
# 🎉 Application Form Completion Results
## Generated by AI Resume Matching System

The following information has been extracted from the candidate's resume and formatted for the job application:

"""
        result_sections.append(header)
        
        for response in responses:
            section = f"""
### {response.field}
{response.response}

"""
            result_sections.append(section)
        
        footer = f"""
---
*✨ Processing completed successfully with {len(responses)} fields filled.*
*🤖 Generated using LlamaIndex Workflow architecture*
"""
        result_sections.append(footer)
        
        return "".join(result_sections)

    async def finalize_workflow(self, session_id: str = None):
        """Finalize workflow and generate comprehensive reports"""
        try:
            # Stop monitoring
            self.monitor.stop_monitoring()
            
            # Generate performance report
            perf_report = self.perf_tracker.get_performance_report()
            monitoring_summary = self.monitor.get_summary()
            
            # Log final statistics
            logger.info("🎉 Workflow completed successfully!")
            logger.info(f"⏱️  Total execution time: {perf_report['total_execution_time']:.2f}s")
            logger.info(f"✅ Success rate: {monitoring_summary['success_rate']*100:.1f}%")
            logger.info(f"🔧 Steps completed: {monitoring_summary['successful_steps']}/{monitoring_summary['total_steps']}")
            
            # Send detailed reports to n8n webhook instead of local file
            logger.info("📤 Sending comprehensive report to n8n webhook...")
            webhook_result = await self.monitor.send_report_to_n8n(session_id)
            
            if webhook_result.get("success"):
                logger.info("✅ Report successfully sent to n8n webhook for processing")
                logger.info("🔄 n8n will now process analytics and send insights to Slack")
            else:
                logger.warning("⚠️  n8n webhook failed, but local backup was saved")
                logger.warning(f"Webhook error: {webhook_result.get('message')}")
            
            # Check for performance issues
            if perf_report['bottlenecks']:
                logger.warning("⚠️  Performance bottlenecks detected:")
                for bottleneck in perf_report['bottlenecks']:
                    logger.warning(f"  - {bottleneck['step']}: {bottleneck['duration']:.2f}s ({bottleneck['severity']} severity)")
            
            return {
                'performance': perf_report,
                'monitoring': monitoring_summary,
                'n8n_integration': webhook_result,
                'report_path': webhook_result.get('local_backup'),  # Local backup path
                'webhook_success': webhook_result.get('success', False)
            }
            
        except Exception as e:
            logger.error(f"❌ Workflow finalization failed: {str(e)}")
            
            # Try to send error report to n8n
            try:
                error_report = {
                    'enhanced_monitoring_summary': {
                        'total_execution_time': 0,
                        'success_rate': 0.0,
                        'total_steps': 0,
                        'successful_steps': 0,
                        'errors_count': 1,
                        'error_details': str(e)
                    },
                    'finalization_error': True,
                    'error_message': str(e),
                    'report_metadata': {
                        'report_version': '2.0_enhanced_error',
                        'generated_by': 'Enhanced WorkflowMonitor (Error)',
                        'generation_timestamp': datetime.now().isoformat()
                    }
                }
                
                await n8n_webhook_client.send_report(error_report, session_id)
                logger.info("📤 Error report sent to n8n webhook")
                
            except Exception as webhook_error:
                logger.error(f"Failed to send error report to n8n: {str(webhook_error)}")
            
            return {
                'performance': {},
                'monitoring': {},
                'n8n_integration': {'success': False, 'error': str(e)},
                'error': str(e)
            }

#</engine.py>

