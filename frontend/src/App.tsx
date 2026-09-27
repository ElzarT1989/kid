import { BrowserRouter, Route, Routes } from 'react-router-dom'
import ChildPlayer from './pages/ChildPlayer'
import ProfileSelect from './pages/ProfileSelect'

export default function App() {
  return (
    <BrowserRouter>
      <div className="h-screen w-screen overflow-hidden bg-slate-950">
        <Routes>
          <Route path="/" element={<ProfileSelect />} />
          <Route path="/play/:childId" element={<ChildPlayer />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
