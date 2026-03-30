import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from './components/Layout'
import { InterviewPage } from './pages/InterviewPage'
import { FlowDiagramPage } from './pages/FlowDiagramPage'
import { ReviewPage } from './pages/ReviewPage'
import { SchemaPage } from './pages/SchemaPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<SchemaPage />} />
          <Route path="/interview/:interviewId" element={<InterviewPage />} />
          <Route path="/interview/:interviewId/flow" element={<FlowDiagramPage />} />
          <Route path="/interview/:interviewId/review" element={<ReviewPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
