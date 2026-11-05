import { onMounted, onUnmounted } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
export function useSettingsGuard(dirty: () => boolean, busy: () => boolean) {
  function leave() {
    return !busy() && (!dirty() || window.confirm('Не сохранять изменения формы?'))
  }
  onBeforeRouteLeave((to) => (to.meta.public ? true : leave()))
  function unload(e: BeforeUnloadEvent) {
    if (dirty() || busy()) {
      e.preventDefault()
      e.returnValue = ''
    }
  }
  onMounted(() => window.addEventListener('beforeunload', unload))
  onUnmounted(() => window.removeEventListener('beforeunload', unload))
}
