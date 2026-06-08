import { Routes, Route } from 'react-router-dom'
import { Playground } from './pages/Playground'
import { ResultDetail } from './pages/ResultDetail'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Playground />} />
      <Route path="/result" element={<ResultDetail />} />
    </Routes>
  )
}
