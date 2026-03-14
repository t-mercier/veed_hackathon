import "dotenv/config";
import { fal } from "@fal-ai/client";

if (!process.env.VEED_API_KEY) {
  console.error("Error: VEED_API_KEY not set in .env");
  process.exit(1);
}

process.env.FAL_KEY = process.env.VEED_API_KEY;

const IMAGE_URL = "https://api.dicebear.com/7.x/bottts/png?seed=news";
const TEXT =
  "Breaking news: scientists have discovered a new species of deep-sea fish that glows in the dark. " +
  "The creature, found at depths of over 3,000 meters, emits a blue bioluminescent light to attract prey. " +
  "Researchers say this finding could unlock new insights into evolutionary biology and underwater ecosystems.";

console.log("Submitting job to veed/fabric-1.0/text...");

try {
  const result = await fal.subscribe("veed/fabric-1.0/text", {
    input: {
      image_url: IMAGE_URL,
      text: TEXT,
      resolution: "480p",
    },
    onQueueUpdate(update) {
      console.log(`[queue] status=${update.status}${update.position != null ? ` position=${update.position}` : ""}`);
    },
  });

  const videoUrl = result?.data?.video?.url ?? result?.data?.video ?? result?.data;
  console.log("Done.");
  console.log("Output video URL:", videoUrl);
} catch (err) {
  const detail = err?.body?.detail ?? err?.cause?.detail;
  console.error("Request failed:", detail ?? err?.message ?? err);
  process.exit(1);
}
