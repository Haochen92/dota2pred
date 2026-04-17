import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

export default function getRootDir() {
    const __filename = fileURLToPath(import.meta.url);
    const __dirname = path.dirname(__filename);
    const rootDir = path.resolve(__dirname, '../../');
    console.log('Root Directory:', rootDir);
    if (!fs.existsSync(rootDir)) {
        throw new Error('Root directory does not exist');
    }
    return rootDir;
}

// If this script is run directly, print the root directory
if (import.meta.url === `file://${process.argv[1]}`) {
      console.log('Running directly, result:', getRootDir());
  }
