/** Shared open/closed state of the Ctrl+K search palette */
export const useSearchPalette = () => {
  const open = useState('search-open', () => false)
  return reactive({ open })
}
