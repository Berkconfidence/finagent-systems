import React, { useState } from 'react';
import { Play } from 'lucide-react';
import { startAnalysis } from '../api';

interface StartFormProps {
  onStarted: (threadId: string) => void;
}

const StartForm: React.FC<StartFormProps> = ({ onStarted }) => {
  const [companyName, setCompanyName] = useState('TÜRK HAVA YOLLARI A.O.');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setInfo(null);
    
    try {
      const response = await startAnalysis({
        company_name: companyName
      });
      
      if (response && response.thread_id) {
        setInfo(response.message || null);
        onStarted(response.thread_id);
      } else {
        setError('Geçersiz yanıt: Thread ID bulunamadı.');
      }
    } catch (err: any) {
      console.error(err);
      setError(err?.message || 'İstek sırasında bir hata oluştu');
    } finally {
      setLoading(false);
    }
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
            className="w-full p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            required
          />
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
          disabled={loading}
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
    </div>
  );
};

export default StartForm;