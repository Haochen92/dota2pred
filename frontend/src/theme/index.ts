'use client';

import { mergeThemeOverrides } from "@mantine/core";
import colorTheme from "./colors";
import componentsTheme from "./components/index";
import typographyTheme from "./typography";

const customTheme = mergeThemeOverrides(
    typographyTheme,
    colorTheme,
    componentsTheme
);

export default customTheme;
