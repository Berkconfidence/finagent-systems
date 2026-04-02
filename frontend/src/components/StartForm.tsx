import React, { useEffect, useState } from 'react';
import { Play } from 'lucide-react';
import axios from 'axios';
import { getRecentAnalyses, type RecentAnalysisItem, startAnalysisWithPdf } from '../api';

interface StartFormProps {
  onStarted: (threadId: string) => void;
}

const StartForm: React.FC<StartFormProps> = ({ onStarted }) => {
  const [companyName, setCompanyName] = useState('');
  const [selectedPdf, setSelectedPdf] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [recentItems, setRecentItems] = useState<RecentAnalysisItem[]>([]);
  const [recentLoading, setRecentLoading] = useState(false);
  const [recentError, setRecentError] = useState<string | null>(null);

  const loadRecent = async () => {
    setRecentLoading(true);
    setRecentError(null);
    try {
      const response = await getRecentAnalyses(10);
      setRecentItems(response.items || []);
    } catch (err: any) {
      setRecentError(err?.message || 'Son analizler alınamadı');
    } finally {
      setRecentLoading(false);
    }
  };

  useEffect(() => {
    loadRecent();
  }, []);

  const readApiError = (err: unknown) => {
    if (axios.isAxiosError(err)) {
      const detail = err.response?.data?.detail;
      if (typeof detail === 'string' && detail.trim()) {
        return detail;
      }
    }
    if (err instanceof Error && err.message) {
      return err.message;
    }
    return 'İstek sırasında bir hata oluştu';
  };

  const validatePdf = (file: File | null) => {
    if (!file) {
      return 'Lütfen bir PDF dosyası seçin.';
    }

    const maxSizeBytes = 20 * 1024 * 1024;
    const lowerName = file.name.toLowerCase();
    const isPdfMime = file.type === 'application/pdf';
    const isPdfExtension = lowerName.endsWith('.pdf');

    if (!isPdfMime && !isPdfExtension) {
      return 'Yalnızca PDF dosyası yükleyebilirsiniz.';
    }

    if (file.size > maxSizeBytes) {
      return 'PDF dosyası en fazla 20 MB olabilir.';
    }

    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const validationError = validatePdf(selectedPdf);
    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);
    setError(null);
    setInfo(null);
    
    try {
      const response = await startAnalysisWithPdf({
        company_name: companyName,
        file: selectedPdf!,
      });
      
      if (response && response.thread_id) {
        setInfo(response.message || null);
        onStarted(response.thread_id);
        await loadRecent();
      } else {
        setError('Geçersiz yanıt: Thread ID bulunamadı.');
      }
    } catch (err) {
      console.error(err);
      setError(readApiError(err));
    } finally {
      setLoading(false);
    }
  };

  const handlePdfChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    setSelectedPdf(file);

    const validationError = validatePdf(file);
    if (validationError) {
      setError(validationError);
      return;
    }

    setError(null);
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
      <h2 className="text-xl font-semibold mb-4 text-gray-800">Yeni Analiz Başlat</h2>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Şirket Ticari Unvanı
          </label>
          <input
            type="text"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            placeholder="Firma ismini giriniz"
            className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Finansal Tablo PDF
          </label>
          <input
            type="file"
            accept="application/pdf,.pdf"
            onChange={handlePdfChange}
            className="w-full p-2 border border-gray-300 rounded-md text-sm file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            required
          />
          <p className="text-xs text-gray-500 mt-1">Maksimum dosya boyutu: 20 MB</p>
          {selectedPdf && (
            <p className="text-xs text-gray-600 mt-1 truncate">
              Seçili dosya: {selectedPdf.name}
            </p>
          )}
        </div>

        {error && (
          <div className="text-red-600 text-sm bg-red-50 p-2 rounded">
            {error}
          </div>
        )}

        {info && (
          <div className="text-blue-700 text-sm bg-blue-50 p-2 rounded border border-blue-100">
            {info}
          </div>
        )}

        <button
          type="submit"
          disabled={loading || !selectedPdf}
          className="w-full mt-4 flex items-center justify-center gap-2 bg-blue-600 text-white p-2 rounded-md hover:bg-blue-700 transition disabled:opacity-50"
        >
          {loading ? (
            <span className="animate-pulse">Başlatılıyor...</span>
          ) : (
            <>
              <Play size={18} />
              Analizi Başlat
            </>
          )}
        </button>
      </form>

      <div className="mt-6 pt-4 border-t border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-700">Son Analizler</h3>
          <button
            type="button"
            onClick={loadRecent}
            className="text-xs text-blue-600 hover:text-blue-800 underline"
            disabled={recentLoading}
          >
            Yenile
          </button>
        </div>

        {recentLoading && <p className="text-xs text-gray-500">Yükleniyor...</p>}
        {recentError && <p className="text-xs text-red-600">{recentError}</p>}

        {!recentLoading && !recentError && recentItems.length === 0 && (
          <p className="text-xs text-gray-500">Henüz analiz kaydı yok.</p>
        )}

        {!recentLoading && !recentError && recentItems.length > 0 && (
          <div className="space-y-2 max-h-56 overflow-auto pr-1">
            {recentItems.map((item) => (
              <button
                key={item.thread_id}
                type="button"
                onClick={() => onStarted(item.thread_id)}
                className="w-full text-left border border-gray-200 rounded-md p-2 hover:bg-gray-50 transition"
              >
                <div className="text-xs font-semibold text-gray-800 truncate">
                  {item.company_name || 'Bilinmeyen Şirket'}
                </div>
                <div className="mt-1 text-[11px] text-gray-500 flex items-center justify-between">
                  <span>{item.status.toUpperCase()}</span>
                  <span className="truncate ml-2">{item.thread_id}</span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default StartForm;