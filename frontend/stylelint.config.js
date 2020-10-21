module.exports = {
    rules: {
        indentation: 4,
        'selector-pseudo-element-no-unknown': [
            true,
            {
                ignorePseudoElements: ['v-deep']
            }
        ]
    },
    extends: ['stylelint-config-standard', 'stylelint-config-prettier']
}
