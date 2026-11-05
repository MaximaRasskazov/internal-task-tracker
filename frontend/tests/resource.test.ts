/* eslint-disable vue/one-component-per-file -- Each test mounts an isolated lifecycle harness. */
import { describe, expect, it } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, ref } from 'vue'
import { useResource } from '../src/features/useResource'
describe('resource lifecycle', () => {
  it('ignores the old page response even if the transport ignores abort', async () => {
    const key = ref('old')
    const pending: ((value: string) => void)[] = []
    let resource!: ReturnType<typeof useResource<string>>
    const wrapper = mount(
      defineComponent({
        setup() {
          resource = useResource(
            () => key.value,
            () => new Promise<string>((resolve) => pending.push(resolve)),
          )
          return () => null
        },
      }),
    )
    key.value = 'new'
    await flushPromises()
    pending[1]('fresh')
    await flushPromises()
    expect(resource.data.value).toBe('fresh')
    pending[0]('stale')
    await flushPromises()
    expect(resource.data.value).toBe('fresh')
    wrapper.unmount()
  })
  it('aborts a pending read when its page is closed', () => {
    let signal!: AbortSignal
    const wrapper = mount(
      defineComponent({
        setup() {
          useResource(
            () => '',
            (s) => {
              signal = s
              return new Promise(() => {})
            },
          )
          return () => null
        },
      }),
    )
    expect(signal.aborted).toBe(false)
    wrapper.unmount()
    expect(signal.aborted).toBe(true)
  })
})
