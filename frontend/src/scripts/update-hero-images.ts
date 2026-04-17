import { HeroImageData } from "@/types/contracts/index";
import fetchHeroData from "@/api-client/fetch-hero-data";
import getRootDir from "@/utils/get-root-dir";
import fsp from 'fs/promises';
import path from 'path';
import os from 'os';

// --- Configuration ---
const ROOT_DIR = getRootDir();
const PUBLIC_DIR = path.join(ROOT_DIR, 'public', 'images', 'heroes');
// Note: cdn.dota2.com currently serves these assets over HTTP with a cert
// that does not match the HTTPS hostname, so we must use plain HTTP here.
const CDN_HOST = 'http://cdn.dota2.com';

/**
 * Downloads an image from a URL and saves it to a specified filepath.
 */
async function downloadImage(url: string, filepath: string): Promise<void> {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status} for ${url}`);
    const arrayBuffer = await res.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);
    await fsp.writeFile(filepath, buffer);
}

/**
 * Checks if a file exists at a given path.
 */
async function fileExists(filepath: string): Promise<boolean> {
    try {
        await fsp.access(filepath);
        return true;
    } catch {
        return false;
    }
}

/**
 * The generic function to download and sync a specific type of hero image.
 */
async function syncImageType({
    heroData,
    targetDir,
    imageUrlPath,
    imageTypeLabel,
}: {
    heroData: { hero_id: number; img?: string | null; image_url?: string | null; [key: string]: any }[];
    targetDir: string;
    imageUrlPath: (hero: { img?: string | null; image_url?: string | null }) => string | undefined;
    imageTypeLabel: string;
}) {
    console.log(`\nProcessing ${imageTypeLabel} images...`);
    await fsp.mkdir(targetDir, { recursive: true });

    let imagesToDownload = 0;
    let imagesExist = 0;
    let failedDownloads = 0;

    const downloadTasks = heroData.map(async (hero) => {
        const filename = `${hero.hero_id}.png`;
        const localFilePath = path.join(targetDir, filename);
        const rawPath = imageUrlPath(hero);
        if (!rawPath) {
            console.warn(`[WARN] Missing image path for hero ID ${hero.hero_id} (${imageTypeLabel})`);
            failedDownloads++;
            return;
        }
        const cleanPath = rawPath.endsWith('?') ? rawPath.slice(0, -1) : rawPath;
        const cdnUrl = `${CDN_HOST}${cleanPath}`;

        if (await fileExists(localFilePath)) {
            imagesExist++;
        } else {
            imagesToDownload++;
            try {
                await downloadImage(cdnUrl, localFilePath);
            } catch (error: any) {
                console.warn(`[WARN] Failed to download ${imageTypeLabel} for hero ID ${hero.hero_id}: ${error.message}`);
                failedDownloads++;
            }
        }
    });

    await Promise.all(downloadTasks);

    console.log(`- ${imageTypeLabel} Summary -`);
    console.log(`  Existing: ${imagesExist}`);
    console.log(`  Downloaded: ${imagesToDownload - failedDownloads}`);
    if (failedDownloads > 0) {
        console.log(`  Failed: ${failedDownloads}`);
    }
}


/**
 * Main orchestrator function for updating all hero images.
 */
export async function updateHeroImages({ publicDir = PUBLIC_DIR } = {}) {
    console.log("Fetching hero data from backend...");
    const heroData = await fetchHeroData();
    console.log(`Found ${heroData.length} heroes.`);

    const portraitsDir = path.join(publicDir, 'portraits');
    const iconsDir = path.join(publicDir, 'icons');

    // --- Sync Portraits ---
    await syncImageType({
        heroData,
        targetDir: portraitsDir,
        imageUrlPath: (hero) => hero.img ?? hero.image_url ?? undefined,
        imageTypeLabel: 'Portraits',
    });

    // --- Sync Icons ---
    await syncImageType({
        heroData,
        targetDir: iconsDir,
        imageUrlPath: (hero) => {
            const base = hero.img ?? hero.image_url;
            return base ? base.replace('/heroes/', '/heroes/icons/') : undefined;
        },
        imageTypeLabel: 'Icons',
    });

    console.log("\n--- Sync Complete ---");
    console.log(`Target Directory: ${publicDir}`);
    console.log(`Total Heroes Processed: ${heroData.length}`);
}


// --- Script Execution ---
(async () => {
    const isDryRun = process.argv.includes('--dry-run');

    if (isDryRun) {
        console.log('--- RUNNING IN DRY RUN MODE ---');
        let tempDir: string | undefined;
        try {
            tempDir = await fsp.mkdtemp(path.join(os.tmpdir(), 'hero-images-sync-'));
            console.log(`Created temporary sandbox at: ${tempDir}`);

            await updateHeroImages({ publicDir: tempDir });
            console.log("\nDry run validation successful.");

        } finally {
            if (tempDir) {
                console.log(`\nCleaning up sandbox directory: ${tempDir}`);
                await fsp.rm(tempDir, { recursive: true, force: true });
                console.log("Sandbox cleaned up.");
            }
        }
    } else {
        console.log('--- RUNNING IN NORMAL MODE ---');
        await updateHeroImages({ publicDir: PUBLIC_DIR });
        console.log("\nSync process finished.");
    }

})().catch(error => {
    console.error("\n--- AN UNEXPECTED ERROR OCCURRED ---");
    console.error(error);
    process.exit(1);
});
