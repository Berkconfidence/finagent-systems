import React, { useEffect, useReducer, useRef, useState } from 'react';
import { Activity, CheckCircle, Clock, AlertTriangle, UserCheck, XCircle } from 'lucide-react';
import { cancelAnalysis, connectAnalysisEvents, getAgentStatus, submitHitlDecision, type AnalysisSseEvent } from '../api';
import ReportModal from './ReportModal';

interface StatusDashboardProps {
  threadId: string;
}

type GraphNodeId =
  | 'START'
  | 'orchestrator'
  | 'financial_agent'
  | 'market_agent'
  | 'risk_auditor_agent'
  | 'END';

type BackendStatus = 'running' | 'interrupted' | 'completed' | 'failed' | 'canceled' | 'pending' | 'unknown';
type UiPhase =
  | 'idle'
  | 'connecting'
  | 'running'
  | 'interrupted'
  | 'submitting_approval'
  | 'awaiting_resume'
  | 'completed'
  | 'canceled'
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
    case 'canceled':
      return 'canceled';
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
  const [canceling, setCanceling] = useState(false);
  const [reportOpen, setReportOpen] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const fallbackTimerRef = useRef<number | null>(null);
  const activityRef = useRef<HTMLDivElement | null>(null);

  const clearFallbackTimer = () => {
    if (fallbackTimerRef.current) {
      window.clearTimeout(fallbackTimerRef.current);
      fallbackTimerRef.current = null;
    }
  };

  useEffect(() => {
    dispatch({ type: 'THREAD_RESET' });
    setReportOpen(false);
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

        if (response.status === 'completed' || response.status === 'failed' || response.status === 'canceled') {
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
        if (event.type === 'end' || status === 'completed' || status === 'failed' || status === 'canceled') {
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

  const activityLog: string[] = Array.isArray(state.data?.activity_log) ? state.data.activity_log : [];

  useEffect(() => {
    if (activityRef.current) {
      activityRef.current.scrollTop = activityRef.current.scrollHeight;
    }
  }, [activityLog.length]);

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

  const handleCancelAnalysis = async () => {
    setCanceling(true);
    try {
      await cancelAnalysis(threadId);
      dispatch({
        type: 'SSE_STATUS',
        payload: {
          ...(state.data || {}),
          thread_id: threadId,
          status: 'canceled',
          is_interrupted: false,
          pending_node: null,
          state: {
            ...(state.data?.state || {}),
            credit_decision: 'CANCELED',
            final_report: state.data?.state?.final_report || 'Analiz kullanıcı tarafından iptal edildi.',
          },
        },
      });
    } catch (err) {
      console.error('İptal isteği sırasında hata:', err);
      const message = err instanceof Error ? err.message : 'İptal isteği gönderilemedi';
      dispatch({ type: 'SSE_ERROR', payload: message });
    } finally {
      setCanceling(false);
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
    canceled: 'CANCELED',
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
      case 'canceled':
        return <XCircle className="text-red-500" />;
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
      case 'canceled': return 'bg-red-100 text-red-800 border-red-200';
      case 'interrupted': return 'bg-orange-100 text-orange-800 border-orange-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const isTerminal = ['completed', 'failed', 'canceled'].includes(String(displayStatus));
  const canOpenReport = displayStatus === 'completed' && !!state.data;

  const backendPendingNode = state.data?.pending_node as string | null | undefined;
  const stateNextNode = state.data?.state?.next_node as string | null | undefined;

  const resolveActiveNode = (): GraphNodeId => {
    if (displayStatus === 'completed' || displayStatus === 'failed' || displayStatus === 'canceled') {
      return 'END';
    }

    const candidate = backendPendingNode || stateNextNode;
    if (
      candidate === 'orchestrator' ||
      candidate === 'financial_agent' ||
      candidate === 'market_agent' ||
      candidate === 'risk_auditor_agent'
    ) {
      return candidate as GraphNodeId;
    }

    return 'START';
  };

  const activeNode = resolveActiveNode();

  const nodeClass = (nodeId: GraphNodeId) => {
    const base = 'px-4 py-2.5 rounded-xl border-2 text-xs font-bold text-center transition-all duration-500 shadow-sm min-w-[140px] relative bg-white';
    if (activeNode === nodeId) {
      return `${base} border-blue-500 text-blue-700 shadow-blue-100 shadow-lg transform scale-105 ring-4 ring-blue-50 z-20`;
    }
    return `${base} border-gray-200 text-gray-600 hover:border-gray-300 hover:shadow-md z-10`;
  };

  return (
    <div className="flex flex-col lg:flex-row gap-6 h-full items-start">
      
      {/* Left Column: Status Data, Logs, HITL, Errors */}
      <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200 flex-1 flex flex-col w-full lg:w-2/3 h-full">
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

        <div className="text-sm text-gray-500 mb-6 shrink-0">
          <div className="flex items-center justify-between gap-3">
            <span><span className="font-semibold text-gray-700">Thread ID:</span> {threadId}</span>
            {canOpenReport ? (
              <button
                type="button"
                onClick={() => setReportOpen(true)}
                className="text-xs px-3 py-1.5 rounded-full border border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100 transition"
              >
                Detaylı Nihai Raporu Aç
              </button>
            ) : !isTerminal && (
              <button
                onClick={handleCancelAnalysis}
                disabled={canceling || state.hitlDecisioning}
                className="text-xs px-3 py-1 rounded border border-red-200 text-red-700 hover:bg-red-50 disabled:opacity-50"
              >
                {canceling ? 'İptal ediliyor...' : 'Analizi İptal Et'}
              </button>
            )}
          </div>
        </div>

        {state.errorMessage && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4 text-sm text-red-700 shrink-0">
            {state.errorMessage}
          </div>
        )}

        {state.uiPhase === 'awaiting_resume' && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6 text-sm text-blue-800 shrink-0">
            Karar gönderildi. Arka planda agent devam etmesi bekleniyor...
          </div>
        )}

        {state.uiPhase === 'canceled' && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 text-sm text-red-800 shrink-0">
            Analiz kullanıcı tarafından iptal edildi.
          </div>
        )}

        {state.uiPhase === 'interrupted' && (
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-5 mb-6 shrink-0">
            <div className="flex items-start gap-3">
              <AlertTriangle className="text-orange-500 mt-1 shrink-0" />
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

        <div className="mb-4 bg-gray-50 rounded-md border border-gray-200 overflow-hidden flex flex-col shrink-0">
          <div className="bg-gray-100 px-4 py-2 text-xs font-semibold text-gray-500 border-b border-gray-200">
            Canlı Ajan Konsolu
          </div>
          <div
            ref={activityRef}
            className="p-3 h-40 overflow-auto font-mono text-xs text-gray-700 whitespace-pre-wrap"
          >
            {activityLog.length > 0
              ? activityLog.map((line, index) => <div key={`${index}-${line}`}>{line}</div>)
              : 'Ajan aktivitesi bekleniyor...'}
          </div>
        </div>

        <div className="flex-1 bg-gray-50 rounded-md border border-gray-200 overflow-hidden flex flex-col">
          <div className="bg-gray-100 px-4 py-2 text-xs font-semibold text-gray-500 border-b border-gray-200">
            State Dump
          </div>
          <div className="p-4 overflow-auto flex-1 font-mono text-sm text-gray-700 whitespace-pre-wrap max-h-96 min-h-[150px]">
            {state.data ? JSON.stringify(state.data, null, 2) : "Canlı veriler bekleniyor..."}
          </div>
        </div>
      </div>

      {/* Right Column: Workflow Map */}
      <div className="w-full lg:w-2/5 shrink-0">
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm flex flex-col h-full">
          <div className="bg-gradient-to-r from-gray-50 to-gray-100 px-5 py-3 text-xs font-semibold text-gray-600 border-b border-gray-200 flex items-center justify-between shrink-0">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-blue-500" />
              Grafiksel Süreç Haritası
            </div>
            <span className="text-[10px] text-gray-400 font-mono font-normal">Workflow Map</span>
          </div>

          <div className="py-8 bg-gray-50/30 flex flex-col items-center relative overflow-x-auto shrink-0 min-h-[450px]">
            
            {/* START Node */}
            <div className={nodeClass('START')}>
              BAŞLANGIÇ
              <span className="font-mono text-[9px] text-gray-400 mt-1 block font-normal">START</span>
            </div>
            
            <div className="w-px h-8 bg-gray-300 relative">
              <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-px border-solid border-t-gray-300 border-t-[5px] border-x-transparent border-x-[4px] border-b-0"></div>
            </div>

            {/* Orchestrator Node */}
            <div className={`${nodeClass('orchestrator')} bg-amber-50/50`}>
              Orkestratör
              <span className="font-mono text-[9px] text-gray-400 mt-1 block font-normal">orchestrator</span>
            </div>

            {/* Fork into two paths */}
            <div className="w-px h-6 bg-gray-300 relative"></div>
            <div className="w-64 h-px bg-gray-300 relative">
               <div className="absolute top-0 left-0 w-px h-6 bg-gray-300 -translate-x-px">
                  <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-px border-solid border-t-gray-300 border-t-[5px] border-x-transparent border-x-[4px] border-b-0"></div>
               </div>
               <div className="absolute top-0 right-0 w-px h-6 bg-gray-300 translate-x-px">
                  <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-px border-solid border-t-gray-300 border-t-[5px] border-x-transparent border-x-[4px] border-b-0"></div>
               </div>
            </div>
            
            {/* Parallel Nodes */}
            <div className="flex gap-[114px] mt-6 relative z-10">
              <div className={`${nodeClass('financial_agent')} bg-blue-50/50`}>
                Finans Ajanı
                <span className="font-mono text-[9px] text-gray-400 mt-1 block font-normal">financial_agent</span>
              </div>
              <div className={`${nodeClass('market_agent')} bg-blue-50/50`}>
                Piyasa Ajanı
                <span className="font-mono text-[9px] text-gray-400 mt-1 block font-normal">market_agent</span>
              </div>
            </div>

            {/* Merge from two paths */}
            <div className="w-64 flex justify-between relative mt-px">
               <div className="w-px h-6 bg-gray-300"></div>
               <div className="w-px h-6 bg-gray-300"></div>
            </div>
            <div className="w-64 h-px bg-gray-300 relative">
               <div className="absolute top-0 left-1/2 -translate-x-1/2 w-px h-8 bg-gray-300">
                  <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-px border-solid border-t-gray-300 border-t-[5px] border-x-transparent border-x-[4px] border-b-0"></div>
               </div>
            </div>

            {/* Risk Auditor Node */}
            <div className="relative mt-8">
              <div className={`${nodeClass('risk_auditor_agent')} bg-red-50/50`}>
                Risk Denetimi
                <span className="font-mono text-[9px] text-gray-400 mt-1 block font-normal">risk_auditor_agent</span>
              </div>
               
               {/* Loopback Arrow to Orchestrator */}
               <div className="absolute top-1/2 -left-[14px] w-[50px] h-[190px] border-l-[1.5px] border-t-[1.5px] border-b-[1.5px] border-orange-400 border-dashed rounded-l-2xl -translate-y-full opacity-60 pointer-events-none">
                  <div className="absolute top-1/2 -left-1 -translate-x-full -translate-y-1/2 text-[9px] font-bold text-orange-500 whitespace-nowrap bg-white/90 px-1.5 py-0.5 rounded shadow-sm border border-orange-100">
                    REVISION
                  </div>
                  {/* Arrow pointing to orchestrator */}
                  <div className="absolute top-0 right-[-1px] translate-x-1/2 -translate-y-[4.5px] border-solid border-l-orange-400 border-l-[6px] border-y-transparent border-y-[5px] border-r-0"></div>
               </div>
            </div>

            {/* To End */}
            <div className="w-px h-10 bg-gray-300 relative">
              <div className="absolute top-1/2 left-3 text-[9px] font-bold text-green-600 whitespace-nowrap bg-white/90 px-1.5 py-0.5 rounded shadow-sm border border-green-100 w-max -translate-y-1/2">
                 APPROVED / CANCELED
              </div>
              <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-px border-solid border-t-gray-300 border-t-[5px] border-x-transparent border-x-[4px] border-b-0"></div>
            </div>

            {/* END Node */}
            <div className={nodeClass('END')}>
               BİTİŞ
               <span className="font-mono text-[9px] text-gray-400 mt-1 block font-normal">END</span>
            </div>

          </div>
        </div>
      </div>

      <ReportModal
        isOpen={reportOpen}
        onClose={() => setReportOpen(false)}
        reportData={state.data}
      />
    </div>
  );
};

export default StatusDashboard;