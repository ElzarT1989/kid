import { BrowserRouter, Route, Routes } from 'react-router-dom'
import RequireAuth from './components/RequireAuth'
import ChildDetail from './pages/ChildDetail'
import Channels from './pages/Channels'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import Videos from './pages/Videos'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <RequireAuth>
              <Dashboard />
            </RequireAuth>
          }
        />
        <Route
          path="/children/:childId"
          element={
            <RequireAuth>
              <ChildDetail />
            </RequireAuth>
          }
        />
        <Route
          path="/channels"
          element={
            <RequireAuth>
              <Channels />
            </RequireAuth>
          }
        />
        <Route
          path="/videos"
          element={
            <RequireAuth>
              <Videos />
            </RequireAuth>
          }
        />
      </Routes>
    </BrowserRouter>
  )
}
