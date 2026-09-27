// Mirrors backend/allegro_common/enums.py
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
  article: 'Теория и статьи',
  note: 'Запись в блоге',
  workshop: 'Мастерская',
}

export const MATERIAL_KINDS: Record<string, string> = {
  book: 'Книги',
  link: 'Ссылки',
  file: 'Файлы',
}
