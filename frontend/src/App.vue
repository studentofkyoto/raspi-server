<template>
    <div id="app">
        <button class="btn btn-primary" @click="gpioOn">ON</button>
        <button class="btn btn-primary" @click="gpioOff">OFF</button>
    </div>
</template>

<script>
import axios from 'axios'
export default {
    methods: {
        gpioOn() {
            axios.get('/on').then(() => {
                console.log('on')
            })
        },
        gpioOff() {
            axios.get('/off').then(() => {
                console.log('off')
            })
        }
    }
}
</script>
