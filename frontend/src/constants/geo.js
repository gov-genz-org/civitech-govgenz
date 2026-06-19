/**
 * Constantes géographiques partagées — Madagascar + Diaspora
 * Importé partout où on a des filtres de localisation ou de profil
 */

export const REGIONS_MG = [
  'Analamanga', 'Vakinankaratra', 'Itasy', 'Bongolava',
  'Matsiatra Ambony', "Amoron'i Mania", 'Vatovavy', 'Fitovinany',
  'Ihorombe', 'Atsimo-Atsinanana', 'Atsinanana', 'Analanjirofo',
  'Alaotra-Mangoro', 'Boeny', 'Sofia', 'Betsiboka', 'Melaky',
  'Atsimo-Andrefana', 'Androy', 'Anosy', 'Menabe', 'Diana', 'Sava',
  'Haute Matsiatra',
]

// Pays de la diaspora malgache (les plus importants en premier)
export const DIASPORA_COUNTRIES = [
  { value: 'FR', label: '🇫🇷 France' },
  { value: 'RE', label: '🇷🇪 La Réunion' },
  { value: 'YT', label: '🇾🇹 Mayotte' },
  { value: 'KM', label: '🇰🇲 Comores' },
  { value: 'ZA', label: '🇿🇦 Afrique du Sud' },
  { value: 'MU', label: '🇲🇺 Maurice' },
  { value: 'US', label: '🇺🇸 États-Unis' },
  { value: 'CA', label: '🇨🇦 Canada' },
  { value: 'BE', label: '🇧🇪 Belgique' },
  { value: 'CH', label: '🇨🇭 Suisse' },
  { value: 'DE', label: '🇩🇪 Allemagne' },
  { value: 'GB', label: '🇬🇧 Royaume-Uni' },
  { value: 'AU', label: '🇦🇺 Australie' },
  { value: 'CN', label: '🇨🇳 Chine' },
  { value: 'AE', label: '🇦🇪 Émirats Arabes Unis' },
  { value: 'OTHER', label: '🌍 Autre pays' },
]

// Toutes les options de localisation (profil utilisateur)
// Un utilisateur est soit à Madagascar (région), soit en diaspora (pays)
export const LOCATION_OPTIONS = {
  MADAGASCAR: 'MG',
  DIASPORA_PREFIX: 'DIASPORA_',
}

// Options pour les filtres de faits/alertes (lieu de l'événement)
export const LOCATION_SCOPES = [
  { value: '', label: 'Toutes les zones' },
  { value: 'national', label: '🇲🇬 Madagascar — national' },
  ...REGIONS_MG.map(r => ({ value: r, label: `   · ${r}` })),
  { value: 'international', label: '🌍 International / Diaspora' },
  ...DIASPORA_COUNTRIES.map(c => ({ value: c.value, label: `   · ${c.label}` })),
]

// Régions pour les faits/collecte (avec options hors-Madagascar)
export const REGIONS_WITH_DIASPORA = [
  'National',
  ...REGIONS_MG,
  '— Hors Madagascar —',
  ...DIASPORA_COUNTRIES.map(c => c.label),
]
