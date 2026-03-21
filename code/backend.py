from dataclasses import dataclass
import json
import httpx
from dotenv import load_dotenv
from runware import Runware, IImageInference, IGoogleTextProviderSettings
import sys
import os
import asyncio


@dataclass
class TutorialRequest:
    prompt: str
    url: str
    avatar_id: str
    mood: str
    level: str


# {
#   "prompt": "Explain recursion using factorial",
#   "url": "https://github.com/user/repo",
#   "avatar_id": "veed_avatar_abc123",
#   "mood": "friendly",
#   "level": "beginner"
# }

FRONT_END_URL = "https://something"


async def process_request(request: TutorialRequest):
    load_dotenv()
    runwareApiKey = os.getenv("RUNWARE_API_KEY")
    if not runwareApiKey:
        sys.exit("Runware API key not found")
    runware = Runware(api_key=runwareApiKey)
    await runware.connect()
    IGoogleTextProviderSettings()


BASE_URL = "https://api.runware.ai/v1"  # If your org uses a different base, change it.

# TODO: Replace with the exact text model ID visible in your Runware catalog
GEMINI_TEXT_MODEL = "google:gemini@3-flash"  # <-- placeholder; use your real model id


async def run_gemini_text(prompt: str, system: str | None = None) -> str:
    load_dotenv()
    runwareApiKey = os.getenv("RUNWARE_API_KEY")
    """
    Sends a text→text request to Runware targeting a Gemini 3 Flash (text) model.
    """
    payload = [
        {
            "taskType": "textInference",
            "apiKey": runwareApiKey,
            "model": GEMINI_TEXT_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        }
    ]

    headers = {
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{BASE_URL}/tasks", headers=headers, json=payload, timeout=60.0
        )
        r.raise_for_status()
        response_json = r.json()
        
        # Check for errors in the individual task
        data = response_json.get("data")
        if not data or not isinstance(data, list):
            errors = response_json.get("errors")
            raise RuntimeError(f"Runware task failed with errors: {json.dumps(errors or response_json, indent=2)}")

        task = data[0]
        task_uuid = task.get("taskUUID") or task.get("id")
        if not task_uuid:
            raise RuntimeError(
                f"Unexpected task response: {json.dumps(task, indent=2)}"
            )

        # Poll for completion (Runware typically processes async work)
        for _ in range(60):
            # Check if task is already completed in the initial response
            status = task.get("status") or task.get("state")
            if status in ("completed", "succeeded", "success"):
                return task.get("text") or json.dumps(task, indent=2)

            s = await client.get(
                f"{BASE_URL}/tasks/{task_uuid}", timeout=30.0
            )
            s.raise_for_status()
            body = s.json()
            
            # The polling response for a single task usually contains the task object directly or in a 'data' list
            task_data = body.get("data")
            if isinstance(task_data, list) and task_data:
                task = task_data[0]
            else:
                task = body

            status = task.get("status") or task.get("state")
            if status in ("completed", "succeeded", "success"):
                return task.get("text") or json.dumps(task, indent=2)

            if status in ("failed", "error"):
                raise RuntimeError(f"Runware task failed: {json.dumps(task, indent=2)}")

            await asyncio.sleep(1)

    raise TimeoutError("Runware task did not complete in time.")


if __name__ == "__main__":

    async def main():
        try:
            result = await run_gemini_text(
                "Summarize the SOLID principles in 5 bullets."
            )
            print(result)
        except httpx.HTTPStatusError as e:
            print(f"HTTP error occurred: {e}")
            if e.response.status_code == 401:
                print("Tip: Check if RUNWARE_API_KEY is correctly set in your .env file.")
        except Exception as e:
            print(f"An error occurred: {e}")

    asyncio.run(main())
