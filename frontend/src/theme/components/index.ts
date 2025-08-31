'use client';

import { mergeThemeOverrides } from "@mantine/core";
import buttonTheme from "./button/button";
import textTheme from "./text/text";

const componentsTheme = mergeThemeOverrides(
    buttonTheme,
    textTheme
);

export default componentsTheme;
