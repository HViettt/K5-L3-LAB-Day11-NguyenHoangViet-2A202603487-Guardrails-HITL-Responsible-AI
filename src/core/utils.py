"""
Lab 11 — Helper Utilities
"""
from core.config import get_llm_provider, PROVIDER_OPENROUTER  # noqa: F401
from core.openai_runtime import OpenAIRunner


async def chat_with_agent(agent, runner, user_message: str, session_id=None):
    """Send a message to the agent and get the response.

    Works with OpenAIRunner (OpenAI Red / OpenRouter Blue) and Google ADK (Gemini Red).
    """
    provider = getattr(runner, "provider", None)
    if isinstance(runner, OpenAIRunner) or provider in ("openrouter", "openai"):
        text = await runner.chat(agent, user_message)
        return text, None

    from google.genai import types

    user_id = "student"
    app_name = runner.app_name

    session = None
    if session_id is not None:
        try:
            session = await runner.session_service.get_session(
                app_name=app_name, user_id=user_id, session_id=session_id
            )
        except (ValueError, KeyError):
            pass

    if session is None:
        try:
            session = await runner.session_service.create_session(
                app_name=app_name, user_id=user_id
            )
        except Exception:
            session = await runner.session_service.create_session(
                app_name=app_name, user_id=user_id
            )

    content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_message)],
    )

    import asyncio

    orig_model = getattr(agent, "model", None)
    models_to_try = [orig_model]
    if isinstance(orig_model, str):
        for fb in ("gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-flash-lite-latest"):
            if fb != orig_model:
                models_to_try.append(fb)

    last_err = None
    for idx, m in enumerate(models_to_try):
        if isinstance(orig_model, str) and m:
            agent.model = m
        try:
            final_response = ""

            async def _collect():
                nonlocal final_response
                async for event in runner.run_async(
                    user_id=user_id, session_id=session.id, new_message=content
                ):
                    if hasattr(event, "content") and event.content and event.content.parts:
                        for part in event.content.parts:
                            if hasattr(part, "text") and part.text:
                                final_response += part.text

            await asyncio.wait_for(_collect(), timeout=15.0)
            return final_response, session
        except Exception as e:
            last_err = e
            # Re-create fresh session for retry
            try:
                session = await runner.session_service.create_session(
                    app_name=app_name, user_id=user_id
                )
            except Exception:
                pass
            continue
        finally:
            if isinstance(orig_model, str):
                agent.model = orig_model

    if last_err is not None:
        raise last_err
    return "", session
