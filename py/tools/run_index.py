import server
from aiohttp import web


class SynVowRunIndex:
    counter = 0

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 2147483647}),
            }
        }

    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("index",)
    FUNCTION = "get_index"
    CATEGORY = "💫SynVow_api/Utils"
    DESCRIPTION = "运行次数自增索引，每次执行自动+1，点击运行时自动归零"

    def get_index(self, seed):
        current_index = SynVowRunIndex.counter
        SynVowRunIndex.counter += 1
        return (current_index,)


@server.PromptServer.instance.routes.post("/synvow/reset_run_index")
async def reset_run_index_endpoint(request):
    SynVowRunIndex.counter = 0
    return web.json_response({"status": "ok", "message": "Counter reset to 0"})


NODE_CLASS_MAPPINGS = {
    "SynVowRunIndex": SynVowRunIndex,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowRunIndex": "运行索引计数器",
}
