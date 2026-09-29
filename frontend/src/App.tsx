import { NavLink, Route, Routes } from 'react-router-dom'
import Repository from './pages/Repository'
import Upload from './pages/Upload'
import AssetDetail from './pages/AssetDetail'
import Search from './pages/Search'

export default function App() {
  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true" />
          <div>
            <strong>PolarLink</strong>
            <span className="brand-sub">Knowledge Repository</span>
          </div>
        </div>
        <nav>
          <NavLink to="/" end>
            Repository
          </NavLink>
          <NavLink to="/upload">Upload</NavLink>
          <NavLink to="/search">Search</NavLink>
        </nav>
      </header>

      <main className="page">
        <Routes>
          <Route path="/" element={<Repository />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/search" element={<Search />} />
          <Route path="/assets/:id" element={<AssetDetail />} />
        </Routes>
      </main>
    </div>
  )
}
