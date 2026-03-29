import React, { useEffect, useReducer, useRef } from 'react';
import { Activity, CheckCircle, Clock, AlertTriangle, UserCheck } from 'lucide-react';
import { connectAnalysisEvents, getAgentStatus, submitHitlDecision, type AnalysisSseEvent } from '../api';

interface StatusDashboardProps {
  threadId: string;
}

type BackendStatus = 'running' | 'interrupted' | 'completed' | 'failed' | 'pending' | 'unknown';
type UiPhase =
  | 'idle'
  | 'connecting'
  | 'running'
  | 'interrupted'
  | 'submitting_approval'
  | 'awaiting_resume'
  | 'completed'
  | 'failed'
  | 'error';

interface DashboardState {
  uiPhase: UiPhase;
  backendStatus: BackendStatus;
  data: any;
  hitlDecisioning: boolean;
  isLive: boolean;
  errorMessage: string | null;
  awaitingResumeSince: number | null;
}

type DashboardAction =
  | { type: 'THREAD_RESET' }
  | { type: 'SSE_CONNECTED' }
  | { type: 'SSE_STATUS'; payload: any }
  | { type: 'SSE_ERROR'; payload?: string }
  | { type: 'APPROVAL_SUBMITTING' }
  | { type: 'APPROVAL_ACCEPTED' }
  | { type: 'APPROVAL_FAILED'; payload: string }
  | { type: 'FORCE_INTERRUPT_RESTORE' };

const initialState: DashboardState = {
  uiPhase: 'idle',
  backendStatus: 'unknown',
  data: null,
  hitlDecisioning: false,
  isLive: false,
  errorMessage: null,
  awaitingResumeSince: null,
};

const mapBackendStatusToUi = (status: BackendStatus): UiPhase => {
  switch (status) {
    case 'running':
    case 'pending':
      return 'running';
    case 'interrupted':
      return 'interrupted';
    case 'completed':
      return 'completed';
    case 'failed':
      return 'failed';
    default:
      return 'connecting';
  }
};

const reducer = (state: DashboardState, action: DashboardAction): DashboardState => {
  switch (action.type) {
    case 'THREAD_RESET':
      return { ...initialState, uiPhase: 'connecting' };

    case 'SSE_CONNECTED':
      return {
        ...state,
        uiPhase: state.uiPhase === 'idle' ? 'connecting' : state.uiPhase,
        isLive: true,
        errorMessage: null,
      };

    case 'SSE_STATUS': {
      const nextBackendStatus = (action.payload?.status ?? 'unknown') as BackendStatus;

      if (state.uiPhase === 'awaiting_resume' && nextBackendStatus === 'interrupted') {
        return {
          ...state,
          data: action.payload,
          backendStatus: nextBackendStatus,
          isLive: true,
        };
      }

      return {
        ...state,
        data: action.payload,
        backendStatus: nextBackendStatus,
        uiPhase: mapBackendStatusToUi(nextBackendStatus),
        hitlDecisioning: false,
        isLive: true,
        errorMessage: null,
        awaitingResumeSince: null,
      };
    }

    case 'SSE_ERROR':
      return {
        ...state,
        isLive: false,
        errorMessage: action.payload ?? 'Canlı bağlantı kesildi. Fallback duruma geçiliyor.',
      };

    case 'APPROVAL_SUBMITTING':
      return {
        ...state,
        hitlDecisioning: true,
        uiPhase: 'submitting_approval',
        errorMessage: null,
      };

    case 'APPROVAL_ACCEPTED':
      return {
        ...state,
        hitlDecisioning: false,
        uiPhase: 'awaiting_resume',
        awaitingResumeSince: Date.now(),
        errorMessage: null,
      };

    case 'APPROVAL_FAILED':
      return {
        ...state,
        hitlDecisioning: false,
        uiPhase: 'interrupted',
        errorMessage: action.payload,
        awaitingResumeSince: null,
      };

    case 'FORCE_INTERRUPT_RESTORE':
      return {
        ...state,
        uiPhase: 'interrupted',
        hitlDecisioning: false,
        awaitingResumeSince: null,
      };

    default:
      return state;
  }
};

