import React from 'react'
import ReactDOM from 'react-dom/client'
import { initGA } from './components/shared/CookieBanner'
import App from './App'
import './index.css'

// Google Analytics 4 — activé uniquement si l'utilisateur a donné son consentement
initGA()

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
