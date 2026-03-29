import { useState } from 'react'
import StartForm from './components/StartForm'
import StatusDashboard from './components/StatusDashboard'

function App() {
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center py-12">
      <header className="mb-8 text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">FinAgent Intelligence</h1>
        <p className="text-gray-600">Enterprise Credit Risk Analysis System</p>
      </header>
      
      <main className="w-full max-w-5xl px-4 flex flex-col md:flex-row gap-6 items-start">
        <div className="w-full md:w-1/3">
          <StartForm onStarted={(threadId) => setActiveThreadId(threadId)} />
        </div>
        
        <div className="w-full md:w-2/3 h-full">
          {activeThreadId ? (
            <StatusDashboard threadId={activeThreadId} />
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
