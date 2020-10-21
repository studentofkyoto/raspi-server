module.exports = {
    root: true,
    env: {
        node: true
    },
    extends: [
        'eslint:recommended',
        'plugin:prettier/recommended',
        'plugin:vue/vue3-recommended',
        'prettier/vue'
    ],
    parserOptions: {
        parser: 'babel-eslint'
    },
    rules: {
        'no-console': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
        'no-debugger': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
        'no-tabs': ['error', { allowIndentationTabs: true }],
        'vue/html-indent': ['error', 4]
    },
    overrides: [
        {
            files: ['**/tests/unit/**/*.spec.{j,t}s?(x)'],
            env: {
                jest: true
            }
        }
    ]
}
