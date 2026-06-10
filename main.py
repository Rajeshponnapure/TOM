import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from agent import TomAgent
from tools.voice_tools import VoiceTools
from safety.guards import SafetyGuards


def safe_print(message: str):
    print(message.encode("ascii", errors="ignore").decode("ascii"))


async def main():
    print("\n" + "=" * 55)
    print("  TOM AUTONOMOUS SYSTEM — Professional AI Assistant")
    print("  Gemma 4 | NLP | Voice | Documents | Data Analysis")
    print("=" * 55 + "\n")

    tom_agent = TomAgent()
    safety = SafetyGuards()
    voice_tools = VoiceTools()
    task_timeout = int(os.environ.get("TASK_TIMEOUT_SECONDS", "180"))

    voice_status = voice_tools.status()
    safe_print(f"Model: {tom_agent.model_name} (primary) / {tom_agent.code_model_name} (code)")
    safe_print(f"Voice input: {'ON' if voice_status['voice_input_enabled'] else 'OFF'}")
    safe_print(f"Voice output: {'ON' if voice_status['voice_output_enabled'] else 'OFF'}")

    if voice_status.get("voice_input_error"):
        safe_print(f"  - Voice input: {voice_status['voice_input_error']}")
    if voice_status.get("voice_output_error"):
        safe_print(f"  - Voice output: {voice_status['voice_output_error']}")

    safe_print("\nCommands available. Type 'help' or 'exit'.\n")

    while True:
        try:
            user_input = input("You: ").strip()

            if user_input.lower() in ("exit", "quit", "q"):
                safe_print("\nShutting down TOM...")
                break

            elif user_input.lower() == "help":
                safe_print("""
TOM PROFESSIONAL COMMANDS:
  Open [app]                  — Launch any installed app
  Write email to [person]     — Draft a context-aware email
  Send email to [email]       — Send email with approval
  Create Word doc about [x]   — Professional .docx creation
  Create Excel for [x]        — .xlsx with data & charts
  Create PPT about [x]        — PowerPoint with animations
  Create PDF report about [x] — Professional PDF generation
  Analyze data in [file]      — Full data analysis pipeline
  Search the web for [x]      — Internet research
  Create website for [x]      — Modern website generation
  WhatsApp [name] saying [msg]— Send WhatsApp message
  Check my inbox              — Email triage
  Read screen                 — OCR screen content
  Build agent called [name]   — Scaffold new sub-agent
  Write code for [file]       — Code file creation
  Schedule [task]             — Background scheduling
  Voice mode / Talk           — Voice conversation mode
  Reward / Penalty            — Feedback on responses

  Tips for professional work:
  - "Create a professional PowerPoint about climate change with internet research"
  - "Create an Excel budget spreadsheet with charts"
  - "Write a formal letter to HR about leave"
  - "Analyze the data in sales.csv and create charts"
""")
                continue

            elif user_input.lower() in ("talk", "voice mode", "talk to me", "let's talk",
                                        "voice chat", "conversation mode", "hey tom"):
                safe_print("\n" + "=" * 50)
                safe_print("  VOICE CONVERSATION MODE")
                safe_print("  Speak naturally — TOM is listening.")
                safe_print("  Say 'stop', 'bye', or 'quit' to end.")
                safe_print("=" * 50 + "\n")

                def _on_status(state, text):
                    if state == "listening":
                        safe_print(f"\n  [LISTENING] {text}")
                    elif state == "processing":
                        safe_print(f"  [THINKING]  {text}")
                    elif state == "speaking":
                        safe_print(f"  [SPEAKING]  {text}")
                    elif state in ("error", "ready", "idle"):
                        safe_print(f"  [{state.upper()}] {text}")

                voice_tools.start_conversation_mode(
                    process_fn=tom_agent.generate_voice_response,
                    on_status=_on_status,
                    blocking=True,
                )
                safe_print("\nBack to text mode.\n")
                continue

            elif user_input.lower() in ("stop talking", "stop voice"):
                voice_tools.stop_conversation_mode()
                safe_print("Voice mode stopped.")
                continue

            elif user_input.lower().startswith("reward"):
                amount = 1.0
                parts = user_input.split()
                if len(parts) >= 2:
                    try:
                        amount = float(parts[1])
                    except ValueError:
                        amount = 1.0
                if tom_agent._last_exp_id:
                    reward_result = await tom_agent.give_reward(int(tom_agent._last_exp_id), abs(amount))
                    safe_print(f"Reward saved: {reward_result.get('message')}")
                else:
                    safe_print("No recent response to reward.")
                continue

            elif user_input.lower().startswith("penalty"):
                amount = -1.0
                parts = user_input.split()
                if len(parts) >= 2:
                    try:
                        amount = -abs(float(parts[1]))
                    except ValueError:
                        amount = -1.0
                if tom_agent._last_exp_id and tom_agent._last_response:
                    penalty_result = await tom_agent.give_reward(int(tom_agent._last_exp_id), amount)
                    safe_print(f"Penalty saved: {penalty_result.get('message')}")
                    correction = input("What should TOM improve?: ").strip()
                    if not correction:
                        correction = "Improve accuracy and alignment."
                    revised = await asyncio.wait_for(
                        tom_agent.revise_response_with_feedback(
                            tom_agent._last_command, tom_agent._last_response, correction,
                        ),
                        timeout=task_timeout,
                    )
                    safe_print(f"\n--- REVISED ---\n{revised.get('message')}")
                else:
                    safe_print("No recent response to penalize.")
                continue

            # Execute task
            result = await asyncio.wait_for(
                tom_agent.execute_task(user_input),
                timeout=task_timeout,
            )

            safe_print(f"\n--- TOM ---")
            msg = result.get("message", "")
            safe_print(msg)

            # Speak response if voice output enabled
            if voice_tools.output_enabled and msg:
                if len(msg) > 500:
                    speak_text = msg[:500] + "..."
                else:
                    speak_text = msg
                voice_tools.speak_async(speak_text)

            # Show additional context
            screen = result.get("screen_summary", "")
            if screen:
                safe_print(f"\n[Screen Content]: {screen[:300]}...")
            content = result.get("content", "")
            if content and len(content) > 0:
                safe_print(f"\n[Content]: {content[:300]}...")
            plan = result.get("plan", "")
            if plan:
                safe_print(f"\n[Plan]: {plan[:300]}...")

            if result.get("experience_id"):
                safe_print("\nTip: Type 'reward' or 'penalty [n]' to give feedback.")
            safe_print("")

        except KeyboardInterrupt:
            safe_print("\n\nInterrupted. Exiting.")
            break
        except asyncio.TimeoutError:
            safe_print(f"\nTask timed out after {task_timeout}s. Try a simpler request.")
            safety.log_action("ERROR", target="task", status="FAILURE", message="Timeout")
        except Exception as e:
            safe_print(f"\nError: {str(e)}")
            safety.log_action("ERROR", target="unknown", status="FAILURE", message=str(e))

    safety.log_action("SESSION_END", target="", status="SUCCESS", message="Session closed.")


if __name__ == "__main__":
    try:
        from tools.crash_guard import install as _cg_install
        _cg_install("cli")
    except Exception:
        pass
    log_dir = PROJECT_ROOT / "tom_logs"
    if not log_dir.exists():
        log_dir.mkdir(parents=True)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        safe_print("\n\nTOM shutting down gracefully...")
    except Exception as e:
        safe_print(f"\nShutdown error: {str(e)}")
