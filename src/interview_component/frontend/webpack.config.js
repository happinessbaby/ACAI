const path = require('path');

module.exports = {
  entry: './src/MyComponent.tsx',
  output: {
    filename: 'bundle.js',
    path: path.resolve(__dirname, 'dist'),
  },
  resolve: {
    extensions: ['.ts', '.tsx', '.js'],
  },
  module: {
    rules: [
      {
        test: /\.js$|jsx/,
        use: 'ts-loader',
        exclude: /node_modules/,
      },
    ],
  },
};