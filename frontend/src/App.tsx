import { Link, NavLink, Route, Routes } from 'react-router-dom'
import Landing from './pages/Landing'
import Repository from './pages/Repository'
import Upload from './pages/Upload'
import AssetDetail from './pages/AssetDetail'
import Search from './pages/Search'

export default function App() {
  return (
    <div className="app">
      <header className="topbar">
        <Link className="brand" to="/">
          <span className="brand-mark" aria-hidden="true" />
          <span>
            <strong>PolarLink</strong>
            <span className="brand-sub">Evidence-linked polar knowledge</span>
          </span>
        </Link>
        <nav>
          <NavLink to="/" end>
            Home
          </NavLink>
          <NavLink to="/repository">Repository</NavLink>
          <NavLink to="/upload">Upload</NavLink>
          <NavLink to="/search">Search</NavLink>
        </nav>
      </header>

      <main className="page">
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/repository" element={<Repository />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/search" element={<Search />} />
          <Route path="/assets/:id" element={<AssetDetail />} />
        </Routes>
      </main>
    </div>
  )
}
