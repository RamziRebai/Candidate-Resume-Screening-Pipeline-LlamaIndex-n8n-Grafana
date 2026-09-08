// {/* <ResumeMatchingApp.tsx> */}
import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { 
  Upload, 
  Settings, 
  Play, 
  CheckCircle, 
  AlertCircle, 
  Clock, 
  Send, 
  FileText,
  Zap,
  Brain,
  Square,
  Target,
  Thermometer,
  RefreshCw,
  MessageSquare,
  Eye,
  Loader2,
  X,
  Database
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const API_BASE_URL = 'http://localhost:8000';

// Types
type Config = {
  llm_model: string;
  embedding_model: string;
  qdrant_index_name: string;
  chunk_size: number;
  chunk_overlap: number;
  similarity_top_k: number;
  min_confidence_threshold: number;
  llm_temperature: number;
};

type Tooltips = {
  llm_model: string;
  embedding_model: string;
  qdrant_index_name: string;
  chunk_size: string;
  chunk_overlap: string;
  similarity_top_k: string;
  min_confidence_threshold: string;
  llm_temperature: string;
};

// Results data types
type FieldResult = {
  name: string;
  response: string;
  confidence: 'high' | 'medium' | 'low' | string;
  confidence_score?: number;
  confidence_scores?: number[];
  confidence_indicator?: string;
};

type ResultsData = {
  status?: string;
  fields?: FieldResult[];
  raw_result?: string;
} | null;

// Top-level components (stable identities)
const ConfigPanel: React.FC<{
  config: Config;
  setConfig: React.Dispatch<React.SetStateAction<Config>>;
  tooltips: Tooltips;
}> = React.memo(({ config, setConfig, tooltips }) => (
  <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
    <div className="flex items-center mb-4">
      <Settings className="w-5 h-5 mr-2 text-blue-600" />
      <h3 className="text-lg font-semibold">Configuration Settings</h3>
    </div>
    
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          <Brain className="w-4 h-4 inline mr-1" />
          LLM Model
        </label>
        <select
          value={config.llm_model}
          onChange={(e) => setConfig(prev => ({ ...prev, llm_model: e.target.value }))}
          className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          title={tooltips.llm_model}
        >
          <optgroup label="Google Gemini Models">
            <option value="gemini-3.5-flash">Gemini 3.5 Flash (Fast & Latest)</option>
            <option value="gemini-3.5-flash-lite">Gemini 3.0 Flash Lite (Fatest, less capable)</option>
          </optgroup>
          <optgroup label="OpenAI Models">
            <option value="gpt-5.4">GPT-5.4 (High Performance)</option>
            <option value="gpt-5.4-mini">GPT-5.4-mini (Fast & Economical)</option>
          </optgroup>
          <optgroup label="Advanced Models">
            <option value="gpt-5.6">GPT 5.6 (Reasoning)</option>
            <option value="claude-opus-4-8">Claude Opus 4.8 (Efficient)</option>
          </optgroup>
        </select>
      </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            <Square className="w-4 h-4 inline mr-1" />
            Embedding Model
          </label>
        <select
          value={config.embedding_model}
          onChange={(e) => setConfig(prev => ({ ...prev, embedding_model: e.target.value }))}
          className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          title={tooltips.embedding_model}
        >
          <optgroup label="Google Embeddings">
            <option value="gemini-embedding-001">Gemini Embedding 001 (768 dim, Latest)</option>
          </optgroup>
          <optgroup label="OpenAI Embeddings">
            <option value="text-embedding-3-large">Text Embedding 3 Large (3072 dim, Most Capable)</option>
            <option value="text-embedding-3-small">Text Embedding 3 Small (1536 dim, Balanced)</option>
          </optgroup>
        </select>
      </div>

      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          <Database className="w-4 h-4 inline mr-1" />
          Qdrant Collection Name
        </label>
        <input
          type="text"
          value={config.qdrant_index_name}
          onChange={(e) => setConfig(prev => ({ ...prev, qdrant_index_name: e.target.value }))}
          className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          title={tooltips.qdrant_index_name}
          placeholder="e.g. resume-application-matcher"
        />
        <p className="text-xs text-gray-500 mt-1">
          use a unique name per embedding dimension
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          <FileText className="w-4 h-4 inline mr-1" />
          Chunk Size
        </label>
        <input
          type="number"
          min="1"
          value={config.chunk_size}
          onChange={(e) => setConfig(prev => ({ ...prev, chunk_size: parseInt(e.target.value) }))}
          className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          title={tooltips.chunk_size}
        />
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          <RefreshCw className="w-4 h-4 inline mr-1" />
          Chunk Overlap
        </label>
        <input
          type="number"
          min="0"
          value={config.chunk_overlap}
          onChange={(e) => setConfig(prev => ({ ...prev, chunk_overlap: parseInt(e.target.value) }))}
          className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          title={tooltips.chunk_overlap}
        />
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          <Target className="w-4 h-4 inline mr-1" />
          Similarity Top K
        </label>
        <input
          type="number"
          min="1"
          max="20"
          value={config.similarity_top_k}
          onChange={(e) => setConfig(prev => ({ ...prev, similarity_top_k: parseInt(e.target.value) }))}
          className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          title={tooltips.similarity_top_k}
        />
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          <Zap className="w-4 h-4 inline mr-1" />
          Min Confidence ({config.min_confidence_threshold})
        </label>
        <input
          type="range"
          min="0"
          max="1"
          step="0.1"
          value={config.min_confidence_threshold}
          onChange={(e) => setConfig(prev => ({ ...prev, min_confidence_threshold: parseFloat(e.target.value) }))}
          className="w-full"
          title={tooltips.min_confidence_threshold}
        />
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          <Thermometer className="w-4 h-4 inline mr-1" />
          Temperature ({config.llm_temperature})
        </label>
        <input
          type="range"
          min="0"
          max="1"
          step="0.1"
          value={config.llm_temperature}
          onChange={(e) => setConfig(prev => ({ ...prev, llm_temperature: parseFloat(e.target.value) }))}
          className="w-full"
          title={tooltips.llm_temperature}
        />
      </div>
    </div>
  </div>
), (a, b) => a.config === b.config && a.tooltips === b.tooltips);

const ResultsDisplay: React.FC<{
  results: ResultsData;
  selectedFields: string[];
  setSelectedFields: (updater: (prev: string[]) => string[]) => void;
}> = React.memo(({ results, selectedFields, setSelectedFields }) => {
  if (!results) return null;
  const fields = results.fields ?? [];

  const toggleField = (fieldName: string) => {
    setSelectedFields((prev) =>
      prev.includes(fieldName)
        ? prev.filter((f) => f !== fieldName)
        : [...prev, fieldName]
    );
  };

  const badge = (conf: FieldResult['confidence'], score?: number, indicator?: string) => {
    // Use the exact confidence indicator if available, otherwise fall back to confidence level
    const icon = indicator || (conf === 'high' ? '✅' : conf === 'medium' ? '⚠️' : '❌');
    const displayScore = score ? (score * 100).toFixed(0) + '%' : 
                        (conf === 'high' ? '85%' : conf === 'medium' ? '65%' : '45%');
    
    if (icon === '✅' || conf === 'high') return (
      <div className="flex items-center space-x-2">
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
          <span className="mr-1">✅</span> High
        </span>
        <span className="text-xs text-gray-600 font-mono">{displayScore}</span>
      </div>
    );
    if (icon === '⚠️' || conf === 'medium') return (
      <div className="flex items-center space-x-2">
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
          <span className="mr-1">⚠️</span> Medium
        </span>
        <span className="text-xs text-gray-600 font-mono">{displayScore}</span>
      </div>
    );
    return (
      <div className="flex items-center space-x-2">
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
          <span className="mr-1">❌</span> Low
        </span>
        <span className="text-xs text-gray-600 font-mono">{displayScore}</span>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-lg p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              Application Form Completion Results
            </h2>
            <p className="text-gray-600">
              Review the AI-generated responses below. Click fields to select them for improvement.
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm">
              {fields.length} Fields Processed
            </span>
          </div>
        </div>
      </div>

      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div className="flex items-start">
          <AlertCircle className="w-5 h-5 text-yellow-600 mt-0.5 mr-3 flex-shrink-0" />
          <div>
            <h3 className="font-medium text-yellow-800 mb-1">How to Review</h3>
            <ul className="text-sm text-yellow-700 space-y-1">
              <li>• <span className="font-mono">✅ Green</span>: High confidence (80%+)</li>
              <li>• <span className="font-mono">⚠️ Yellow</span>: Medium confidence (60–79%)</li>
              <li>• <span className="font-mono">❌ Red</span>: Low confidence (&lt;60%)</li>
              <li>• <span className="font-semibold">Score</span>: Mean confidence from retrieved documents</li>
              <li>• <span className="font-semibold">Query</span>: What the AI searched for to find this answer</li>
              <li>• Click a field card to select it for feedback</li>
            </ul>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-sm border p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center">
          <FileText className="w-5 h-5 mr-2 text-blue-600" />
          Extracted Field Responses
        </h3>

        {fields.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <FileText className="w-12 h-12 mx-auto mb-4 text-gray-300" />
            <p>No fields were extracted. Check logs for details.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {fields.map((field) => {
              const isSelected = selectedFields.includes(field.name);
              return (
                <div
                  key={field.name}
                  className={`border rounded-lg p-5 cursor-pointer transition-all duration-200 ${
                    isSelected 
                      ? 'border-blue-500 bg-blue-50 shadow-md transform scale-[1.02]' 
                      : 'border-gray-200 bg-white hover:bg-gray-50 hover:shadow-sm'
                  }`}
                  onClick={() => toggleField(field.name)}
                >
                  {/* Header with field name and confidence */}
                  <div className="flex items-start justify-between mb-3">
                    <h4 className="font-semibold text-gray-900 mr-2 leading-tight">{field.name}</h4>
                    {badge(field.confidence, field.confidence_score, field.confidence_indicator)}
                  </div>


                  {/* Response Content */}
                  <div className="mb-3">
                    <div className="flex items-center mb-2">
                      <MessageSquare className="w-3 h-3 mr-1 text-gray-500" />
                      <span className="text-xs font-medium text-gray-600 uppercase tracking-wide">Response</span>
                    </div>
                    <div className="text-sm text-gray-800 leading-relaxed bg-gray-50 p-3 rounded-md border prose prose-sm max-w-none prose-headings:text-gray-900 prose-headings:mt-2 prose-headings:mb-1 prose-p:my-1 prose-ul:my-1 prose-li:my-0 prose-strong:text-gray-900">
                      {field.response ? (
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {field.response}
                        </ReactMarkdown>
                      ) : (
                        <span className="text-gray-400 italic">No response generated</span>
                      )}
                    </div>
                  </div>

                  {/* Selection indicator */}
                  {isSelected && (
                    <div className="flex items-center justify-center mt-3 pt-3 border-t border-blue-200">
                      <CheckCircle className="w-4 h-4 mr-2 text-blue-600" />
                      <span className="text-sm font-medium text-blue-700">Selected for improvement</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
});

const FeedbackInput: React.FC<{ 
  feedback: string;
  setFeedback: (v: string) => void;
  selectedFields: string[];
  setSelectedFields: (updater: (prev: string[]) => string[]) => void;
  isProcessing: boolean;
  onSubmit: (approve: boolean) => void;
}> = React.memo(({ feedback, setFeedback, selectedFields, setSelectedFields, isProcessing, onSubmit }) => (
  <div id="feedback-section" className="bg-white rounded-lg shadow-sm border p-6">
    <div className="flex items-center mb-4">
      <MessageSquare className="w-5 h-5 mr-2 text-blue-600" />
      <h3 className="text-lg font-semibold">Provide Improvement Feedback</h3>
    </div>

    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
      <p className="text-sm text-blue-800 mb-1">
        Select fields above that need changes, then describe what to improve.
      </p>
      <p className="text-xs text-blue-700">
        Be specific about missing details, tone, or accuracy. Example: “Shorten to 2-3 bullet points and include metrics.”
      </p>
    </div>

    <div className="mb-4">
      <p className="text-sm font-medium text-gray-700 mb-2">
        Selected Fields ({selectedFields.length}):
      </p>
      {selectedFields.length === 0 ? (
        <div className="text-center py-4 text-gray-500">
          <Target className="w-8 h-8 mx-auto mb-2 text-gray-300" />
          <p className="text-sm">Click field cards above to select them for feedback</p>
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          {selectedFields.map((field) => (
            <span
              key={field}
              className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm flex items-center border border-blue-200"
            >
              {field}
              <X
                className="w-3 h-3 ml-2 cursor-pointer hover:text-blue-900"
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedFields((prev) => prev.filter((f) => f !== field));
                }}
              />
            </span>
          ))}
        </div>
      )}
    </div>

    <div className="mb-4">
      <label className="block text-sm font-medium text-gray-700 mb-2">Improvement Instructions</label>
      <textarea
        value={feedback}
        onChange={(e) => setFeedback(e.target.value)}
        placeholder="Describe how you'd like the selected fields to be improved."
        className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-vertical"
        rows={4}
        maxLength={800}
      />
      <p className="text-xs text-gray-500 mt-1">{feedback.length}/800 characters</p>
    </div>

    <div className="flex justify-between items-center">
      <button
        onClick={() => {
          setFeedback('');
          setSelectedFields(() => []);
        }}
        className="text-gray-600 hover:text-gray-800 text-sm font-medium"
      >
        Clear All
      </button>

      <div className="flex items-center space-x-3">
        <button
          onClick={() => onSubmit(true)}
          disabled={isProcessing}
          className="flex items-center px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
        >
          Skip & Approve All
        </button>
        <button
          onClick={() => onSubmit(false)}
          disabled={!feedback.trim() || selectedFields.length === 0 || isProcessing}
          className="flex items-center px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
        >
          {isProcessing ? (
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <Send className="w-4 h-4 mr-2" />
          )}
          Submit Improvements
        </button>
      </div>
    </div>
  </div>
));

const LogsPanel: React.FC<{
  logs: { id: string; timestamp: string; level: string; message: string; step?: string }[];
  isLogsExpanded: boolean;
  setIsLogsExpanded: (v: boolean) => void;
  autoScroll: boolean;
  setAutoScroll: (v: boolean) => void;
  logsEndRef: React.RefObject<HTMLDivElement>;
  logsContainerRef: React.RefObject<HTMLDivElement>;
}> = React.memo(({ logs, isLogsExpanded, setIsLogsExpanded, autoScroll, setAutoScroll, logsEndRef, logsContainerRef }) => {
  const onScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const container = e.currentTarget;
    const isAtBottom = Math.abs(container.scrollHeight - container.scrollTop - container.clientHeight) < 5;
    if (!isAtBottom && autoScroll) setAutoScroll(false);
    else if (isAtBottom && !autoScroll) setAutoScroll(true);
  };
  return (
    <div className="bg-gray-900 rounded-lg shadow-sm border border-gray-700 mb-6">
      <div 
        className="flex items-center justify-between p-4 cursor-pointer"
        onClick={() => setIsLogsExpanded(!isLogsExpanded)}
      >
        <div className="flex items-center">
          <Eye className="w-5 h-5 mr-2 text-green-400" />
          <h3 className="text-lg font-semibold text-white">Real-time Logs</h3>
          <span className="ml-2 px-2 py-1 bg-green-600 text-white text-xs rounded-full">
            {logs.length}
          </span>
        </div>
        <div className="flex items-center space-x-2">
          {!autoScroll && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setAutoScroll(true);
                if (logsEndRef.current) logsEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
              }}
              className="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 transition-colors"
            >
              ↓ Scroll to bottom
            </button>
          )}
          <div className="text-gray-400">
            {isLogsExpanded ? '▼' : '▶'}
          </div>
        </div>
      </div>
      {isLogsExpanded && (
        <div 
          ref={logsContainerRef}
          className="max-h-64 overflow-y-auto p-4 pt-0"
          onScroll={onScroll}
        >
          {logs.length === 0 ? (
            <p className="text-gray-400 text-center py-8">No logs yet...</p>
          ) : (
            <div className="space-y-2">
              {logs.map((log) => (
                <div key={log.id} className="flex items-start space-x-3">
                  <span className="text-xs text-gray-500 mt-1 w-16 flex-shrink-0">
                    {log.timestamp}
                  </span>
                  <div className="flex items-center space-x-2">
                    {log.level === 'error' && <AlertCircle className="w-4 h-4 text-red-400" />}
                    {log.level === 'success' && <CheckCircle className="w-4 h-4 text-green-400" />}
                    {log.level === 'info' && <Clock className="w-4 h-4 text-blue-400" />}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm text-gray-300">{log.message}</p>
                    {log.step && (
                      <p className="text-xs text-gray-500 mt-1">Step: {log.step}</p>
                    )}
                  </div>
                </div>
              ))}
              <div ref={logsEndRef} />
            </div>
          )}
        </div>
      )}
    </div>
  );
});

const ResumeMatchingApp = () => {
  // Main application state
  const [currentStep, setCurrentStep] = useState('upload');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  
  // File upload state
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [applicationFile, setApplicationFile] = useState<File | null>(null);
  
  // Configuration state
  const [config, setConfig] = useState({
    llm_model: 'gemini-3.5-flash',
    embedding_model: 'gemini-embedding-001',
    qdrant_index_name: 'resume-application-matcher',
    chunk_size: 200,
    chunk_overlap: 0,
    similarity_top_k: 7,
    min_confidence_threshold: 0.6,
    llm_temperature: 0.0
  });
  
  // Results and feedback state
  const [results, setResults] = useState<any>(null);
  const [feedback, setFeedback] = useState('');
  const [selectedFields, setSelectedFields] = useState<string[]>([]);
  
  // Polling control state
  const [activePollingInterval, setActivePollingInterval] = useState<number | null>(null);
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  
  // Real-time logs state
  const [logs, setLogs] = useState<Array<{
    id: string;
    timestamp: string;
    level: string;
    message: string;
    step?: string;
  }>>([]);
  const [isLogsExpanded, setIsLogsExpanded] = useState(true);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const logsContainerRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const wsRef = useRef<WebSocket | null>(null);
  const heartbeatRef = useRef<number | null>(null);

  // Configuration tooltips
  const configTooltips = useMemo(() => ({
    llm_model: 'Choose the language model: Gemini models (fast & latest from Google), GPT models (powerful OpenAI models), or o1 models (advanced reasoning)',
    embedding_model: 'Choose embedding model: Google (768 dim), OpenAI Large (3072 dim - most capable), Small (1536 dim - balanced)',
    qdrant_index_name: 'Name of the Qdrant vector database collection to use for storing and retrieving resume embeddings',
    chunk_size: 'Size of text chunks for processing (minimum 50). Larger chunks provide more context but use more tokens.',
    chunk_overlap: 'Overlap between chunks (minimum 0). Higher overlap ensures better continuity but increases processing time.',
    similarity_top_k: 'Number of similar chunks to retrieve (1-20). More chunks provide better coverage but may include noise.',
    min_confidence_threshold: 'Minimum confidence score threshold (0.0-1.0). Higher values filter out uncertain responses.',
    llm_temperature: 'Creativity level (0.0-1.0). Lower values are more deterministic, higher values are more creative.'
  }), []);

  // Scroll to bottom of logs when new logs are added
  useEffect(() => {
    if (logsEndRef.current && isLogsExpanded && autoScroll && logs.length > 0) {
      // Use setTimeout to ensure DOM is updated
      setTimeout(() => {
        if (logsEndRef.current) {
          logsEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }
      }, 100);
    }
  }, [logs.length, isLogsExpanded, autoScroll]); // Only depend on logs.length, not the entire logs array

  // WebSocket connection for real-time logs
  const connectWebSocket = (sessionId: string): void => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    // Clear any existing heartbeat
    if (heartbeatRef.current) {
      clearInterval(heartbeatRef.current);
      heartbeatRef.current = null;
    }

    console.log(`Attempting to connect to WebSocket: ws://localhost:8000/ws/${sessionId}`);
    const ws: WebSocket = new WebSocket(`ws://localhost:8000/ws/${sessionId}`);
    
    ws.onopen = (): void => {
      console.log('WebSocket connected successfully');
      // Send a heartbeat every 30 seconds to keep connection alive
      const heartbeat: number = window.setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send('ping');
        } else {
          clearInterval(heartbeat);
          heartbeatRef.current = null;
        }
      }, 30000);
      
      // Store heartbeat interval for cleanup
      heartbeatRef.current = heartbeat;
    };

    interface WebSocketLogData {
      message: string;
      timestamp?: string;
    }

    interface WebSocketMessage {
      type: string;
      data: WebSocketLogData;
    }
    
    ws.onmessage = (event: MessageEvent): void => {
      try {
        const data: WebSocketMessage = JSON.parse(event.data);
        console.log('WebSocket message received:', data);
        
        // Handle different types of messages
        if (data.type === 'workflow_log' || data.type === 'log') {
          const logData: WebSocketLogData = data.data;
          addWorkflowLog(logData.message, logData.timestamp);
        }
      } catch (error: unknown) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };
    
    ws.onclose = (event: CloseEvent): void => {
      console.log('WebSocket disconnected', event.code, event.reason);
      if (heartbeatRef.current) {
        clearInterval(heartbeatRef.current);
        heartbeatRef.current = null;
      }
    };
    
    ws.onerror = (error: Event): void => {
      console.error('WebSocket error:', error);
      if (heartbeatRef.current) {
        clearInterval(heartbeatRef.current);
        heartbeatRef.current = null;
      }
    };
    
    wsRef.current = ws;
  };

  // Cleanup WebSocket and polling on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (heartbeatRef.current) {
        clearInterval(heartbeatRef.current);
        heartbeatRef.current = null;
      }
      if (activePollingInterval) {
        clearInterval(activePollingInterval);
      }
    };
  }, [activePollingInterval]);

  // Add workflow log entry (only from LogEvents)
  const addWorkflowLog = (message: string, timestamp?: string) => {
    const logTimestamp = timestamp || new Date().toISOString();
    const logId = `${logTimestamp}-${message.substring(0, 50)}`;
    
    setLogs(prev => {
      // Check if this log already exists to prevent duplicates
      const exists = prev.some(log => log.id === logId);
      if (exists) {
        return prev;
      }
      
      const newLog = {
        id: logId,
        timestamp: new Date(logTimestamp).toLocaleTimeString(),
        level: 'info',
        message,
        step: 'workflow'
      };
      
      return [...prev, newLog];
    });
  };

  // Create session
  const createSession = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });
      
      if (!response.ok) throw new Error('Failed to create session');
      
      const data = await response.json();
      setSessionId(data.session_id);
      
      // Delay WebSocket connection slightly to ensure session is fully initialized
      setTimeout(() => {
        connectWebSocket(data.session_id);
      }, 100);
      
      return data.session_id;
    } catch (error) {
      console.error('Failed to create session:', error);
      throw error;
    }
  };

  // Upload files
  const uploadFiles = async (sessionId: string) => {
    try {
      if (!resumeFile || !applicationFile) {
        throw new Error('Files are missing');
      }
      
      const formData = new FormData();
      formData.append('resume', resumeFile);
      formData.append('application_form', applicationFile);
      
      const response = await fetch(`${API_BASE_URL}/api/sessions/${sessionId}/upload`, {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) throw new Error('Failed to upload files');
      
    } catch (error: any) {
      console.error('Failed to upload files:', error);
      throw error;
    }
  };

  // Start workflow
  const startWorkflow = async (sessionId: string): Promise<void> => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/sessions/${sessionId}/start`, {
        method: 'POST'
      });
      
      if (!response.ok) throw new Error('Failed to start workflow');
      
      setCurrentStep('processing');
    } catch (error) {
      console.error('Failed to start workflow:', error);
      throw error;
    }
  };

// Poll for results
  const pollForResults = useCallback(async (sessionId: string) => {
    // Clear any existing polling interval
    if (activePollingInterval) {
      clearInterval(activePollingInterval);
      setActivePollingInterval(null);
    }
    
    let pollCount = 0;
    const maxPolls = 150; // 5 minutes with 2-second intervals
    
    const poll = async () => {
      try {
        pollCount++;
        const response = await fetch(`${API_BASE_URL}/api/sessions/${sessionId}/status`);
        const data = await response.json();
        
        console.log("Polling response:", data);
        
        // Update logs if they exist in the response
        if (data.logs && Array.isArray(data.logs)) {
            interface LogFromBackend {
            timestamp: string;
            message: string;
            level: string;
            step?: string;
            }

            interface FormattedLog {
            id: string;
            timestamp: string;
            level: string;
            message: string;
            step?: string;
            }

            const newLogs: FormattedLog[] = (data.logs as LogFromBackend[]).map(log => ({
            id: `${log.timestamp}-${log.message.substring(0, 50)}`,
            timestamp: new Date(log.timestamp).toLocaleTimeString(),
            level: log.level,
            message: log.message,
            step: log.step
            }));
          
          setLogs(currentLogs => {
            const existingIds = new Set(currentLogs.map(log => log.id));
            const logsToAdd = newLogs.filter(log => !existingIds.has(log.id));
            
            if (logsToAdd.length > 0) {
              return [...currentLogs, ...logsToAdd];
            }
            return currentLogs;
          });
        }
        
        if (data.status === 'awaiting_review' && data.results) {
          const parsedResults = parseWorkflowResults(data.results);
          console.log("Parsed Results:", parsedResults);
          setResults(parsedResults);
          setCurrentStep('review');
          setIsProcessing(false);
          setFeedbackSubmitted(false);
          
          if (activePollingInterval) {
            clearInterval(activePollingInterval);
            setActivePollingInterval(null);
          }
          return;
        } else if (data.status === 'completed' && data.results) {
          const parsedResults = parseWorkflowResults(data.results);
          console.log("Completed Results:", parsedResults);
          setResults(parsedResults);
          setCurrentStep('completed');
          setIsProcessing(false);
          
          if (activePollingInterval) {
            clearInterval(activePollingInterval);
            setActivePollingInterval(null);
          }
          return;
        } else if (data.status === 'failed') {
          setIsProcessing(false);
          
          if (activePollingInterval) {
            clearInterval(activePollingInterval);
            setActivePollingInterval(null);
          }
          
          setCurrentStep('upload');
          return;
        }
        
        if (pollCount >= maxPolls) {
          if (activePollingInterval) {
            clearInterval(activePollingInterval);
            setActivePollingInterval(null);
          }
          setIsProcessing(false);
          return;
        }
        
      } catch (error: any) {
        console.error('Polling error:', error);
      }
    };
    
    await poll();
    const newInterval = window.setInterval(poll, 2000);
    setActivePollingInterval(newInterval);
  }, [activePollingInterval]);

  // Cleanup WebSocket and polling on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (heartbeatRef.current) {
        clearInterval(heartbeatRef.current);
        heartbeatRef.current = null;
      }
      if (activePollingInterval) {
        clearInterval(activePollingInterval);
      }
    };
  }, [activePollingInterval]);

  // Parse workflow results from the structured or formatted text output
  const parseWorkflowResults = (resultsData: any) => {
    if (!resultsData) return null;
    
    // If it's already parsed (has fields array), return as is
    if (resultsData.fields) {
      return resultsData;
    }
    
    // If it's a direct array of structured objects (new format from backend)
    if (Array.isArray(resultsData)) {
      return {
        status: 'awaiting_review',
        fields: resultsData,
        raw_result: JSON.stringify(resultsData, null, 2)
      };
    }
    
    // If it's raw text from the workflow, parse it
    const rawText = resultsData.raw_result || resultsData.final_result || resultsData;
    if (typeof rawText !== 'string') return resultsData;
    
    const fields: Array<{
      name: string;
      response: string;
      confidence: string;
      confidence_score: number;
      confidence_scores: number[];
      confidence_indicator: string;
    }> = [];
    const lines = rawText.split('\n');
    let currentField: string | null = null;
    let currentResponse: string[] = [];
    let currentConfidence = 'medium';
    
    for (let line of lines) {
      // Match field headers like "**1. Field Name**✅ (confidence: 0.85)"
      const fieldMatch = line.match(/^\*\*\d+\.\s*(.+?)\*\*([✅⚠️❌❓]?)\s*(?:\(confidence:\s*([\d.]+)\))?/);
      
      if (fieldMatch) {
        // Save previous field
        if (currentField) {
          const confidenceScore = currentConfidence === 'high' ? 0.85 : currentConfidence === 'medium' ? 0.65 : 0.45;
          fields.push({
            name: currentField,
            response: currentResponse.join('\n').trim(),
            confidence: currentConfidence,
            confidence_score: confidenceScore,
            confidence_scores: [confidenceScore],
            confidence_indicator: currentConfidence === 'high' ? '✅' : currentConfidence === 'medium' ? '⚠️' : '❌'
          });
        }
        
        // Start new field
        currentField = fieldMatch[1].trim();
        currentResponse = [];
        
        // Determine confidence from icon or score
        const icon = fieldMatch[2];
        const score = fieldMatch[3] ? parseFloat(fieldMatch[3]) : null;
        
        if (score !== null) {
          currentConfidence = score >= 0.8 ? 'high' : score >= 0.6 ? 'medium' : 'low';
        } else if (icon === '✅') {
          currentConfidence = 'high';
        } else if (icon === '⚠️') {
          currentConfidence = 'medium';
        } else if (icon === '❌') {
          currentConfidence = 'low';
        }
      } else if (line.trim() && !line.startsWith('-') && currentField) {
        // Add to current response if it's not a separator line
        if (!line.match(/^-+$/)) {
          currentResponse.push(line);
        }
      }
    }
    
    // Save last field
    if (currentField) {
      const confidenceScore = currentConfidence === 'high' ? 0.85 : currentConfidence === 'medium' ? 0.65 : 0.45;
      fields.push({
        name: currentField,
        response: currentResponse.join('\n').trim(),
        confidence: currentConfidence,
        confidence_score: confidenceScore,
        confidence_scores: [confidenceScore],
        confidence_indicator: currentConfidence === 'high' ? '✅' : currentConfidence === 'medium' ? '⚠️' : '❌'
      });
    }
    
    return {
      status: 'awaiting_review',
      fields: fields,
      raw_result: rawText
    };
  };

  // Handle workflow execution
  const handleExecuteWorkflow = useCallback(async () => {
    if (!resumeFile || !applicationFile) {
      console.error('Please upload both resume and application form');
      return;
    }
    
    setIsProcessing(true);
    
    try {
      const sessionId = await createSession();
      await uploadFiles(sessionId);
      await startWorkflow(sessionId);
      
      // Start polling for results
      if (sessionId) {
        pollForResults(sessionId);
      }
    } catch (error) {
      setIsProcessing(false);
      console.error('Workflow execution failed');
    }
  }, [config, resumeFile, applicationFile, createSession, uploadFiles, startWorkflow, pollForResults, connectWebSocket]);

  // Submit feedback or approval
  const submitFeedbackOrApproval = useCallback(async (isApproval = false) => {
    if (!sessionId) {
      console.error('No active session');
      return;
    }
    
    setIsProcessing(true);
    setFeedbackSubmitted(true);
    
    try {
      if (isApproval) {
        // Submit approval (empty feedback indicates approval)
        const response = await fetch(`${API_BASE_URL}/api/sessions/${sessionId}/feedback`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: sessionId,
            feedbacks: [] // Empty feedbacks array indicates approval
          })
        });
        
        if (!response.ok) throw new Error('Failed to submit approval');

        // Don't optimistically jump to 'completed'. The backend still has to
        // finalize: run the workflow to StopEvent, generate the PDF, and upload
        // it to Google Drive. Poll until the backend reports 'completed' so the
        // UI reflects the real result (and the Drive upload actually happens).
        setCurrentStep('processing');
        if (sessionId) {
          pollForResults(sessionId);
        }
      } else {
        // Submit feedback for modifications
        if (!feedback.trim() || selectedFields.length === 0) {
          console.error('Please select fields and provide feedback');
          setIsProcessing(false);
          setFeedbackSubmitted(false);
          return;
        }
        
        const feedbackData = {
          session_id: sessionId,
          feedbacks: selectedFields.map(field => ({
            field,
            feedback: feedback.trim()
          }))
        };
        
        const response = await fetch(`${API_BASE_URL}/api/sessions/${sessionId}/feedback`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(feedbackData)
        });
        
        if (!response.ok) throw new Error('Failed to submit feedback');
        
        setFeedback('');
        setSelectedFields([]);
        setCurrentStep('processing');
        
        // Poll for updated results
        if (sessionId) {
          pollForResults(sessionId);
        }
      }
    } catch (error: any) {
      setIsProcessing(false);
      setFeedbackSubmitted(false);
      console.error(`Operation failed: ${error.message}`);
    }
  }, [sessionId, feedback, selectedFields, setCurrentStep, setIsProcessing, setFeedbackSubmitted]);

  // File upload component
  const FileUpload = ({ label, file, setFile, accept, icon: Icon }: { label: string; file: File | null; setFile: (f: File) => void; accept: string; icon: React.ElementType }) => (
    <div className="relative">
      <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-gray-300 border-dashed rounded-lg cursor-pointer bg-gray-50 hover:bg-gray-100 transition-colors">
        <div className="flex flex-col items-center justify-center pt-5 pb-6">
          <Icon className="w-8 h-8 mb-4 text-gray-500" />
          <p className="mb-2 text-sm text-gray-500">
            <span className="font-semibold">{file ? file.name : `Upload ${label}`}</span>
          </p>
          <p className="text-xs text-gray-500">PDF, DOC, DOCX</p>
        </div>
        <input
          type="file"
          className="hidden"
          accept={accept}
          onChange={(e) => {
            const files = e.target.files;
            if (files && files.length > 0) {
              setFile(files[0]);
            }
          }}
        />
      </label>
      {file && (
        <div className="absolute top-2 right-2">
          <CheckCircle className="w-5 h-5 text-green-500" />
        </div>
      )}
    </div>
  );

  

  // Results UI is provided by top-level ResultsDisplay component
  // Feedback UI is provided by top-level FeedbackInput component

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div 
              className="flex items-center cursor-pointer" 
              onClick={() => {
                setCurrentStep('upload');
                setSessionId(null);
                setIsProcessing(false);
                setResults(null);
                setFeedback('');
                setSelectedFields([]);
                setLogs([]);
                setResumeFile(null);
                setApplicationFile(null);
                if (wsRef.current) wsRef.current.close();
                if (activePollingInterval) {
                  clearInterval(activePollingInterval);
                  setActivePollingInterval(null);
                }
              }}
            >
              <Brain className="w-8 h-8 text-blue-600 mr-3" />
              <h1 className="text-xl font-semibold text-gray-900 hover:text-blue-600 transition-colors">
                AI Resume Matcher
              </h1>
            </div>
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-500">Step:</span>
              <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm">
                {currentStep === 'upload' && 'Upload & Configure'}
                {currentStep === 'processing' && 'Processing'}
                {currentStep === 'review' && 'Review Results'}
                {currentStep === 'completed' && 'Completed'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Upload and Configuration Step */}
        {currentStep === 'upload' && (
          <div>
            {/* File Upload */}
            <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
              <h2 className="text-lg font-semibold mb-6">Upload Documents</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <FileUpload
                  label="Resume"
                  file={resumeFile}
                  setFile={setResumeFile}
                  accept=".pdf,.doc,.docx"
                  icon={FileText}
                />
                <FileUpload
                  label="Application Form"
                  file={applicationFile}
                  setFile={setApplicationFile}
                  accept=".pdf,.doc,.docx"
                  icon={Upload}
                />
              </div>
            </div>

            {/* Configuration Panel */}
            <ConfigPanel config={config} setConfig={setConfig} tooltips={configTooltips} />

            {/* Execute Button */}
            <div className="flex justify-center">
              <button
                onClick={handleExecuteWorkflow}
                disabled={!resumeFile || !applicationFile || isProcessing}
                className="flex items-center px-8 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg hover:from-blue-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed text-lg font-medium shadow-lg"
              >
                {isProcessing ? (
                  <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                ) : (
                  <Play className="w-5 h-5 mr-2" />
                )}
                Start Processing
              </button>
            </div>
          </div>
        )}

        {/* Processing Step */}
        {currentStep === 'processing' && (
          <div className="text-center py-12">
            <Loader2 className="w-16 h-16 animate-spin mx-auto mb-4 text-blue-600" />
            <h2 className="text-2xl font-semibold text-gray-900 mb-2">
              Processing Your Documents
            </h2>
            <p className="text-gray-600">
              Our AI is analyzing your resume and matching it to the application form...
            </p>
          </div>
        )}

        {/* Review Results Step */}
        {(currentStep === 'review' || currentStep === 'completed') && results && (
          <div className="space-y-6">
            <ResultsDisplay 
              results={results} 
              selectedFields={selectedFields}
              setSelectedFields={(updater) => setSelectedFields(updater as any)}
            />
            {currentStep === 'review' && (
              <FeedbackInput 
                feedback={feedback}
                setFeedback={(v) => setFeedback(v)}
                selectedFields={selectedFields}
                setSelectedFields={(updater) => setSelectedFields(updater as any)}
                isProcessing={isProcessing}
                onSubmit={(approve) => submitFeedbackOrApproval(approve)}
              />
            )}
            
            {currentStep === 'completed' && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-6">
                <div className="flex items-center">
                  <CheckCircle className="w-8 h-8 text-green-600 mr-4" />
                  <div>
                    <h2 className="text-xl font-semibold text-green-800 mb-1">
                      Workflow Completed Successfully!
                    </h2>
                    <p className="text-green-700">
                      Your application form has been completed using the AI-matched information from your resume. 
                      You can copy the results above to use in your job application.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Real-time Logs */}
        {sessionId && (
          <LogsPanel 
            logs={logs}
            isLogsExpanded={isLogsExpanded}
            setIsLogsExpanded={setIsLogsExpanded}
            autoScroll={autoScroll}
            setAutoScroll={setAutoScroll}
            logsEndRef={logsEndRef}
            logsContainerRef={logsContainerRef}
          />
        )}
      </div>
    </div>
  );
};

export default ResumeMatchingApp;

// {/* <ResumeMatchingApp.tsx> */}
