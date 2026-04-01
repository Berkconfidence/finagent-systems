import React, { useEffect, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { CheckCircle2, FileText, Landmark, LineChart, ShieldAlert, X } from 'lucide-react';

type ReportModalProps = {
  isOpen: boolean;
  onClose: () => void;
  reportData: any;
};

type MetricRow = {
  label: string;
  value: string;
  tone?: 'good' | 'warn' | 'bad' | 'neutral';
};

const toFiniteNumber = (value: unknown): number | null => {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
};

const formatMetricValue = (value: unknown) => {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'number' && Number.isFinite(value)) {
    return new Intl.NumberFormat('tr-TR', {
      maximumFractionDigits: 2,
    }).format(value);
  }
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
};

const getToneClasses = (tone: MetricRow['tone']) => {
  switch (tone) {
    case 'good':
      return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    case 'warn':
      return 'bg-amber-50 text-amber-700 border-amber-200';
    case 'bad':
      return 'bg-rose-50 text-rose-700 border-rose-200';
    default:
      return 'bg-gray-50 text-gray-700 border-gray-200';
  }
};

const getDecisionTone = (decision: string) => {
  const normalized = decision?.toUpperCase?.() ?? 'PENDING';
  if (normalized === 'APPROVED') return 'good';
  if (normalized === 'REJECTED') return 'bad';
  if (normalized === 'CANCELED') return 'neutral';
  return 'warn';
};

const getRiskProgressTone = (score: number | null) => {
  if (score === null) return 'bg-gray-300';
  if (score >= 70) return 'bg-rose-500';
  if (score >= 45) return 'bg-amber-500';
  return 'bg-emerald-500';
};

