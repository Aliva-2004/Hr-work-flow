"""AI HR assistant chat (grounded in live database data)."""
import streamlit as st
from services import ai_service as ai

QUICK = {"📋 Daily summary": "Give me my daily work summary.",
         "⏰ Approaching deadlines": "Which tasks have approaching deadlines?",
         "🚨 Overdue work": "Highlight all overdue work and who owns it.",
         "📧 Pending emails": "Summarise pending client emails and which are most urgent.",
         "📈 Productivity insights": "Give me productivity insights from the data."}


def render(user: dict):
    st.title("AI Assistant")
    if ai.ai_enabled():
        st.caption("Connected to Gemini · answers are based on your live FlowHR data.")
    else:
        st.info("No AI key found. The assistant will show live data summaries. "
                "Add GEMINI_API_KEY to your .env file to enable full AI chat and drafting.")
    chat = st.session_state.setdefault("ai_chat", [])
    cols = st.columns(len(QUICK))
    clicked = None
    for col, (label, q) in zip(cols, QUICK.items()):
        if col.button(label):
            clicked = q
    if st.button("Clear chat"):
        chat.clear()
        st.rerun()
    for m in chat:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
    question = st.chat_input("Ask about tasks, deadlines, leave, emails, meetings...") or clicked
    if question:
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                answer, _ = ai.ask(user, question, chat)
            st.markdown(answer)
        chat.append({"role": "user", "content": question})
        chat.append({"role": "assistant", "content": answer})
