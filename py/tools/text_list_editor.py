import time
import uuid
import server
from aiohttp import web
from nodes import interrupt_processing
try:
    import execution as _execution
except ImportError:
    _execution = None

pending_text_lists = {}


class TextListEditor:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text_list": ("STRING", {"forceInput": True}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("edited_texts",)
    INPUT_IS_LIST = True
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "edit_text_list"
    CATEGORY = "💫SynVow_api/tools"
    OUTPUT_NODE = True

    def edit_text_list(self, text_list, unique_id=None):
        if isinstance(unique_id, list):
            unique_id = unique_id[0] if unique_id else None

        texts = text_list if isinstance(text_list, list) else [str(text_list)]

        session_id = str(uuid.uuid4())
        pending_text_lists[session_id] = {
            "edited_texts": texts.copy(),
            "confirmed": False,
            "cancelled": False
        }

        cleaned_texts = [str(t).strip() for t in texts]

        server.PromptServer.instance.send_sync(
            "text_list_edit_session",
            {
                "session_id": session_id,
                "node_id": unique_id,
                "texts": cleaned_texts
            }
        )

        timeout = 3600
        start_time = time.time()
        while True:
            time.sleep(0.1)

            if session_id not in pending_text_lists:
                interrupt_processing()
                return ([], )

            session = pending_text_lists[session_id]
            if session.get("confirmed"):
                break
            if session.get("cancelled"):
                del pending_text_lists[session_id]
                interrupt_processing()
                return ([], )

            if time.time() - start_time > timeout:
                del pending_text_lists[session_id]
                interrupt_processing()
                return ([], )

            if _execution is not None and getattr(_execution, "interrupt_processing_boolean", False):
                if session_id in pending_text_lists:
                    del pending_text_lists[session_id]
                return ([], )

        edited_texts = pending_text_lists[session_id]["edited_texts"]
        if not isinstance(edited_texts, list):
            edited_texts = [edited_texts] if edited_texts else []

        del pending_text_lists[session_id]
        return (edited_texts,)


def add_routes(routes):
    @routes.post('/text_list_edit/confirm')
    async def confirm(request):
        try:
            data = await request.json()
            session_id = data.get("session_id")
            edited_texts = data.get("edited_texts", [])

            if session_id not in pending_text_lists:
                return web.json_response({"status": "error", "message": "Session not found"}, status=404)

            if not isinstance(edited_texts, list):
                edited_texts = [edited_texts] if edited_texts else []

            pending_text_lists[session_id]["edited_texts"] = edited_texts
            pending_text_lists[session_id]["confirmed"] = True
            return web.json_response({"status": "success"})
        except Exception as e:
            print(f"TextListEditor: Confirm error: {e}")
            return web.json_response({"status": "error", "message": str(e)}, status=500)

    @routes.post('/text_list_edit/cancel')
    async def cancel(request):
        try:
            data = await request.json()
            session_id = data.get("session_id")

            if session_id not in pending_text_lists:
                return web.json_response({"status": "error", "message": "Session not found"}, status=404)

            pending_text_lists[session_id]["cancelled"] = True
            return web.json_response({"status": "success"})
        except Exception as e:
            print(f"TextListEditor: Cancel error: {e}")
            return web.json_response({"status": "error", "message": str(e)}, status=500)


try:
    if server.PromptServer.instance is not None:
        add_routes(server.PromptServer.instance.routes)
except Exception as e:
    print(f"Warning: Could not register TextListEditor routes: {e}")


NODE_CLASS_MAPPINGS = {"SynVowApiTextListEditor": TextListEditor}
NODE_DISPLAY_NAME_MAPPINGS = {"SynVowApiTextListEditor": "提示词文本编辑器"}
