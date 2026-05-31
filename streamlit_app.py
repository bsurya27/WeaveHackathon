import asyncio
import os
import uuid

import streamlit as st
import weave

from env_loader import load_dotenv

load_dotenv()

import config
from agents import followup, intake_turn, merge_intake_updates
from fixtures import DUMMY_PITCH_DECK
from orchestrator import run
from schemas import PitchDeck, empty_pitch_deck
from session import append_followup, load_session, save_session

FOLLOWUP_ROLES = [
    "supervisor",
    "marketer",
    "legal",
    "tech",
    "finance",
    "investor",
    "devils_advocate",
    "innovator",
]


def run_async(coro):
    return asyncio.run(coro)


def init_weave() -> None:
    if st.session_state.get("weave_ready"):
        return
    weave.init(config.WEAVE_PROJECT)
    st.session_state.weave_ready = True


def ensure_state() -> None:
    if "session_id" not in st.session_state:
        st.session_state.session_id = uuid.uuid4().hex[:12]
    if "deck" not in st.session_state:
        st.session_state.deck = empty_pitch_deck()
    if "intake_messages" not in st.session_state:
        st.session_state.intake_messages = []
    if "intake_done" not in st.session_state:
        st.session_state.intake_done = False
    if "panel_done" not in st.session_state:
        st.session_state.panel_done = False
    if "session_data" not in st.session_state:
        st.session_state.session_data = None
    if "followup_messages" not in st.session_state:
        st.session_state.followup_messages = []


def start_intake() -> None:
    turn = run_async(
        intake_turn(st.session_state.deck, None, st.session_state.intake_messages)
    )
    st.session_state.deck = merge_intake_updates(st.session_state.deck, turn.updates)
    if turn.next_question:
        st.session_state.intake_messages.append(
            {"role": "supervisor", "text": turn.next_question}
        )
    if turn.done:
        st.session_state.intake_done = True


def handle_intake_message(text: str) -> None:
    st.session_state.intake_messages.append({"role": "user", "text": text})
    turn = run_async(
        intake_turn(st.session_state.deck, text, st.session_state.intake_messages)
    )
    st.session_state.deck = merge_intake_updates(st.session_state.deck, turn.updates)
    if turn.done:
        st.session_state.intake_done = True
        st.session_state.intake_messages.append(
            {
                "role": "supervisor",
                "text": "Pitch deck complete. Review it below, then run the advisor panel.",
            }
        )
    elif turn.next_question:
        st.session_state.intake_messages.append(
            {"role": "supervisor", "text": turn.next_question}
        )


def run_panel() -> None:
    output = run_async(run(st.session_state.deck))
    sid = save_session(
        pitch_deck=output.pitch_deck,
        specialist_reports=output.specialist_reports,
        stage1=output.stage1,
        stage2=output.stage2,
        final_brief=output.final_brief,
        session_id=st.session_state.session_id,
        followups=[],
    )
    st.session_state.session_id = sid
    st.session_state.session_data = load_session(sid)
    st.session_state.panel_done = True


def handle_followup(text: str, role: str) -> None:
    reply = run_async(
        followup(st.session_state.session_data, text, target_role=role)
    )
    append_followup(st.session_state.session_id, text, reply.reply, role)
    st.session_state.session_data = load_session(st.session_state.session_id)
    st.session_state.followup_messages.append({"role": "user", "text": text, "scope": role})
    st.session_state.followup_messages.append(
        {"role": "assistant", "text": reply.reply, "scope": role}
    )


def load_fixture_deck() -> None:
    st.session_state.deck = DUMMY_PITCH_DECK.model_copy()
    st.session_state.intake_done = True
    st.session_state.intake_messages = [
        {
            "role": "supervisor",
            "text": (
                "Loaded pitch deck from fixtures.py (AI research curator). "
                "Review it on the right, then run the advisor panel."
            ),
        }
    ]


def reset_all() -> None:
    for key in list(st.session_state.keys()):
        del st.session_state[key]


def main() -> None:
    st.set_page_config(page_title="Startup Advisor", layout="wide")
    st.title("Startup Advisor")

    if not os.environ.get("ANTHROPIC_API_KEY"):
        st.error("Set ANTHROPIC_API_KEY in .env before running.")
        st.stop()

    init_weave()
    ensure_state()

    with st.sidebar:
        st.caption(f"Session `{st.session_state.session_id}`")
        if st.button("Load fixture deck (skip intake)", type="secondary"):
            load_fixture_deck()
            st.rerun()
        if st.button("New session"):
            reset_all()
            st.rerun()
        if st.session_state.panel_done:
            st.success("Panel complete")
        elif st.session_state.intake_done:
            st.info("Intake complete — run panel when ready")

    col_chat, col_deck = st.columns([3, 2])

    with col_chat:
        st.subheader("Advisor Q&A" if st.session_state.panel_done else "Intake")
        if not st.session_state.intake_messages and not st.session_state.intake_done:
            with st.spinner("Starting intake…"):
                start_intake()
            st.rerun()

        messages = (
            st.session_state.intake_messages
            if not st.session_state.panel_done
            else st.session_state.followup_messages
        )
        for msg in messages:
            role = "assistant" if msg["role"] != "user" else "user"
            label = msg.get("scope") or msg.get("role", "")
            with st.chat_message(role):
                if label and msg["role"] != "user":
                    st.caption(label)
                st.write(msg["text"])

        if not st.session_state.intake_done:
            if prompt := st.chat_input("Your answer…"):
                with st.spinner("Thinking…"):
                    handle_intake_message(prompt)
                st.rerun()
        elif st.session_state.panel_done:
            scope = st.selectbox("Answer from", FOLLOWUP_ROLES, index=0)
            if prompt := st.chat_input("Ask about the brief…"):
                with st.spinner("Thinking…"):
                    handle_followup(prompt, scope)
                st.rerun()

    with col_deck:
        st.subheader("Pitch deck")
        deck = st.session_state.deck
        if st.session_state.intake_done:
            st.json(deck.model_dump())

        if st.session_state.intake_done and not st.session_state.panel_done:
            st.divider()
            if st.button("Run advisor panel", type="primary"):
                with st.spinner("Running panel (several minutes)…"):
                    run_panel()
                st.rerun()

        if st.session_state.panel_done and st.session_state.session_data:
            st.divider()
            st.subheader("Final brief")
            brief = st.session_state.session_data.get("final_brief", {})
            for i, item in enumerate(brief.get("focus_list", []), 1):
                with st.expander(f"{i}. {item.get('title', 'Focus item')}"):
                    st.markdown(f"**Action:** {item.get('action', '')}")
                    st.markdown(f"**Success:** {item.get('success_criteria', '')}")
                    st.caption(item.get("rationale", ""))
            st.caption(f"Saved to sessions/{st.session_state.session_id}.json")


if __name__ == "__main__":
    main()
