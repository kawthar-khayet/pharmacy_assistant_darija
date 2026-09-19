import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.jsx'
import { ConversationsProvider } from './lib/ConversationsContext'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <ConversationsProvider>
        <App />
      </ConversationsProvider>
    </BrowserRouter>
  </StrictMode>,
)