const StatusDashboard: React.FC<StatusDashboardProps> = ({ threadId }) => {
  const [state, dispatch] = useReducer(reducer, initialState);
  const eventSourceRef = useRef<EventSource | null>(null);
  const fallbackTimerRef = useRef<number | null>(null);

  const clearFallbackTimer = () => {
    if (fallbackTimerRef.current) {
      window.clearTimeout(fallbackTimerRef.current);
      fallbackTimerRef.current = null;
    }
  };

  useEffect(() => {
    dispatch({ type: 'THREAD_RESET' });
  }, [threadId]);

  useEffect(() => {
    if (!threadId) return;

    let fallbackAttempt = 0;
    let isDisposed = false;
    let hasTerminalStatus = false;

    const fallbackPoll = async () => {
      try {
        fallbackAttempt += 1;
        const response = await getAgentStatus(threadId);
        dispatch({ type: 'SSE_STATUS', payload: response });

        if (response.status === 'completed' || response.status === 'failed') {
          return;
        }

        const delay = Math.min(6000, 1200 + fallbackAttempt * 600);
        fallbackTimerRef.current = window.setTimeout(fallbackPoll, delay);
      } catch (error) {
        console.error('Fallback polling hatası:', error);
        fallbackTimerRef.current = window.setTimeout(fallbackPoll, 3000);
      }
    };

    const onEvent = (event: AnalysisSseEvent) => {
      if (event.type === 'heartbeat') {
        return;
      }

      if (event.type === 'error') {
        if (hasTerminalStatus || isDisposed) {
          return;
        }
        dispatch({ type: 'SSE_ERROR', payload: event.data?.detail ?? 'SSE stream hatası' });
        return;
      }

      if (event.type === 'snapshot' || event.type === 'status_update' || event.type === 'end') {
        const status = event.data?.status;
        if (event.type === 'end' || status === 'completed' || status === 'failed') {
          hasTerminalStatus = true;
        }
        dispatch({ type: 'SSE_STATUS', payload: event.data });
      }
    };

    clearFallbackTimer();
    eventSourceRef.current?.close();
    const es = connectAnalysisEvents(
      threadId,
      onEvent,
      () => {
        if (hasTerminalStatus || isDisposed) {
          return;
        }
        dispatch({ type: 'SSE_ERROR' });
        if (!fallbackTimerRef.current) {
          fallbackTimerRef.current = window.setTimeout(fallbackPoll, 1500);
        }
      }
    );

    eventSourceRef.current = es;
    dispatch({ type: 'SSE_CONNECTED' });

    return () => {
      isDisposed = true;
      es.close();
      clearFallbackTimer();
    };
  }, [threadId]);

  useEffect(() => {
    if (state.uiPhase !== 'awaiting_resume' || !state.awaitingResumeSince) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      if (state.backendStatus === 'interrupted') {
        dispatch({ type: 'FORCE_INTERRUPT_RESTORE' });
      }
    }, 12000);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [state.uiPhase, state.awaitingResumeSince, state.backendStatus]);

  const handleHitlDecision = async (decision: "approved" | "rejected") => {
    dispatch({ type: 'APPROVAL_SUBMITTING' });

    try {
      await submitHitlDecision(threadId, {
        is_approved: decision === 'approved'
      });
      dispatch({ type: 'APPROVAL_ACCEPTED' });
    } catch (err) {
      console.error('Hitl kararı gönderilirken hata:', err);
      const message = err instanceof Error ? err.message : 'Bilinmeyen hata oluştu';
      dispatch({ type: 'APPROVAL_FAILED', payload: message });
    }
  };

  const displayStatus =
    state.uiPhase === 'submitting_approval' || state.uiPhase === 'awaiting_resume'
      ? 'running'
      : state.backendStatus;

  const statusTextMap: Record<string, string> = {
    running: 'RUNNING',
    pending: 'PENDING',
    interrupted: 'INTERRUPTED',
    completed: 'COMPLETED',
    failed: 'FAILED',
    unknown: 'UNKNOWN',
  };

  const getStatusIcon = () => {
    switch (displayStatus) {
      case 'running':
      case 'pending':
        return <Activity className="text-blue-500 animate-spin" />;
      case 'completed':
        return <CheckCircle className="text-green-500" />;
      case 'interrupted':
        return <UserCheck className="text-orange-500 animate-bounce" />;
      default:
        return <Clock className="text-gray-500" />;
    }
  };

  const getStatusColor = () => {
    switch (displayStatus) {
      case 'running':
      case 'pending': return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'completed': return 'bg-green-100 text-green-800 border-green-200';
      case 'interrupted': return 'bg-orange-100 text-orange-800 border-orange-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4 border-b pb-4">
        <h2 className="text-xl font-semibold text-gray-800 flex items-center gap-2">
          {getStatusIcon()}
          Durum Monitörü
        </h2>
        
        <div className={`px-4 py-1.5 rounded-full border font-medium text-sm flex items-center gap-2 ${getStatusColor()}`}>
          {(state.isLive || state.uiPhase === 'awaiting_resume' || state.uiPhase === 'submitting_approval') && (
            <span className="w-2 h-2 rounded-full bg-current animate-ping"></span>
          )}
          {statusTextMap[displayStatus] ?? displayStatus.toUpperCase()}
        </div>
      </div>

      <div className="text-sm text-gray-500 mb-6">
        <span className="font-semibold text-gray-700">Thread ID:</span> {threadId}
      </div>

      {state.errorMessage && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4 text-sm text-red-700">
          {state.errorMessage}
        </div>
      )}

      {state.uiPhase === 'awaiting_resume' && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6 text-sm text-blue-800">
          Karar gönderildi. Arka planda agent devam etmesi bekleniyor...
        </div>
      )}

      {state.uiPhase === 'interrupted' && (
        <div className="bg-orange-50 border border-orange-200 rounded-lg p-5 mb-6">
          <div className="flex items-start gap-3">
            <AlertTriangle className="text-orange-500 mt-1" />
            <div>
              <h3 className="font-semibold text-orange-800 mb-1">Müdahale Gerekiyor (HITL)</h3>
              <p className="text-sm text-orange-700 mb-4">
                Ajan bir karar verebilmek için insan onayı bekliyor. Lütfen işlemi onaylayın ya da reddedin.
              </p>
              
              <div className="flex gap-3">
                <button 
                  onClick={() => handleHitlDecision('approved')}
                  disabled={state.hitlDecisioning}
                  className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-md font-medium transition disabled:opacity-50"
                >
                  Onayla
                </button>
                <button 
                  onClick={() => handleHitlDecision('rejected')}
                  disabled={state.hitlDecisioning}
                  className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-md font-medium transition disabled:opacity-50"
                >
                  Reddet
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="flex-1 bg-gray-50 rounded-md border border-gray-200 overflow-hidden flex flex-col">
        <div className="bg-gray-100 px-4 py-2 text-xs font-semibold text-gray-500 border-b border-gray-200">
          State Dump
        </div>
        <div className="p-4 overflow-auto flex-1 font-mono text-sm text-gray-700 whitespace-pre-wrap max-h-96">
          {state.data ? JSON.stringify(state.data, null, 2) : "Canlı veriler bekleniyor..."}
        </div>
      </div>
    </div>
  );
};

export default StatusDashboard;