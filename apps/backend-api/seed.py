import asyncio
from db import AsyncSessionLocal
from models import Space, SpaceStatus, SpaceVisibility


async def seed():
    async with AsyncSessionLocal() as db:
        spaces = [
            Space(
                name="Object Detection",
                slug="object-detection",
                description="Detect objects in images using YOLOv11.",
                task_type="object-detection",
                input_types=["image"],
                output_types=["image", "json"],
                container_image="localhost/ai-spaces-yolo:latest",
                resource_requirements={"cpu": "1", "memory": "2Gi"},
                ui_config={
                    "inputs": [{"type": "image_upload", "label": "Upload Image"}],
                    "outputs": [{"type": "image", "label": "Result"}],
                },
                runner_config={"timeout": 120},
                visibility=SpaceVisibility.public,
                status=SpaceStatus.active,
            ),
            Space(
                name="Video Generator",
                slug="video-generator",
                description="Generate videos from text prompts using LTX 2.3.",
                task_type="text-to-video",
                input_types=["text"],
                output_types=["video"],
                container_image="localhost/ai-spaces-ltx:latest",
                resource_requirements={"cpu": "4", "memory": "16Gi", "gpu": "1"},
                ui_config={
                    "inputs": [{"type": "text", "label": "Enter your prompt"}],
                    "outputs": [{"type": "video", "label": "Generated Video"}],
                },
                runner_config={"timeout": 600},
                visibility=SpaceVisibility.public,
                status=SpaceStatus.active,
            ),
        ]
        db.add_all(spaces)
        await db.commit()
        print("✅ Seeded 2 spaces successfully.")


if __name__ == "__main__":
    asyncio.run(seed())
