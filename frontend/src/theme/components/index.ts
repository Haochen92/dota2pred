'use client';

import { mergeThemeOverrides } from "@mantine/core";
import buttonTheme from "./button/button";
import textTheme from "./text/text";
import inputTheme from "./input/input";

const componentsTheme = mergeThemeOverrides(
    buttonTheme,
    textTheme,
    inputTheme
);

export default componentsTheme;