const ReportModal: React.FC<ReportModalProps> = ({ isOpen, onClose, reportData }) => {
  const reportState = reportData?.state ?? reportData ?? {};

  const derived = useMemo(() => {
    const financial = Array.isArray(reportState?.financial_kpis) ? reportState.financial_kpis[0] : null;
    const market = Array.isArray(reportState?.market_sentiment) ? reportState.market_sentiment[0] : null;
    const marketAnalysis = market?.market_analysis ?? {};

    const sectorRiskScore = toFiniteNumber(marketAnalysis?.sector_risk_score);

    const currentRatio = toFiniteNumber(financial?.liquidity_metrics?.current_ratio);
    const quickRatio = toFiniteNumber(financial?.liquidity_metrics?.quick_ratio);
    const debtToEquity = toFiniteNumber(financial?.leverage_and_debt?.debt_to_equity);
    const interestCoverage = toFiniteNumber(financial?.leverage_and_debt?.interest_coverage_ratio);
    const netProfit = toFiniteNumber(financial?.profitability_metrics?.net_profit);

    const metrics: MetricRow[] = [
      {
        label: 'Cari Oran',
        value: formatMetricValue(financial?.liquidity_metrics?.current_ratio),
        tone: currentRatio === null ? 'neutral' : currentRatio >= 1.2 ? 'good' : 'bad',
      },
      {
        label: 'Asit-Test Oranı',
        value: formatMetricValue(financial?.liquidity_metrics?.quick_ratio),
        tone: quickRatio === null ? 'neutral' : quickRatio >= 1 ? 'good' : 'warn',
      },
      {
        label: 'Debt / Equity',
        value: formatMetricValue(financial?.leverage_and_debt?.debt_to_equity),
        tone: debtToEquity === null ? 'neutral' : debtToEquity < 4 ? 'good' : 'bad',
      },
      {
        label: 'Faiz Karşılama',
        value: formatMetricValue(financial?.leverage_and_debt?.interest_coverage_ratio),
        tone: interestCoverage === null ? 'neutral' : interestCoverage > 1.5 ? 'good' : 'warn',
      },
      {
        label: 'Net Kar',
        value: formatMetricValue(financial?.profitability_metrics?.net_profit),
        tone: netProfit === null ? 'neutral' : netProfit >= 0 ? 'good' : 'bad',
      },
      {
        label: 'FAVÖK Marjı',
        value: formatMetricValue(financial?.profitability_metrics?.ebitda_margin),
        tone: 'neutral',
      },
    ];

    const marketRiskTone: MetricRow['tone'] =
      sectorRiskScore === null
        ? 'neutral'
        : sectorRiskScore >= 70
          ? 'bad'
          : sectorRiskScore >= 45
            ? 'warn'
            : 'good';

    return {
      financial,
      marketAnalysis,
      sectorRiskScore,
      metrics,
      marketRiskTone,
    };
  }, [reportState]);

  useEffect(() => {
    if (!isOpen) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', onKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen || typeof document === 'undefined') {
    return null;
  }

  const companyName = reportState?.company_name || reportData?.company_name || 'Bilinmeyen Şirket';
  const decision = String(reportState?.credit_decision || reportData?.credit_decision || 'PENDING').toUpperCase();
  const finalReport = reportState?.final_report || reportData?.final_report || 'Nihai rapor metni henüz oluşmadı.';
  const auditLog: string[] = Array.isArray(reportState?.audit_log) ? reportState.audit_log : [];
  const threadId = reportData?.thread_id || '—';
  const pendingNode = reportData?.pending_node || reportState?.next_node || 'END';
  const riskWidth = Math.max(0, Math.min(100, derived.sectorRiskScore ?? 0));

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="w-full max-w-6xl max-h-[90vh] overflow-hidden rounded-3xl bg-white shadow-2xl ring-1 ring-black/5"
        role="dialog"
        aria-modal="true"
        aria-labelledby="report-modal-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4 border-b border-gray-200 bg-gradient-to-r from-slate-50 to-white px-6 py-5">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-gray-500">
              <FileText className="h-4 w-4 text-blue-500" />
              Zengin Nihai Rapor
            </div>
            <h2 id="report-modal-title" className="mt-1 text-2xl font-bold text-gray-900">
              {companyName}
            </h2>
            <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-gray-500">
              <span className="rounded-full bg-gray-100 px-3 py-1 font-mono text-xs">Thread: {threadId}</span>
              <span className="rounded-full bg-gray-100 px-3 py-1 font-mono text-xs">Pending: {pendingNode}</span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className={`rounded-full border px-4 py-2 text-sm font-semibold ${getToneClasses(getDecisionTone(decision))}`}>
              {decision}
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded-full border border-gray-200 p-2 text-gray-500 transition hover:bg-gray-100 hover:text-gray-800"
              aria-label="Raporu kapat"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        <div className="max-h-[calc(90vh-90px)] overflow-y-auto bg-slate-50 px-6 py-6">
          <div className="space-y-6">
            <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
              <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-700">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                Yönetici Özeti
              </div>
              <p className="whitespace-pre-wrap text-sm leading-7 text-gray-700">
                {finalReport}
              </p>
            </section>

            <div className="grid gap-6 lg:grid-cols-2">
              <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
                <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-gray-700">
                  <Landmark className="h-4 w-4 text-blue-500" />
                  Finansal Sağlık
                </div>

                <div className="space-y-3">
                  {derived.metrics.map((metric) => (
                    <div key={metric.label} className={`flex items-center justify-between rounded-xl border px-4 py-3 ${getToneClasses(metric.tone)}`}>
                      <span className="text-sm font-medium">{metric.label}</span>
                      <span className="font-mono text-sm font-semibold">{metric.value}</span>
                    </div>
                  ))}
                </div>
              </section>

              <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
                <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-gray-700">
                  <LineChart className="h-4 w-4 text-violet-500" />
                  Piyasa ve Risk Özeti
                </div>

                <div className="rounded-2xl border border-gray-200 bg-slate-50 p-4">
                  <div className="mb-2 flex items-center justify-between text-sm">
                    <span className="font-medium text-gray-700">Sektör Risk Skoru</span>
                    <span className={`rounded-full border px-3 py-1 font-mono text-xs ${getToneClasses(derived.marketRiskTone)}`}>
                      {derived.sectorRiskScore ?? '—'} / 100
                    </span>
                  </div>
                  <div className="h-3 overflow-hidden rounded-full bg-gray-200">
                    <div
                      className={`h-full rounded-full transition-all ${getRiskProgressTone(derived.sectorRiskScore)}`}
                      style={{ width: `${riskWidth}%` }}
                    />
                  </div>
                </div>

                <div className="mt-4 grid gap-3 text-sm">
                  <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
                    <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">Sentiment</div>
                    <div className="font-medium text-gray-800">
                      {String(derived.marketAnalysis?.sentiment || '—')}
                    </div>
                  </div>

                  <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
                    <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">Kritik Riskler</div>
                    <ul className="list-disc space-y-1 pl-5 text-gray-700">
                      {Array.isArray(derived.marketAnalysis?.key_risks) && derived.marketAnalysis.key_risks.length > 0 ? (
                        derived.marketAnalysis.key_risks.map((risk: string) => <li key={risk}>{risk}</li>)
                      ) : (
                        <li>Risk listesi henüz yok.</li>
                      )}
                    </ul>
                  </div>

                  <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
                    <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-gray-500">Rakip ve Haber Özeti</div>
                    <p className="text-gray-700">
                      {derived.marketAnalysis?.competitor_analysis || 'Rakip değerlendirmesi bulunmuyor.'}
                    </p>
                    <p className="mt-3 text-gray-700">
                      {derived.marketAnalysis?.critical_news_summary || 'Kritik haber özeti bulunmuyor.'}
                    </p>
                  </div>
                </div>
              </section>
            </div>

            <section className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
              <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-gray-700">
                <ShieldAlert className="h-4 w-4 text-orange-500" />
                Denetim Geçmişi
              </div>

              {auditLog.length > 0 ? (
                <div className="space-y-3">
                  {auditLog.map((item, index) => (
                    <div key={`${index}-${item}`} className="flex gap-3 rounded-xl border border-gray-200 bg-gray-50 p-4">
                      <div className="mt-1 h-3 w-3 rounded-full bg-blue-500" />
                      <div>
                        <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">Döngü {index + 1}</div>
                        <p className="text-sm text-gray-700">{item}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-600">Audit kaydı yok. İlk karar akışı tamamlandıysa bu alan boş kalabilir.</p>
              )}
            </section>

            <section className="sticky bottom-0 rounded-2xl border border-gray-200 bg-white/95 p-4 shadow-sm backdrop-blur supports-[backdrop-filter]:bg-white/80">
              <div className="flex flex-wrap items-center justify-end gap-3">
                <button
                  type="button"
                  onClick={() => window.print()}
                  className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-100"
                >
                  Yazdır
                </button>
                <button
                  type="button"
                  onClick={onClose}
                  className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-semibold text-blue-700 transition hover:bg-blue-100"
                >
                  Kapat
                </button>
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>,
    document.body,
  );
};

export default ReportModal;