// Mirrors the backend vocabularies (allegro/modules/*: catalog/enums.py, accounts/roles.py, publications, site)
/** What a work is written for: one choice that suggests its usual instruments (the composer can edit them) */
export const GENRES: Record<string, { label: string; instruments: string[] }> = {
  solo: { label: 'Соло', instruments: ['фортепиано'] },
  duo_sonata: { label: 'Соната для инструмента и фортепиано', instruments: ['скрипка', 'фортепиано'] },
  duo: { label: 'Дуэт', instruments: [] },
  trio: { label: 'Трио', instruments: ['скрипка', 'виолончель', 'фортепиано'] },
  quartet: { label: 'Квартет', instruments: ['скрипка', 'скрипка', 'альт', 'виолончель'] },
  quintet: { label: 'Квинтет', instruments: ['фортепиано', 'скрипка', 'скрипка', 'альт', 'виолончель'] },
  ensemble: { label: 'Камерный ансамбль', instruments: [] },
  concerto: { label: 'Концерт', instruments: ['фортепиано', 'оркестр'] },
  symphony: { label: 'Симфония', instruments: ['оркестр'] },
  orchestral: { label: 'Оркестровая пьеса', instruments: ['оркестр'] },
  vocal: { label: 'Романс, песня', instruments: ['голос', 'фортепиано'] },
  choir: { label: 'Хор', instruments: ['хор'] },
  cantata: { label: 'Кантата, оратория, опера', instruments: ['солисты', 'хор', 'оркестр'] },
  other: { label: 'Другое', instruments: [] },
}
export const genreLabel = (genre: string) => GENRES[genre]?.label || 'Другое'

/** Suggestions for the instrument list (any other name can be typed) */
export const INSTRUMENTS = [
  'фортепиано', 'скрипка', 'альт', 'виолончель', 'контрабас', 'флейта', 'гобой', 'кларнет', 'фагот', 'саксофон',
  'валторна', 'труба', 'тромбон', 'туба', 'арфа', 'гитара', 'орган', 'клавесин', 'ударные', 'челеста', 'голос',
  'хор', 'оркестр', 'струнный оркестр', 'солисты', 'баян', 'аккордеон', 'домра', 'балалайка', 'электроника',
]

/** «скрипка, скрипка, альт, виолончель» → «2 скрипки, альт, виолончель» */
export function instrumentsText(list: string[]): string {
  const counts = new Map<string, number>()
  for (const name of list) counts.set(name, (counts.get(name) || 0) + 1)
  return [...counts].map(([name, n]) => (n > 1 ? `${n} × ${name}` : name)).join(', ')
}

export const SCORE_ACCESS: Record<string, string> = {
  free: 'Свободное скачивание',
  view_only: 'Только просмотр',
  paid: 'За донат (скоро)',
}

export const STATUSES: Record<string, string> = {
  published: 'Опубликовано',
  unlisted: 'По ссылке',
  draft: 'Черновик',
}

export const POST_KINDS: Record<string, string> = {
  note: 'Запись в блоге',
  article: 'Статья',
  news: 'Новости',
  workshop: 'Мастерская',
}

export const MATERIAL_KINDS: Record<string, string> = {
  book: 'Книги',
  link: 'Ссылки',
  file: 'Файлы',
}

export const ROLES: Record<string, { label: string; icon: string; about: string }> = {
  composer: { label: 'Композитор', icon: '♪', about: 'Выставка и библиотека сочинений, статьи, блог' },
  theorist: { label: 'Теоретик / музыковед', icon: '¶', about: 'Статьи и обзоры, блог, материалы' },
  performer: { label: 'Исполнитель', icon: '♫', about: 'Исполнения — свои записи любых сочинений, блог' },
  listener: { label: 'Слушатель', icon: '♡', about: 'Блог и обсуждения: слушать, читать, делиться мыслями' },
}

export const HALL_THEMES: Record<string, { label: string; about: string }> = {
  baroque: { label: 'Барокко и классицизм', about: 'Гравюрные прописные, пурпур и старое золото' },
  romantic: { label: 'Романтизм', about: 'Тёмный холст, свет свечи, золочёные рамы' },
  modern: { label: 'Модерн', about: 'Зелень и медь, плавные линии начала века' },
  avantgarde: { label: 'Авангард', about: 'Чёрный, красный и белый, геометрия плаката' },
}

export const FEEDBACK_KINDS: Record<string, string> = { idea: 'Идея', bug: 'Ошибка', other: 'Другое' }
export const FEEDBACK_STATUSES: Record<string, string> = {
  new: 'Новое',
  planned: 'В планах',
  done: 'Сделано',
  declined: 'Отклонено',
}

/** Google Fonts of each hall era (romanticism is the site's own set, always loaded) */
export const THEME_FONTS: Record<string, string[]> = {
  baroque: ['Prata', 'Alegreya:ital,wght@0,400;0,500;0,700;1,400;1,500', 'Playfair+Display+SC:wght@400;700'],
  modern: ['Kurale', 'Philosopher:ital,wght@0,400;0,700;1,400'],
  avantgarde: ['Oswald:wght@400;500;600', 'Jost:ital,wght@0,400;0,500;1,400'],
}
export const themeFontsUrl = (families: string[]) =>
  `https://fonts.googleapis.com/css2?${families.map((f) => `family=${f}`).join('&')}&display=swap`
