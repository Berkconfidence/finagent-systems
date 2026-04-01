import { useEffect, useState } from 'react'
import StartForm from './components/StartForm'
import StatusDashboard from './components/StatusDashboard'

const ACTIVE_THREAD_STORAGE_KEY = 'finagent_active_thread_id';

function App() {
  const [activeThreadId, setActiveThreadId] = useState<string | null>(() => {
    return localStorage.getItem(ACTIVE_THREAD_STORAGE_KEY);
  });

  useEffect(() => {
    if (activeThreadId) {
      localStorage.setItem(ACTIVE_THREAD_STORAGE_KEY, activeThreadId);
    } else {
      localStorage.removeItem(ACTIVE_THREAD_STORAGE_KEY);
    }
  }, [activeThreadId]);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center py-12">
      <header className="mb-8 text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">FinAgent Intelligence</h1>
        <p className="text-gray-600">Enterprise Credit Risk Analysis System</p>
      </header>
      
      <main className="w-full max-w-[1500px] px-4 flex flex-col lg:flex-row gap-6 items-start justify-center">
        <div className="w-full lg:w-1/4 lg:max-w-md shrink-0">
          <StartForm onStarted={(threadId) => setActiveThreadId(threadId)} />
        </div>
        
        <div className="w-full lg:w-3/4 h-full">
          {activeThreadId ? (
            <>
              <div className="mb-3 flex justify-end">
                <button
                  onClick={() => setActiveThreadId(null)}
                  className="text-sm text-gray-600 hover:text-gray-900 underline"
                >
                  Aktif görünümü temizle
                </button>
              </div>
              <StatusDashboard threadId={activeThreadId} />
            </>
          ) : (
            <div className="bg-white border border-dashed border-gray-300 rounded-lg p-12 flex flex-col items-center justify-center text-gray-400 h-[400px]">
              <p className="mb-2">Sonuçları görmek için sol taraftan yeni bir analiz başlatın.</p>
              <span className="text-sm">HITL mekanizması devrede olduğunda burada onay ekranı belirecektir.</span>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

export default App
