import { createTheme, Text } from '@mantine/core';
import classes from './text.module.css';

/**
 * This file connects our CSS module to the Mantine Text component.
 * It tells every Text component to use the .root class from our CSS file.
 */
const textTheme = createTheme({
  components: {
    Text: Text.extend({
      classNames: {
        root: classes.root,
      },
    }),
  },
});

export default textTheme;
