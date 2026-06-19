/**
 * Types d'entités — Civitech
 * L'État malgache est la cible principale,
 * mais tous les acteurs nationaux ET internationaux opérant sur Madagascar sont documentés.
 */

export const ENTITY_TYPE_CONFIG = {
  // ── Acteurs nationaux ──────────────────────────────────────────────────────
  politician:   { label: 'Politicien',          icon: '👤', color: 'text-red-700    bg-red-50    border-red-200    dark:text-red-300    dark:bg-red-900/20    dark:border-red-800' },
  institution:  { label: 'Institution d\'État', icon: '🏛',  color: 'text-blue-700   bg-blue-50   border-blue-200   dark:text-blue-300   dark:bg-blue-900/20   dark:border-blue-800' },
  company:      { label: 'Entreprise',          icon: '🏢', color: 'text-purple-700 bg-purple-50 border-purple-200 dark:text-purple-300 dark:bg-purple-900/20 dark:border-purple-800' },
  media:        { label: 'Média',               icon: '📺', color: 'text-orange-700 bg-orange-50 border-orange-200 dark:text-orange-300 dark:bg-orange-900/20 dark:border-orange-800' },
  ngo:          { label: 'ONG nationale',       icon: '🤝', color: 'text-green-700  bg-green-50  border-green-200  dark:text-green-300  dark:bg-green-900/20  dark:border-green-800' },
  group:        { label: 'Groupe / Réseau',     icon: '🕸',  color: 'text-gray-700   bg-gray-50   border-gray-200   dark:text-gray-300   dark:bg-gray-800      dark:border-gray-700' },
  person:       { label: 'Personne physique',   icon: '🧑', color: 'text-indigo-700 bg-indigo-50 border-indigo-200 dark:text-indigo-300 dark:bg-indigo-900/20 dark:border-indigo-800' },

  // ── Acteurs internationaux opérant à Madagascar ───────────────────────────
  ptf:          { label: 'PTF / Bailleur',      icon: '💰', color: 'text-teal-700   bg-teal-50   border-teal-200   dark:text-teal-300   dark:bg-teal-900/20   dark:border-teal-800' },
  intl_org:     { label: 'Organisation intl.',  icon: '🌐', color: 'text-cyan-700   bg-cyan-50   border-cyan-200   dark:text-cyan-300   dark:bg-cyan-900/20   dark:border-cyan-800' },
  embassy:      { label: 'Ambassade / Consul',  icon: '🏴', color: 'text-slate-700  bg-slate-50  border-slate-200  dark:text-slate-300  dark:bg-slate-900/20  dark:border-slate-800' },
  foreign_co:   { label: 'Entreprise étrangère',icon: '🏭', color: 'text-violet-700 bg-violet-50 border-violet-200 dark:text-violet-300 dark:bg-violet-900/20 dark:border-violet-800' },
  diaspora_org: { label: 'Organisation diaspora',icon: '✈️', color: 'text-pink-700   bg-pink-50   border-pink-200   dark:text-pink-300   dark:bg-pink-900/20   dark:border-pink-800' },
}

// Types backend autorisés (à synchroniser avec models/entity.py si besoin)
export const ENTITY_TYPES_BACKEND = Object.keys(ENTITY_TYPE_CONFIG)
