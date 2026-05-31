from env_loader import load_dotenv

load_dotenv()

import asyncio

import weave

import config
from fixtures import DUMMY_PITCH_DECK
from orchestrator import run
from session import save_session


async def main() -> None:
    import os

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit(
            "ANTHROPIC_API_KEY is not set. Add it to .env in the project root "
            "or export it in your shell before running."
        )

    weave.init(config.WEAVE_PROJECT)

    output = await run(DUMMY_PITCH_DECK)

    print(output.final_brief.model_dump_json(indent=2))

    session_id = save_session(
        pitch_deck=output.pitch_deck,
        specialist_reports=output.specialist_reports,
        stage1=output.stage1,
        stage2=output.stage2,
        final_brief=output.final_brief,
    )
    print(f"session: {session_id} — saved")


if __name__ == "__main__":
    asyncio.run(main())
