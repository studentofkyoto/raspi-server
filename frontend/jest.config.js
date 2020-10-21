module.exports = {
    transform: {
        '^.+\\.js$': '<rootDir>/node_modules/babel-jest',
        '.*\\.(vue)$': '<rootDir>/node_modules/vue-jest',
        '^.+\\.vue$': 'vue-jest'
    },
    runner: 'browser',

    collectCoverage: false,
    collectCoverageFrom: ['**/*.{js,vue}', '!**/node_modules/**'],
    coverageReporters: ['html', 'text-summary'],

    moduleFileExtensions: ['js', 'vue'],

    moduleNameMapper: {
        '^@/(.*)$': '<rootDir>/src/$1'
    },

    preset: '@vue/cli-plugin-unit-jest'
}
