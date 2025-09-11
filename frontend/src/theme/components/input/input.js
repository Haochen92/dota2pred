// theme.ts
'use client';

import { Input, TextInput, Select, MultiSelect, createTheme } from '@mantine/core';
import classes from './input.module.css';

const inputTheme = createTheme({
  components: {
    // Base input primitive – affects many components that use "input" slot
    Input: Input.extend({
      defaultProps: { variant: 'filled' },
      classNames: { input: classes.customFilled },
    }),

    // Explicitly apply to common inputs used in FiltersBar
    TextInput: TextInput.extend({
      defaultProps: { variant: 'filled' },
      classNames: { input: classes.customFilled },
    }),
    Select: Select.extend({
      defaultProps: { variant: 'filled' },
      classNames: { input: classes.customFilled },
    }),
    MultiSelect: MultiSelect.extend({
      defaultProps: { variant: 'filled' },
      classNames: { inputField: classes.customFilled },
    }),
  },
});

export default inputTheme;
