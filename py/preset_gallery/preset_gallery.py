import json, os
from aiohttp import web
from server import PromptServer

from ..api import synvow_auth
from ..api.media_common import stack_image_tensors, unpack_list_input as _unpack
from ..api import gpt_image_2_synvow as _g

HERE = os.path.dirname(__file__)
_D = json.load(open(os.path.join(HERE, "commands.json"), encoding="utf-8"))
_OPTS = [c["zh"] for c in _D]
_PROMPT = {c["zh"]: f'{c["code"]} {c["zh"]}' for c in _D}
_PROMPT.update({c["zh_t"]: _PROMPT[c["zh"]] for c in _D if c.get("zh_t")})  # 兼容旧工作流里的繁体预设名


def _thumb_name(c):
    n = f'{c["code"]}➕{c.get("zh_t") or c["zh"]}'
    for ch in '\\/:*?"<>|':
        n = n.replace(ch, "_")
    return n + ".jpg"


@PromptServer.instance.routes.get("/preset_gallery/list")
async def _list(req):
    return web.json_response([{"label": o, "thumb": _thumb_name(c), "cat": c.get("category", ""), "code": c.get("code", ""), "alt": c.get("zh_t", "")} for o, c in zip(_OPTS, _D)])


@PromptServer.instance.routes.get("/preset_gallery/thumb/{name}")
async def _thumb(req):
    p = os.path.join(HERE, "thumbs", os.path.basename(req.match_info["name"]))
    return web.FileResponse(p) if os.path.exists(p) else web.Response(status=404)


# ---- 收藏：按指令 code 记录，保存在本插件目录的 favorites.json，重启不丢 ----
_FAV = os.path.join(HERE, "favorites.json")


def _load_favs():
    try:
        with open(_FAV, encoding="utf-8") as f:
            v = json.load(f)
        return [str(x) for x in v] if isinstance(v, list) else []
    except Exception:
        return []


def _save_favs(favs):
    tmp = _FAV + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(favs, f, ensure_ascii=False, indent=1)
    os.replace(tmp, _FAV)


@PromptServer.instance.routes.get("/preset_gallery/favs")
async def _get_favs(req):
    return web.json_response(_load_favs())


@PromptServer.instance.routes.post("/preset_gallery/favs/set")
async def _set_fav(req):
    body = await req.json()
    code, on = str(body.get("code", "")), bool(body.get("fav"))
    favs = [x for x in _load_favs() if x != code]
    if on and code:
        favs.append(code)
    _save_favs(favs)
    return web.json_response(favs)


class PresetGallery:
    """预设画廊：模型选择与出图流程复用 SynVow GPT-Image-2 节点。"""
    CATEGORY = "💫SynVow_api/api/图像"
    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "prompt")
    FUNCTION = "run"

    @classmethod
    def INPUT_TYPES(cls):
        req = {"preset": (_OPTS,)}
        req.update(_g._param_inputs())
        return {"required": req, "optional": {f"image_{i}": ("IMAGE",) for i in range(1, 9)}}

    @classmethod
    def VALIDATE_INPUTS(cls, preset):
        return True if preset in _PROMPT else "未知预设，请在画廊重新选择"

    def run(self, preset, model_type=None, gpt_style=None, quality=None, resolution=None,
            aspect_ratio=None, transparent=False, seed=0, image_1=None, image_2=None,
            image_3=None, image_4=None, image_5=None, image_6=None, image_7=None, image_8=None):
        model, style, quality, eff_resolution, size = _g._prep_model(
            model_type, quality, resolution or "1K", aspect_ratio, gpt_style)
        prompt = _PROMPT.get(preset, preset)
        api_key = synvow_auth.read_api_key()
        imgs = [t for t in (image_1, image_2, image_3, image_4, image_5, image_6, image_7, image_8) if t is not None]
        is_img2img = len(imgs) > 0
        urls = _g._run_tasks([(prompt, imgs)], model, size, quality, eff_resolution, is_img2img,
                             api_key, gpt_style=style, transparent=bool(transparent))
        if not any(urls):
            raise RuntimeError(f"生成失败 model={model} size={size}")
        out = stack_image_tensors(urls, tag="PresetGallery")
        synvow_auth.refresh_balance()
        return (out, prompt)


NODE_CLASS_MAPPINGS = {"PresetGallery": PresetGallery}
NODE_DISPLAY_NAME_MAPPINGS = {"PresetGallery": "预设画廊"}
