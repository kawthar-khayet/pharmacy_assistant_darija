import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.jsx'
import { reveillerApi } from './lib/api'
import { ConversationsProvider } from './lib/ConversationsContext'
import { LanguageProvider } from './lib/LanguageContext'

// L'API dort peut-etre (Azure) : on la reveille pendant que le visiteur decouvre le site
reveillerApi()

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <LanguageProvider>
        <ConversationsProvider>
          <App />
        </ConversationsProvider>
      </LanguageProvider>
    </BrowserRouter>
  </StrictMode>,
)
