import discord
import io
import re
import os
import threading
import base64
from discord.ext import commands
from flask import Flask

# Thử nghiệm import thư viện giả lập Lua chuyên nghiệp
try:
    from lupa import LuaRuntime
except ImportError:
    LuaRuntime = None

# KHỞI TẠO WEB SERVER DUY TRÌ PORT TRÊN RENDER
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Ultimate Sandbox Dumper v3.0 đang LIVE!"

def run_server():
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=".", intents=intents)

# ====================================================
# ENGINE TỐI CAO: DYNAMIC LUA SANDBOX HOOKER
# ====================================================

def run_lua_dynamic_sandbox(obfuscated_code):
    """
    Hộp cát ảo cấp cao: Ép script tự bẻ khóa chính nó trong môi trường RAM cô lập
    """
    if LuaRuntime is None:
        return "Error: Thư viện 'lupa' chưa được cài đặt trên máy chủ Hosting!"
        
    try:
        # Khởi tạo môi trường nhân Lua ảo thuần khiết
        lua = LuaRuntime(unpack_returned_tuples=True)
        dumped_payloads = []
        
        # 1. Định nghĩa bộ lọc chặn bắt (Hook Callback) khi chuỗi thô rò rỉ ra bộ nhớ
        def catch_leaked_source(source_code):
            if type(source_code) == str and len(source_code.strip()) > 15:
                # Bỏ qua các chuỗi rác lặp lại của chính trình obfuscator
                if not any(k in source_code for k in ["IlllIIllI", "MiyuObfuscatorFakeCheck"]):
                    if source_code not in dumped_payloads:
                        dumped_payloads.append(source_code)
            return lua.eval("function() end")

        # 2. Cài cắm camera giám sát vào các hàm nhạy cảm toàn cục của hệ thống ảo
        lua_globals = lua.globals()
        lua_globals['loadstring'] = catch_leaked_source
        lua_globals['load'] = catch_leaked_source
        
        # Giả lập lại toàn bộ cấu trúc biến môi trường Roblox để đánh lừa mã độc bypass anti-dump
        lua.execute("getgenv = function() return _G end")
        lua.execute("shared = {}")
        lua.execute([[
            game = {
                HttpGet = function(self, url) 
                    return "print('=== [ DETECTED REQ TO: ' .. tostring(url) .. ' ] ===')" 
                end,
                HttpGetAsync = function(self, url) return "" end,
                GetService = function(self, service) 
                    return { GetLocalPlayer = function() return {} end } 
                end
            }
            owner = {}
            script = { Name = "WandaDumpSandbox" }
        ]])
        
        # 3. Kích hoạt lệnh chạy động cho mã hóa tự cắn đuôi nhau trong sandbox
        try:
            lua.execute(obfuscated_code)
        except:
            pass

        if dumped_payloads:
            return "\n\n-- [ DUMPED VIA DYNAMIC LUA SANDBOX ENGINE ] --\n\n" + "\n\n".join(dumped_payloads)
    except Exception as e:
        return f"Sandbox Error: {str(e)}"
    return None

# ====================================================
# CÁC BỘ LỌC TĨNH DỰ PHÒNG (STATIC FALLBACK DETECTORS)
# ====================================================

def clean_lua_math(expr):
    return expr.replace(';', '').replace('{', '').replace('}', '').strip()

