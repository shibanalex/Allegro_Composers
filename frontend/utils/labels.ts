// Mirrors the backend vocabularies (allegro/modules/*: catalog/enums.py, accounts/roles.py, publications, site)
export const ENSEMBLES: Record<string, string> = {
  solo: 'Соло',
  chamber: 'Камерный ансамбль',
  orchestra: 'Симфонический оркестр',
  choir: 'Хор',
}

export const FORMS: Record<string, string> = {
  sonata: 'Соната',
  suite: 'Сюита',
  miniature: 'Миниатюра',
  variations: 'Вариации',
  cantata: 'Кантата',
  other: 'Другое',
}

export const DIFFICULTY: Record<number, string> = {
  1: 'Начальная',
  2: 'Лёгкая',
  3: 'Средняя',
  4: 'Сложная',
  5: 'Виртуозная',
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
  composer: { label: 'Композитор', icon: '♪', about: 'Выставка и библиотека сочинений, статьи, исполнения, блог' },
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
