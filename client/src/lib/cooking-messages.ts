/**
 * Fun cooking-themed loading messages shown during generation.
 *
 * Each pipeline step has a pool of messages that rotate every few seconds
 * so the user always sees something fresh and fun while waiting.
 */

/** Messages mapped to backend progress/status strings. */
const STEP_MESSAGES: Record<string, string[]> = {
  // ── Repo pipeline steps (backend `progress` field) ──────────────────────
  "Queued":                    ["Preheating the AI oven… 🔥", "Sharpening the kitchen knives… 🔪", "Tying the apron… 👨‍🍳"],
  "Ingesting GitHub repo…":   ["Gathering fresh ingredients from GitHub… 🧅", "Picking the ripest commits… 🍅", "Raiding the repo pantry… 🥕"],
  "Analyzing architecture…":  ["Reading the recipe book… 📖", "Tasting the code base… 👅", "Sorting ingredients by flavor… 🧂"],
  "Generating storyboard…":   ["Mixing the narrative batter… 🥣", "Folding in the plot twists… 🥐", "Whisking up the storyboard… 🍳"],
  "Polishing narration…":     ["Adding a pinch of eloquence… ✨", "Seasoning the script to perfection… 🌶️", "Letting the narration simmer… 🍲"],
  "Generating scene audio…":  ["Warming up the vocal cords… 🎤", "Pouring the voiceover sauce… 🫗", "Taste-testing the audio… 👂"],
  "Generating avatar videos…": ["Plating the avatar dish… 🍽️", "Adding the finishing garnish… 🌿", "The chef is filming the cooking show… 📹"],

  // ── Code pipeline steps ─────────────────────────────────────────────────
  "Enriching prompt…":         ["Marinating your prompt in AI juices… 🥩", "Infusing extra flavor into the prompt… 🧄", "Adding secret sauce to your idea… 🫙"],
  "Generating scripts…":      ["Writing the recipe step by step… ✍️", "The AI chef is improvising… 🎭", "Cooking up some fresh code… 💻"],
  "Rendering animation…":     ["Baking the animation in the oven… 🎂", "Letting the visuals rise like soufflé… 🧁", "Glazing the frames with pixels… 🖼️"],
  "Generating avatar & voice…": ["The chef is recording a cooking show… 🎬", "Adding the voiceover cream… 🍦", "Decorating with avatar sprinkles… 🍩"],
  "Assembling final video…":  ["Plating the final dish… 🍽️", "Last taste test before serving… 🤌", "Drizzling the finishing glaze… 🍯"],

  // ── Supabase status aliases (used by Premium page production polling) ───
  "pending":            ["Preheating the AI oven… 🔥", "Washing the ingredients… 🧼", "Setting the table… 🍴"],
  "generating_script":  ["The chef is reading your recipe… 📋", "Chopping up the code into pieces… 🔪", "Measuring the AI spices… 🧂"],
  "rendering":          ["Baking the animation in the oven… 🎂", "Watching through the oven window… 👀", "The soufflé is rising nicely… 🧁"],
  "adding_voiceover":   ["Recording the cooking commentary… 🎙️", "Adding the voiceover cream… 🍦", "The chef is narrating the recipe… 👨‍🍳"],
  "finalizing":         ["Plating the final dish… 🍽️", "Last taste test before serving… 🤌", "Adding a sprig of parsley… 🌿"],
  "in_progress":        ["Stirring the AI pot… 🥄", "Something delicious is cooking… 🍳", "Almost ready, keep sniffing… 👃"],
  "done":               ["Bon appétit! 🎉"],
  "completed":          ["Bon appétit! 🎉"],

  // ── Generic / fallback messages ─────────────────────────────────────────
  "Processing…":        ["Something tasty is in the oven… 🍕", "The AI kitchen is buzzing… 🐝", "Chef's special coming right up… 🧑‍🍳"],
};

/** Flat pool of generic fallback messages when the step key isn't recognized. */
const FALLBACK_MESSAGES = [
  "Warming up the AI kitchen… 🔥",
  "Something delicious is cooking… 🍳",
  "The AI chef is hard at work… 👨‍🍳",
  "Stirring the digital pot… 🥄",
  "Simmering your request… 🍲",
  "Kneading the code dough… 🍞",
  "Adding a dash of machine learning… 🧪",
];

/**
 * Pick a cooking message for the given step/status key and rotation tick.
 * `tick` should be an incrementing number (e.g. from a setInterval) so
 * the message rotates even when the backend status hasn't changed.
 */
export function getCookingMessage(statusOrProgress: string | null | undefined, tick: number): string {
  const key = statusOrProgress ?? "";
  const pool = STEP_MESSAGES[key] ?? FALLBACK_MESSAGES;
  return pool[tick % pool.length];
}
