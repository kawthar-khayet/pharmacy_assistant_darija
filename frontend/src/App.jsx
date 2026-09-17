import { Route, Routes, useLocation } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import BottomNavigation from './components/BottomNavigation'
import Home from './pages/Home'
import Assistant from './pages/Assistant'
import Medicines from './pages/Medicines'
import Pharmacies from './pages/Pharmacies'
import History from './pages/History'
import Settings from './pages/Settings'

export default function App() {
  const location = useLocation()

  // L'Assistant gere son propre defilement (fil + socle fixes), les autres
  // pages defilent normalement : la classe distingue les deux comportements.
  const plein = location.pathname.startsWith('/assistant')

  return (
    <div className="coquille">
      <Sidebar />

      <main className="zone" style={plein ? { overflow: 'hidden' } : undefined}>
        {/* la cle sur la route rejoue l'apparition a chaque changement de page */}
        <div key={location.pathname} className="transition-page" style={{ height: plein ? '100%' : undefined }}>
          <Routes location={location}>
            <Route path="/" element={<Home />} />
            <Route path="/assistant" element={<Assistant />} />
            <Route path="/medicaments" element={<Medicines />} />
            <Route path="/pharmacies" element={<Pharmacies />} />
            <Route path="/historique" element={<History />} />
            <Route path="/parametres" element={<Settings />} />
            <Route path="*" element={<Home />} />
          </Routes>
        </div>
      </main>

      <BottomNavigation />
    </div>
  )
}
