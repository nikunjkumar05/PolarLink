import { Link, NavLink, Route, Routes } from 'react-router-dom'
import Alerts from './pages/Alerts'
import ArticleDetail from './pages/ArticleDetail'
import Articles from './pages/Articles'
import AssetDetail from './pages/AssetDetail'
import Claims from './pages/Claims'
import Landing from './pages/Landing'
import Login from './pages/Login'
import PublicArticle from './pages/PublicArticle'
import Repository from './pages/Repository'
import Search from './pages/Search'
import Upload from './pages/Upload'
import { useAuth } from './lib/useAuth'

export default function App() {
  const { user, signOut, can } = useAuth()

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
          <NavLink to="/claims">Claims</NavLink>
          <NavLink to="/articles">Articles</NavLink>
          {can('REVIEWER') && <NavLink to="/alerts">Alerts</NavLink>}
        </nav>
        <div className="session">
          {user ? (
            <>
              <span className="small">
                {user.name} <span className="chip">{user.role.toLowerCase()}</span>
              </span>
              <button className="btn small" onClick={signOut}>
                Sign out
              </button>
            </>
          ) : (
            <Link className="btn small" to="/login">
              Sign in
            </Link>
          )}
        </div>
      </header>

      <main className="page">
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/repository" element={<Repository />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/search" element={<Search />} />
          <Route path="/assets/:id" element={<AssetDetail />} />
          <Route path="/login" element={<Login />} />
          <Route path="/claims" element={<Claims />} />
          <Route path="/articles" element={<Articles />} />
          <Route path="/articles/:id" element={<ArticleDetail />} />
          <Route path="/alerts" element={<Alerts />} />
          <Route path="/read/:slug" element={<PublicArticle />} />
        </Routes>
      </main>
    </div>
  )
}