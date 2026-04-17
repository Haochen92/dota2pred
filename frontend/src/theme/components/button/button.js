'use client'

import { Button, createTheme } from "@mantine/core"
import  classes  from "./button.module.css"

const buttonTheme = createTheme({
    components: {
        Button: Button.extend({
            classNames:{root: classes.root},
        })
    }
})

export default buttonTheme;
