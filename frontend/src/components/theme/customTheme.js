'use client'

import { Button, createTheme } from "@mantine/core"
import classes from './customTheme.module.css'

const customTheme = createTheme({
    components: {
        Button: Button.extend({
            classNames:{root: classes.root},
        })
    }
})

export default customTheme;