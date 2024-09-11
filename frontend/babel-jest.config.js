// babel-jest.config.js
module.exports = {
  presets: [
    [
      '@babel/preset-env', // Automatically includes necessary polyfills and transformations
    ],
    [
      '@babel/preset-react',
      {
        runtime: 'automatic', // Enables the new JSX transform
      },
    ],
  ],
};
