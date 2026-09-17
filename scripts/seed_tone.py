import asyncio
from sqlalchemy import select, update
from app.db.session import AsyncSessionLocal
from app.db.models.tone import Tone

# ✅ Predefined tones (including missing Professional)
DEFAULT_TONES = [
    {
        "name": "Professional",
        "description": "Formal, respectful, and business-oriented communication",
        "is_default": False,
    },
    {
        "name": "Friendly",
        "description": "Warm, approachable, and easygoing interaction",
        "is_default": True,  # default tone
    },
    {
        "name": "Concise",
        "description": "Short, direct, and to-the-point responses",
        "is_default": False,
    },
    {
        "name": "Empathetic",
        "description": "Understanding, supportive, and emotionally aware",
        "is_default": False,
    },
    {
        "name": "Persuasive",
        "description": "Convincing, engaging, and action-driven communication",
        "is_default": False,
    },
]


async def seed_default_tones():
    async with AsyncSessionLocal() as session:
        for tone_data in DEFAULT_TONES:
            # 🔍 Check if tone already exists
            stmt = select(Tone).where(Tone.name == tone_data["name"])
            result = await session.execute(stmt)
            existing_tone = result.scalar_one_or_none()

            if existing_tone:
                print(f"'{tone_data['name']}' already exists. Skipping.")

                # ✅ Ensure default is correctly set even if already exists
                if tone_data.get("is_default"):
                    await session.execute(
                        update(Tone)
                        .where(Tone.is_default == True)
                        .values(is_default=False)
                    )
                    existing_tone.is_default = True

                continue

            # If this tone should be default → unset previous default
            if tone_data.get("is_default"):
                await session.execute(
                    update(Tone)
                    .where(Tone.is_default == True)
                    .values(is_default=False)
                )

            # ✅ Create new tone
            new_tone = Tone(
                name=tone_data["name"],
                description=tone_data["description"],
                is_default=tone_data.get("is_default", False),
                created_by=None,  
            )

            session.add(new_tone)
            await session.flush()

        await session.commit()
        print("✅ Default tones seeded successfully.")


if __name__ == "__main__":
    asyncio.run(seed_default_tones())