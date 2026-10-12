import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.jsx'
import { ConversationsProvider } from './lib/ConversationsContext'
import { LanguageProvider } from './lib/LanguageContext'

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
