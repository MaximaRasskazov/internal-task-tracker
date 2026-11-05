import js from '@eslint/js'
import ts from 'typescript-eslint'
import vue from 'eslint-plugin-vue'
import prettier from 'eslint-config-prettier'
export default ts.config(
  { ignores: ['dist/**', 'src/api/generated/**'] },
  js.configs.recommended,
  ...ts.configs.recommended,
  ...vue.configs['flat/recommended'],
  {
    files: ['**/*.vue'],
    languageOptions: {
      globals: {
        window: 'readonly',
        document: 'readonly',
        AbortController: 'readonly',
        BeforeUnloadEvent: 'readonly',
        KeyboardEvent: 'readonly',
        DragEvent: 'readonly',
        Event: 'readonly',
        HTMLSelectElement: 'readonly',
      },
      parserOptions: { parser: ts.parser },
    },
  },
  {
    files: ['scripts/*.mjs'],
    languageOptions: { globals: { process: 'readonly', console: 'readonly', URL: 'readonly' } },
  },
  { rules: { 'vue/multi-word-component-names': 'off' } },
  prettier,
)
