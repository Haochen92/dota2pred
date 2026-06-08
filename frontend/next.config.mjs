/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  experimental: {
    optimizePackageImports: [
      '@mantine/core',
      '@mantine/charts',
      '@mantine/dates',
      '@mantine/hooks',
      '@tabler/icons-react',
    ],
  },
};

export default nextConfig;
