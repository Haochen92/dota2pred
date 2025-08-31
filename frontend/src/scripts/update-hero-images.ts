import { HeroImageData } from "@/types/contracts/index";
import fetchHeroData from "@/api/fetch-hero-data";
import getRootDir from "@/utils/get-root-dir";
import fsp from 'fs/promises';
import path from 'path';
import os from 'os';

const ROOT_DIR = getRootDir();
const DEFAULT_IMAGE_DIR = path.join(ROOT_DIR, 'public', 'icons', 'heroes');
const CDN_HOST = 'http://cdn.dota2.com'

async function downloadImage(url: string, filepath: string): Promise<void> {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Failed to fetch image from ${url}: ${res.statusText}`);
    const arrayBuffer = await res.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);
    await fsp.writeFile(filepath, buffer);
}

async function fileExists(filepath: string): Promise<boolean> {
    try {
        await fsp.access(filepath);
        return true;
    } catch {
        return false;
    }
}

export async function updateHeroImages({ targetDir = DEFAULT_IMAGE_DIR } = {}) {
    console.log("Fetching hero data from backend...");
    const heroData: HeroImageData[] = await fetchHeroData();
    console.log(`Found ${heroData.length} heroes. Processing images...`);

    await fsp.mkdir(targetDir, { recursive: true });

    let imagesToDownload = 0;
    let imagesExist = 0;

    const downloadTasks = heroData.map(async (hero) => {
        const imagePath = path.join(targetDir, `${hero.hero_id}.png`);
        const imageUrl = `${CDN_HOST}${hero.image_url}`;

        if (await fileExists(imagePath)) {
            imagesExist++;
        } else if (imageUrl) {
            imagesToDownload++;
            try {
                await downloadImage(imageUrl, imagePath);
            } catch (error: any) {
                console.warn(`Failed to download image for hero ID ${hero.hero_id}: ${error.message}`);
            }
        }
    });

    await Promise.all(downloadTasks);

    console.log("\n--- Sync Summary ---");
    console.log(`Target Directory: ${targetDir}`);
    console.log(`Total Heroes Processed: ${heroData.length}`);
    console.log(`Images Already Existing: ${imagesExist}`);
    console.log(`Images Downloaded: ${imagesToDownload}`);
}

(async () => {
    const isDryRun = process.argv.includes('--dry-run');

    if (isDryRun) {
        console.log('--- RUNNING IN DRY RUN MODE ---');
        let tempDir: string | undefined;
        try {
            tempDir = await fsp.mkdtemp(path.join(os.tmpdir(), 'hero-images-sync-'));
            console.log(`Created temporary sandbox at: ${tempDir}`);

            await updateHeroImages({ targetDir: tempDir });
            console.log("\nDry run validation successful.");

        } finally {
            if (tempDir) {
                console.log(`Cleaning up sandbox directory: ${tempDir}`);
                await fsp.rm(tempDir, { recursive: true, force: true });
                console.log("Sandbox cleaned up.");
            }
        }
    } else {
        console.log('--- RUNNING IN NORMAL MODE ---');
        await updateHeroImages({ targetDir: DEFAULT_IMAGE_DIR });
        console.log("\nSync complete.");
    }

})().catch(error => {
    console.error("\n--- An unexpected error occurred ---");
    console.error(error);
    process.exit(1);
});
