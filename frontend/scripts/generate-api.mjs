import { readFile, writeFile, mkdir } from 'node:fs/promises'
import openapiTS, { astToString } from 'openapi-typescript'
const output = new URL('../src/api/generated/schema.ts', import.meta.url)
const source = new URL('../../docs/api/openapi.json', import.meta.url)
const generated = astToString(await openapiTS(source))
if (process.argv.includes('--check')) {
  if ((await readFile(output, 'utf8')) !== generated) {
    console.error('Типы API устарели. Выполните npm run api:generate.')
    process.exitCode = 1
  }
} else {
  await mkdir(new URL('../src/api/generated/', import.meta.url), { recursive: true })
  await writeFile(output, generated)
}
