import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface StartAnalysisRequest {
  company_name: string;
}

export interface StartAnalysisResponse {
  thread_id: string;
  message: string;
}

export interface HitlRequest {
  is_approved: boolean;
  note?: string;
}

export type AnalysisEventType = 'snapshot' | 'status_update' | 'heartbeat' | 'end' | 'error';

export interface AnalysisSseEvent<T = any> {
  type: AnalysisEventType;
  data: T;
}

export interface RecentAnalysisItem {
  thread_id: string;
  company_name: string;
  status: 'running' | 'interrupted' | 'completed' | 'failed' | 'canceled';
  is_interrupted: boolean;
  pending_node: string | null;
  last_checkpoint_id: string;
}

export interface RecentAnalysesResponse {
  count: number;
  items: RecentAnalysisItem[];
}

export const startAnalysis = async (data: StartAnalysisRequest) => {
  const response = await api.post<StartAnalysisResponse>('/api/v1/analysis/start', data);
  return response.data;
};

export const getAgentStatus = async (threadId: string) => {
  const response = await api.get(`/api/v1/analysis/${threadId}/status`, {
    params: { _: new Date().getTime() },
    headers: {
      'Cache-Control': 'no-cache',
      'Pragma': 'no-cache',
      'Expires': '0',
    }
  });
  return response.data;
};

export const getRecentAnalyses = async (limit = 10) => {
  const response = await api.get<RecentAnalysesResponse>('/api/v1/analysis/recent', {
    params: { limit },
  });
  return response.data;
};

export const submitHitlDecision = async (threadId: string, data: HitlRequest) => {
  const response = await api.post(`/api/v1/analysis/${threadId}/approve`, data);
  return response.data;
};

export const cancelAnalysis = async (threadId: string) => {
  const response = await api.post(`/api/v1/analysis/${threadId}/cancel`);
  return response.data;
};

export const connectAnalysisEvents = (
  threadId: string,
  onEvent: (event: AnalysisSseEvent) => void,
  onError?: (error: Event) => void
) => {
  const eventUrl = `${API_BASE_URL}/api/v1/analysis/${threadId}/events`;
  const eventSource = new EventSource(eventUrl);

  const bindEvent = (eventName: AnalysisEventType) => {
    eventSource.addEventListener(eventName, (event: MessageEvent) => {
      let parsed: any = {};
      try {
        parsed = event.data ? JSON.parse(event.data) : {};
      } catch {
        parsed = { raw: event.data };
      }

      onEvent({
        type: eventName,
        data: parsed,
      });
    });
  };

  bindEvent('snapshot');
  bindEvent('status_update');
  bindEvent('heartbeat');
  bindEvent('end');
  bindEvent('error');

  eventSource.onerror = (err) => {
    if (onError) {
      onError(err);
    }
  };

  return eventSource;
};

export default api;
