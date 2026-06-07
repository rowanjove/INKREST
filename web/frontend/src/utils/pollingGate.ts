/** Skip background polls when the tab is hidden (saves API/disk load during连写). */
export function shouldPoll(): boolean {
  return typeof document === 'undefined' || document.visibilityState !== 'hidden'
}