def try_dump_static_layers(code):
    """Tổng hợp toàn bộ sức mạnh quét chuỗi tĩnh cũ khi Sandbox không hoạt động"""
    try:
        hex_block_match = re.search(r'\[=\[[A-Z]{3}:([0-9A-Fa-f]+)\]=\]', code)
        matrix_match = re.search(r'\{\s*(\{[^{}]+\}\s*,\s*)*\{[^{}]+\}\s*\}', code)
        if hex_block_match and matrix_match:
            hex_payload = hex_block_match.group(1)
            pairs = re.findall(r'\{\s*([^\},]+)\s*,\s*([^\}]+)\s*\}', matrix_match.group(0))
            matrix = []
            for obf_key, obf_offset in pairs:
                matrix.append([int(eval(clean_lua_math(obf_key), {"__builtins__": None}, {})), int(eval(clean_lua_math(obf_offset), {"__builtins__": None}, {}))])
            decoded_bytes = bytearray()
            byte_idx = 0
            for i in range(0, len(hex_payload), 2):
                cipher_byte = int(hex_payload[i:i+2], 16)
                dec_byte = cipher_byte
                for k_layer in matrix:
                    v_x = 0
                    for v_m in range(8):
                        if ((dec_byte >> v_m) & 1) != ((k_layer[0] >> v_m) & 1): v_x |= (1 << v_m)
                    dec_byte = v_x
                decoded_bytes.append(dec_byte)
                for k_layer in matrix: k_layer[0] = (k_layer[0] + byte_idx + k_layer[1]) % 256
                byte_idx += 1
            return decoded_bytes.decode('utf-8', errors='ignore')
    except: pass

    if "£" in code:
        pattern = r'([A-Za-z0-9ÂÝÎËÌÍÊÏÆÈÇ]+(?:£[A-Za-z0-9ÂÝÎËÌÍÊÏÆÈÇ]*)+)'
        matches = re.findall(pattern, code)
        if matches:
            decoded_str = ""
            for match in matches:
                for token in match.split('£'):
                    if not token: continue
                    t_sum = sum(ord(c) for c in token)
                    res_ascii = (t_sum - 120) % 256
                    if 32 <= res_ascii <= 126 or res_ascii in [9, 10, 13]: decoded_str += chr(res_ascii)
            if len(decoded_str.strip()) > 20: return decoded_str

    slash_bytes = re.findall(r'\\([0-9]{2,3})', code)
    if slash_bytes and len(slash_bytes) > 10:
        try: return "".join(chr(int(b)) for b in slash_bytes if 0 <= int(b) <= 255)
        except: pass

    b64_pattern = r'["\']([A-Za-z0-9+/]{30,}=*=*)["\']'
    matches = re.findall(b64_pattern, code)
    if matches:
        try:
            for m in matches:
                ds = base64.b64decode(m).decode('utf-8', errors='ignore')
                if any(k in ds for k in ["loadstring", "game", "local", "HttpGet"]): return ds
        except: pass

    return None

# ==========================================
# COMMAND XỬ LÝ ĐA LUỒNG TỐI CAO
# ==========================================

@bot.command(name="dump")
async def dump_command(ctx, *, text_code: str = None):
    target_code = None
    if ctx.message.attachments:
        try:
            target_code = (await ctx.message.attachments[0].read()).decode(errors="ignore")
        except:
            await ctx.reply("❌ Error: Không thể đọc tệp tin đính kèm.")
            return
    elif text_code:
        target_code = re.sub(r'^```[a-zA-Z]*\n|```$', '', text_code.strip(), flags=re.MULTILINE)
        
    if not target_code:
        await ctx.reply("⚠️ Hãy gửi file `.lua` hoặc dán mã nguồn mã hóa sau cấu trúc lệnh `.dump`")
        return

    status_msg = await ctx.reply("⚙️ **CỖ MÁY DUMP TỐI CAO v3.0:** Đang khởi tạo hộp cát RAM ảo và ép chạy giải mã...")

    result_code = None
    engine_used = ""

    if LuaRuntime:
        dynamic_res = run_lua_dynamic_sandbox(target_code)
        if dynamic_res and not dynamic_res.startswith("Error"):
            result_code = dynamic_res
            engine_used = "Ultimate Dynamic Sandbox Hooker (Lupa Engine)"

    if not result_code:
        static_res = try_dump_static_layers(target_code)
        if static_res:
            result_code = static_res
            engine_used = "Cascading Static Deobfuscator"

    await status_msg.delete()
    
    if result_code and len(result_code.strip()) > 10:
        file_stream = io.BytesIO(result_code.encode('utf-8'))
        await ctx.reply(
            content=f"✅ {ctx.author.mention} **Bẻ khóa mã nguồn thành công!**\n💎 **Công nghệ bóc tách:** `{engine_used}`",
            file=discord.File(file_stream, filename="dumped_ultimate_source.lua")
        )
    else:
        await ctx.reply("⚠️ Cảnh báo: Loại mã nguồn này sử dụng cơ chế dịch ngược Bytecode mã máy ảo cực sâu độc quyền, hộp cát ảo không ghi nhận tín hiệu bung chuỗi đọc được.")

if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    bot.run(os.getenv("TOKEN"))

